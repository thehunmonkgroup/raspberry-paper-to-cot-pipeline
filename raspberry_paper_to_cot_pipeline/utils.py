import logging
import requests
import sqlite3
import json
import pymupdf4llm
import re
from datetime import datetime
from contextlib import contextmanager
from urllib.parse import urlparse
from pathlib import Path
import xml.etree.ElementTree as ET
import textwrap
from typing import Optional, List, Dict, Generator, Any, Tuple
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from lwe.core.config import Config
from lwe import ApiBackend
from raspberry_paper_to_cot_pipeline import constants


@contextmanager
def get_db_connection(database_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections with WAL journaling and IMMEDIATE isolation.

    :param database_path: Path to the SQLite database
    :yield: SQLite connection object configured with Write-Ahead Logging (WAL)
           journal mode and IMMEDIATE isolation level for better concurrency
    :raises sqlite3.Error: If connection cannot be established
    """
    conn = sqlite3.connect(database_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.isolation_level = "IMMEDIATE"
    try:
        yield conn
    finally:
        conn.close()


class Utils:
    """Utility class for various operations in the raspberry_paper_to_cot_pipeline."""

    def __init__(
        self,
        database: Optional[str] = constants.DEFAULT_DB_NAME,
        inference_artifacts_directory: Optional[
            str
        ] = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        training_artifacts_directory: Optional[
            str
        ] = constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        pdf_cache_dir: Optional[str] = constants.DEFAULT_PDF_CACHE_DIR,
        lwe_default_preset: Optional[str] = constants.DEFAULT_LWE_PRESET,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Utils class.

        :param database: Path to the SQLite database
        :param inference_artifacts_directory: Directory for inference artifacts
        :param training_artifacts_directory: Directory for training artifacts
        :param pdf_cache_dir: Directory for caching PDFs
        :param lwe_default_preset: Default preset for LWE
        :param logger: Logger object
        """
        self.database = database
        self.inference_artifacts_directory = Path(inference_artifacts_directory)
        self.training_artifacts_directory = Path(training_artifacts_directory)
        self.pdf_cache_dir = Path(pdf_cache_dir)
        self.lwe_default_preset = lwe_default_preset
        self.logger = logger if logger else self.setup_logging("Utils", False)
        self.lwe_backend: Optional[ApiBackend] = None

    @staticmethod
    def setup_logging(logger_name: str, debug: bool) -> logging.Logger:
        """Set up logging configuration for a specific logger."""
        logging.getLogger().addHandler(logging.NullHandler())
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        logger.propagate = False
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def setup_lwe(self) -> ApiBackend:
        """Set up LWE configuration and API backend."""
        config = Config(
            config_dir=str(constants.LWE_CONFIG_DIR),
            data_dir=str(constants.LWE_DATA_DIR),
        )
        config.load_from_file()
        config.set("model.default_preset", self.lwe_default_preset)
        self.lwe_backend = ApiBackend(config)
        self.lwe_backend.set_return_only(True)
        return self.lwe_backend

    def run_lwe_template(
        self,
        template: str,
        template_vars: Dict[str, Any],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Run the LWE template with the given variables.

        :param template: Template name
        :param template_vars: Template variables
        :param overrides: Optional overrides for the template
        :return: Response on success
        :raises RuntimeError: If LWE backend is not initialized or template execution fails
        """
        if self.lwe_backend is None:
            raise RuntimeError("LWE backend not initialized")
        overrides = overrides or {}
        success, response, user_message = self.lwe_backend.run_template(
            template, template_vars, overrides
        )
        if not success:
            message = f"Error running LWE template: {user_message}"
            self.logger.error(message)
            raise RuntimeError(message)
        return response

    def write_pdf_to_cache(self, pdf_path: Path, pdf_content: bytes) -> None:
        """
        Write PDF content to cache.

        :param pdf_path: Path to the PDF file
        :param pdf_content: Content of the PDF file
        """
        pdf_path.write_bytes(pdf_content)
        self.logger.debug(f"Saved PDF to {pdf_path}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def download_pdf(self, paper: Dict[str, Any]) -> str:
        """
        Download PDF from the given URL.

        :param paper: Paper data
        :return: Path to the downloaded PDF file
        :raises requests.RequestException: If the download fails after retries
        """
        response = requests.get(paper["paper_url"])
        response.raise_for_status()
        pdf_path = self.make_pdf_cache_path_from_paper_id(paper["paper_id"])
        self.write_pdf_to_cache(pdf_path, response.content)
        self.logger.debug(f"Downloaded PDF from {paper['paper_url']} to {pdf_path}")
        return str(pdf_path)

    def get_pdf_text(self, paper: Dict[str, Any]) -> str:
        """
        Get the text content of a PDF file.

        :param paper: Paper data
        :return: Extracted text from the PDF
        """
        pdf_path = self.make_pdf_cache_path_from_paper_id(paper["paper_id"])
        if not pdf_path.exists():
            pdf_path = Path(self.download_pdf(paper))
        return self.extract_text(str(pdf_path))

    def extract_paper_id(self, url: str) -> str:
        """
        Extract the paper ID from the full URL.

        :param url: Full URL of the paper
        :return: Extracted paper ID
        """
        return Path(urlparse(url).path).name

    def make_pdf_cache_path_from_paper_id(self, id: str) -> Path:
        """
        Make a cache path from the paper ID.

        :param id: ID of the paper
        :return: Full path to the PDF in the cache
        """
        self.ensure_directory_exists(self.pdf_cache_dir)
        return self.pdf_cache_dir / self.make_pdf_name_from_paper_id(id)

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
        :raises FileNotFoundError: If PDF file doesn't exist
        :raises pymupdf4llm.ConversionError: If PDF conversion fails
        :raises RuntimeError: If an unexpected error occurs
        """
        self.logger.debug(f"Extracting text from {pdf_path}")
        try:
            return pymupdf4llm.to_markdown(pdf_path)
        except FileNotFoundError as e:
            message = f"PDF file not found at {pdf_path}: {str(e)}"
            self.logger.error(message)
            raise
        except pymupdf4llm.ConversionError as e:
            message = f"PDF conversion error for {pdf_path}: {str(e)}"
            self.logger.error(message)
            raise
        except Exception as e:
            message = f"Unexpected error extracting {pdf_path} content: {str(e)}"
            self.logger.error(message)
            raise RuntimeError(message)

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

    def extract_question_chain_of_reasoning_answer(
        self, content: str
    ) -> Tuple[str, str, str]:
        """
        Parse the content to extract question, chain of reasoning, and answer.

        :param content: The content string containing XML to parse
        :return: Tuple of (question, chain_of_reasoning, answer)
        :raises ValueError: If XML content cannot be extracted
        :raises AttributeError: If required XML elements are missing
        """
        xml_string = self.extract_xml(content)
        if not xml_string:
            raise ValueError("Could not extract XML content")
        root = ET.fromstring(xml_string)

        question_elem = root.find(".//question")
        chain_elem = root.find(".//chain_of_reasoning")
        answer_elem = root.find(".//answer")

        if None in (question_elem, chain_elem, answer_elem):
            raise AttributeError("Required XML elements missing")

        question = question_elem.text.strip()
        chain_of_reasoning = textwrap.dedent(chain_elem.text).strip()
        answer = answer_elem.text.strip()
        return question, chain_of_reasoning, answer

    def create_database(self) -> None:
        """
        Conditionally creates an SQLite database with the required tables and columns.

        :raises sqlite3.Error: If there's an issue with the SQLite operations.
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

    def fetch_papers_by_processing_status(
        self,
        status: str,
        select_columns: Optional[List[str]] = constants.DEFAULT_FETCH_BY_STATUS_COLUMNS,
        order_by: Optional[str] = "RANDOM()",
        limit: Optional[int] = 1,
    ) -> Generator[sqlite3.Row, None, None]:
        """
        Fetch papers from the database, by processing status and order them by the given field.

        :param status: Processing status of the papers to fetch
        :param select_columns: Columns to select from the database
        :param order_by: Field to order the papers by
        :param limit: Maximum number of papers to fetch
        :return: Generator of dictionaries containing paper information
        :raises sqlite3.Error: If there's an issue with the database operations
        """
        columns = ", ".join(select_columns)
        query = f"""
        SELECT {columns}
        FROM papers
        WHERE processing_status = ?
        ORDER BY {order_by}
        """
        params: tuple = (status,)
        if limit is not None:
            query += " LIMIT ?"
            params += (limit,)

        try:
            with get_db_connection(self.database) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                yield from cursor
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise

    def fetch_papers_by_processing_status_balanced_by_category(
        self,
        status: str = constants.STATUS_PAPER_LINK_VERIFIED,
        limit: int = 1,
    ) -> Generator[sqlite3.Row, None, None]:
        """
        Fetch papers from the database, by processing status, balancing them by category.

        :param status: Processing status of the papers to fetch
        :param limit: Maximum number of papers to fetch per category
        :return: Generator of dictionaries containing paper information
        :raises sqlite3.Error: If there's an issue with the database operations
        """
        query = f"""
        WITH RECURSIVE
        vars(papers_per_category) AS (
          SELECT {limit}
        ),
        ranked_papers AS (
          SELECT
            pc.category,
            p.id,
            p.paper_id,
            p.paper_url,
            ROW_NUMBER() OVER (PARTITION BY pc.category ORDER BY RANDOM()) AS category_row_num,
            ROW_NUMBER() OVER (ORDER BY RANDOM()) AS global_row_num
          FROM paper_categories pc
          JOIN papers p ON pc.paper_id = p.id
          WHERE p.processing_status = '{status}'
        ),
        selected_papers AS (
          SELECT category, id, paper_id, paper_url, category_row_num, global_row_num
          FROM ranked_papers, vars
          WHERE category_row_num <= vars.papers_per_category
        ),
        final_selection AS (
          SELECT
            category,
            id,
            paper_id,
            paper_url,
            category_row_num,
            ROW_NUMBER() OVER (PARTITION BY paper_url ORDER BY global_row_num) AS url_row_num
          FROM selected_papers
        )
        SELECT category, id, paper_id, paper_url
        FROM final_selection
        WHERE url_row_num = 1
        ORDER BY category, category_row_num;
        """
        params: tuple = (status, limit)
        try:
            with get_db_connection(self.database) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                yield from cursor
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise

    def update_paper(self, paper_id: str, data: Dict[str, Any]) -> None:
        """
        Update the data of a paper in the database.

        :param paper_id: ID of the paper
        :param data: Dictionary of fields and their new values
        :raises sqlite3.Error: If there's an issue with the database operations
        """
        try:
            with get_db_connection(self.database) as conn:
                cursor = conn.cursor()

                if data:
                    update_fields = ", ".join([f"{field} = ?" for field in data.keys()])
                    update_query = f"""
                    UPDATE papers SET
                        {update_fields}
                    WHERE id = ?
                    """
                    update_values = tuple(data.values()) + (paper_id,)
                    self.logger.debug(
                        f"Executing update query for paper {paper_id}:\n"
                        f"Query: {update_query}\n"
                        f"Values: {update_values}"
                    )
                    cursor.execute(update_query, update_values)
                    conn.commit()
                    self.logger.debug(
                        f"Successfully updated paper {paper_id} with {len(data)} fields: {list(data.keys())}"
                    )
        except sqlite3.Error as e:
            self.logger.error(
                f"Database error updating paper {paper_id} with fields {list(data.keys())}: {e}"
            )
            raise

    def update_paper_status(self, paper_id: str, status: str) -> None:
        """
        Update the processing status of the paper in the database.

        :param paper_id: ID of the paper
        :param status: New processing status
        """
        self.update_paper(paper_id, {"processing_status": status})

    def ensure_directory_exists(self, directory: Path) -> None:
        """
        Ensure that the directory exists.

        :param directory: Path to the directory
        """
        directory.mkdir(parents=True, exist_ok=True)

    def read_inference_artifact(self, filename: str) -> str:
        """
        Read inference artifact from a file.

        :param filename: Name of the file to read
        """
        artifact_file_path = self.inference_artifacts_directory / filename
        try:
            content = artifact_file_path.read_text()
            self.logger.debug(f"Read inference artifact from {artifact_file_path}")
            return content
        except FileNotFoundError:
            self.logger.error(f"Artifact file {artifact_file_path} not found")
            raise

    def write_inference_artifact(self, filename: str, content: str) -> None:
        """
        Write inference artifact to a file.

        :param filename: Name of the file to write
        :param content: Content of the inference artifact
        """
        self.ensure_directory_exists(self.inference_artifacts_directory)
        artifact_file_path = self.inference_artifacts_directory / filename
        artifact_file_path.write_text(content)
        self.logger.debug(f"Wrote inference artifact to {artifact_file_path}")

    def write_training_artifact(self, filename: str, content: str) -> None:
        """
        Write training artifact to a file.

        :param filename: Name of the file to write
        :param content: Content of the training artifact
        """
        self.ensure_directory_exists(self.training_artifacts_directory)
        artifact_file_path = self.training_artifacts_directory / filename
        artifact_file_path.write_text(json.dumps(content))
        self.logger.debug(f"Wrote training artifact to {artifact_file_path}")

    def read_training_artifact(self, filename: str) -> Dict[str, Any]:
        """
        Read training artifact from a file.

        :param filename: Name of the file to read
        :return: Deserialized content of the training artifact
        :raises FileNotFoundError: If the artifact file doesn't exist
        :raises json.JSONDecodeError: If the file contains invalid JSON
        """
        artifact_file_path = self.training_artifacts_directory / filename
        try:
            content = artifact_file_path.read_text()
            self.logger.debug(f"Read training artifact from {artifact_file_path}")
            return json.loads(content)
        except FileNotFoundError:
            self.logger.error(f"Training artifact file {artifact_file_path} not found")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in training artifact {artifact_file_path}: {e}")
            raise

    def validate_date(self, date_str: str, date_name: str) -> None:
        """
        Validate the format of a date string.

        :param date_str: The date string to validate
        :param date_name: The name of the date parameter (for error reporting)
        :raises ValueError: If the date format is invalid
        :return: None on successful validation
        """
        self.logger.debug(f"Validating {date_name}: {date_str}")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self.logger.error(f"Invalid date format for {date_name}. Use YYYY-MM-DD.")
            raise ValueError(f"Invalid date format for {date_name}")

    def fetch_arxiv_categories(self) -> Dict[str, str]:
        """
        Fetch arXiv categories from the official taxonomy page.

        :return: Dictionary of category codes and names, or empty dict if no categories found
        :raises requests.RequestException: If there's an error fetching the categories
        :raises BeautifulSoup.ParserError: If there's an error parsing the HTML
        """
        self.logger.debug("Fetching arXiv taxonomy")
        try:
            response = requests.get(constants.ARXIV_TAXONOMY_URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            categories = {}
            taxonomy_list = soup.find("div", id="category_taxonomy_list")
            if not taxonomy_list:
                self.logger.warning("No taxonomy list found in arXiv page")
                return {}

            for accordion_body in taxonomy_list.find_all(
                "div", class_="accordion-body"
            ):
                for column in accordion_body.find_all(
                    "div", class_="column is-one-fifth"
                ):
                    h4 = column.find("h4")
                    if h4:
                        category_code = h4.contents[0].strip()
                        category_name = (
                            h4.find("span").text.strip() if h4.find("span") else ""
                        )
                        category_name = category_name.strip("()")
                        if category_code and category_name:
                            categories[category_code] = category_name

            self.logger.debug(f"Found {len(categories)} categories")
            return categories
        except Exception as e:
            self.logger.error(f"Error parsing arXiv taxonomy: {e}")
            raise

    def fetch_papers_by_custom_query(
        self, query: str, params: tuple
    ) -> Generator[sqlite3.Row, None, None]:
        """
        Fetch papers from the database using a custom query.

        :param query: Custom SQL query to execute
        :param params: Tuple of parameters for the query
        :return: Generator of dictionaries containing paper information
        :raises sqlite3.Error: If there's an issue with the database operations
        """
        try:
            with get_db_connection(self.database) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                yield from cursor
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
