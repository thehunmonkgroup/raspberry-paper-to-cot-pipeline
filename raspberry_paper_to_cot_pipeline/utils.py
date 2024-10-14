import logging
import requests
import sqlite3
import pymupdf4llm
import re
import os
from contextlib import contextmanager
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Dict, Generator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from lwe.core.config import Config
from lwe import ApiBackend
from raspberry_paper_to_cot_pipeline import constants


@contextmanager
def get_db_connection(database_path):
    conn = sqlite3.connect(database_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.isolation_level = "IMMEDIATE"
    try:
        yield conn
    finally:
        conn.close()

class Utils:
    def __init__(self,
                 database: Optional[str] = constants.DEFAULT_DB_NAME,
                 inference_artifacts_directory: Optional[str] = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
                 training_artifacts_directory: Optional[str] = constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
                 pdf_cache_dir: Optional[str] = constants.DEFAULT_PDF_CACHE_DIR,
                 lwe_default_preset: Optional[str] = constants.DEFAULT_LWE_PRESET,
                 logger: Optional[str] = None,
                 ):
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.training_artifacts_directory = training_artifacts_directory
        self.pdf_cache_dir = pdf_cache_dir
        self.lwe_default_preset = lwe_default_preset
        self.logger = logger if logger else self.setup_logging("Utils", False)
        self.lwe_backend = None

    @staticmethod
    def setup_logging(logger_name: str, debug: bool) -> logging.Logger:
        """Set up logging configuration for a specific logger."""
        logging.getLogger().addHandler(logging.NullHandler())
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        logger.propagate = False
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def setup_lwe(self) -> ApiBackend:
        """Set up LWE configuration and API backend."""
        config = Config(config_dir=str(constants.LWE_CONFIG_DIR), data_dir=str(constants.LWE_DATA_DIR))
        config.load_from_file()
        config.set("model.default_preset", self.lwe_default_preset)
        self.lwe_backend = ApiBackend(config)
        self.lwe_backend.set_return_only(True)
        return self.lwe_backend

    def run_lwe_template(self, template: str, template_vars: dict, overrides: dict = None) -> str:
        """
        Run the LWE template with the given variables.

        :param lwe_backend: LWE API backend
        :param template: Template name
        :param template_vars: Template variables
        :return: Response on success
        """
        # Check if self.lwe_backend is None, if so, raise a RuntimeError
        if self.lwe_backend is None:
            raise RuntimeError("LWE backend not initialized")
        overrides = overrides or {}
        success, response, user_message = self.lwe_backend.run_template(template, template_vars, overrides)
        if not success:
            message = f"Error running LWE template: {user_message}"
            self.logger.error(message)
            raise RuntimeError(message)
        return response

    def write_pdf_to_cache(self, pdf_path: Path | str, pdf_content: bytes) -> None:
        """
        Write PDF content to cache.

        :param pdf_path: Path to the PDF file
        :param pdf_content: Content of the PDF file
        """
        pdf_path = Path(pdf_path)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        self.logger.debug(f"Saved PDF to {pdf_path}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def download_pdf(self, paper: Dict) -> str:
        """
        Download PDF from the given URL.

        :param paper: Paper data
        :return: Path to the downloaded PDF file
        """
        response = requests.get(paper["paper_url"])
        response.raise_for_status()
        pdf_path = self.make_pdf_cache_path_from_paper_id(paper["paper_id"])
        self.write_pdf_to_cache(pdf_path, response.content)
        self.logger.debug(f"Downloaded PDF from {paper["paper_url"]} to {pdf_path}")
        return str(pdf_path)

    def get_pdf_text(self, paper: Dict) -> str:
        """
        Get the text content of a PDF file.

        :param paper: Paper data
        :return: Extracted text from the PDF
        """
        pdf_path = self.make_pdf_cache_path_from_paper_id(paper["paper_id"])
        if not pdf_path.exists():
            pdf_path = self.download_pdf(paper)
        return self.extract_text(pdf_path)

    def extract_paper_id(self, url: str) -> str:
        """
        Extract the paper ID from the full URL.

        :param url: Full URL of the paper
        :return: Extracted paper ID
        """
        return os.path.basename(urlparse(url).path)

    def make_pdf_cache_path_from_paper_id(self, id: str) -> str:
        """
        Make a cache patch from the paper ID.

        :param id: ID of the paper
        :return: Full path to the PDF in the cache
        """
        self.ensure_directory_exists(self.pdf_cache_dir)
        return Path(self.pdf_cache_dir) / self.make_pdf_name_from_paper_id(id)

    def make_pdf_name_from_paper_id(self, id: str) -> str:
        """
        Make a PDF name from the paper ID.

        :param id: ID of the paper
        :return: Name of the PDF file
        """
        return f"{id}.pdf"

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from the PDF file.

        :param pdf_path: Path to the PDF file
        :return: Extracted text
        """
        self.logger.debug(f"Extracting text from {pdf_path}")
        try:
            return pymupdf4llm.to_markdown(pdf_path)
        except Exception as e:
            message = f"Error extracting {pdf_path} content with pymupdf4llm: {str(e)}"
            self.logger.error(message)
            raise

    def extract_xml(self, content: str) -> Optional[str]:
        """
        Extract XML content from the paper content.

        :param content: Paper content
        :return: Extracted XML content or None if not found
        """
        match = re.search(
            r"<results>(?:(?!</results>).)*</results>", content, re.DOTALL
        )
        return match.group(0) if match else None

    def create_database(self) -> None:
        """
        Conditionally creates an SQLite database with the required tables and columns.

        This method connects to the SQLite database specified by self.database,
        creates the necessary tables if they don't exist, and handles any errors
        that may occur during the process.

        Raises:
            sqlite3.Error: If there's an issue with the SQLite operations.
        """
        db_path = Path(self.database)
        self.logger.info(f"Creating/connecting to database: {db_path}")

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.executescript(constants.CREATE_TABLES_QUERY)
                conn.commit()
            self.logger.info(f"Database '{db_path}' is ready.")
        except sqlite3.Error as e:
            self.logger.error(
                f"An error occurred while creating database {db_path}: {e}"
            )
            raise

    def fetch_papers_by_processing_status(self, status: str, order_by: Optional[str] = "RANDOM()", limit: Optional[int] = 1) -> Generator[sqlite3.Row, None, None]:
        """
        Fetch papers from the database, by processing status and order them by the given field.

        :param status: Processing status of the papers to fetch
        :param order_by: Field to order the papers by
        :param limit: Maximum number of papers to fetch

        :return: List of dictionaries containing paper information
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            query = f"""
            SELECT id, paper_id, paper_url
            FROM papers
            WHERE processing_status = ?
            ORDER BY {order_by}
            """
            params = (status,)
            if limit is not None:
                query += " LIMIT ?"
                params += (limit,)
            with get_db_connection(self.database) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                for row in cursor:
                    yield row
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_paper(self, paper_id: str, data: Dict[str, int]) -> None:
        """
        Update the data of a paper in the database.

        :param paper_id: ID of the paper
        :param data: Dictionary of fields and their new values
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()

            if data:
                update_fields = ", ".join(
                    [f"{field} = ?" for field in data.keys()]
                )
                update_query = f"""
                UPDATE papers SET
                    {update_fields}
                WHERE id = ?
                """
                update_values = tuple(data.values()) + (paper_id,)
                cursor.execute(update_query, update_values)
                conn.commit()
                self.logger.debug(f"Updated paper {paper_id} with {data}")
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_paper_status(self, paper_id: str, status: str) -> None:
        """
        Update the processing status and criteria of the paper in the database.

        :param paper_id: ID of the paper
        :param status: New processing status
        """
        self.update_paper(paper_id, {"processing_status": status})

    def ensure_directory_exists(self, directory: Path | str) -> None:
        """
        Ensure that the training artifacts directory exists.

        :param directory: Path to the directory
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

    def write_inference_artifact(
        self, filename: Dict, content: str
    ) -> None:
        """
        Write inference artifact to a file.

        :param paper: Paper data
        :param content: Content of the inference artifact
        """
        self.ensure_directory_exists(self.inference_artifacts_directory)
        artifact_file_path = (
            Path(self.inference_artifacts_directory) / filename
        )
        with open(artifact_file_path, "w") as file:
            file.write(content)
        self.logger.debug(f"Wrote inference artifact to {artifact_file_path}")
