import logging
import os
import signal
import requests
import email.parser
import email.message
from email.policy import Compat32
import email.errors
from pathlib import Path
import sqlite3
import json
import pymupdf4llm
import re
from datetime import datetime
from contextlib import contextmanager
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import textwrap
from typing import Union, Optional, List, Dict, Generator, Any, Tuple
from datetime import timedelta
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
def timeout(seconds):
    def handler(signum, frame):
        raise TimeoutError()

    # Register the signal function handler
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)


@contextmanager
def get_db_connection(
    database_path: Union[str, Path]
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections with WAL journaling and IMMEDIATE isolation.

    Provides a context-managed SQLite database connection with Write-Ahead Logging (WAL)
    journal mode and IMMEDIATE isolation level for better concurrency handling.

    :param database_path: Path to the SQLite database file
    :type database_path: Union[str, Path]
    :yield: SQLite connection object configured with WAL and IMMEDIATE isolation
    :rtype: Generator[sqlite3.Connection, None, None]
    :raises FileNotFoundError: If database directory doesn't exist
    """
    path = Path(database_path)
    if not path.parent.exists():
        raise FileNotFoundError(f"Database directory does not exist: {path.parent}")
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.isolation_level = "IMMEDIATE"
    try:
        yield conn
    finally:
        conn.close()


class Utils:
    """Utility class for various operations in the raspberry_paper_to_cot_pipeline."""

    # Custom email policy with minimal settings
    EMAIL_POLICY = Compat32(linesep="\n")

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
        """Initialize the Utils class with configuration parameters.

        Sets up utility class with database connection, artifact directories,
        and logging configuration.

        :param database: Path to the SQLite database file
        :type database: Optional[str]
        :param inference_artifacts_directory: Directory for storing inference artifacts
        :type inference_artifacts_directory: Optional[str]
        :param training_artifacts_directory: Directory for storing training artifacts
        :type training_artifacts_directory: Optional[str]
        :param pdf_cache_dir: Directory for caching downloaded PDF files
        :type pdf_cache_dir: Optional[str]
        :param lwe_default_preset: Default preset configuration for LWE
        :type lwe_default_preset: Optional[str]
        :param logger: Custom logger instance
        :type logger: Optional[logging.Logger]
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
        """Set up logging configuration for a specific logger.

        Configures a logger with appropriate handlers and formatting based on debug level.
        If a logger with the given name already exists, returns the existing instance.

        :param logger_name: Name of the logger to configure
        :type logger_name: str
        :param debug: Whether to enable debug logging
        :type debug: bool
        :return: Configured logger instance
        :rtype: logging.Logger
        """
        logger = logging.getLogger(logger_name)
        if logger.handlers:
            return logger
        logging.getLogger().addHandler(logging.NullHandler())
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
        """Set up LWE configuration and API backend.

        Initializes and configures the LWE backend with default settings.

        :return: Configured LWE API backend instance
        :rtype: ApiBackend
        """
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
        """Run the LWE template with the given variables.

        :param template: Template name
        :type template: str
        :param template_vars: Template variables
        :type template_vars: Dict[str, Any]
        :param overrides: Optional overrides for the template
        :type overrides: Optional[Dict[str, Any]]
        :return: Response on success
        :rtype: str
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
        """Write PDF content to cache.

        Saves PDF binary content to the specified cache location, creating
        directories as needed.

        :param pdf_path: Path where the PDF should be saved
        :type pdf_path: Path
        :param pdf_content: Binary content of the PDF file
        :type pdf_content: bytes
        """
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(pdf_content)
        self.logger.debug(f"Saved PDF to {pdf_path}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def download_pdf(self, paper: Union[Dict[str, Any], sqlite3.Row]) -> str:
        """Download PDF from the given URL.

        Downloads a paper's PDF and saves it to the cache directory. Implements
        retry logic for resilient downloading.

        :param paper: Paper record containing 'paper_url' and 'paper_id' fields
        :type paper: Union[Dict[str, Any], sqlite3.Row]
        :return: String path to the downloaded PDF file
        :rtype: str
        """
        response = requests.get(paper["paper_url"])
        response.raise_for_status()
        pdf_path = self.make_pdf_cache_path_from_paper_id(paper["paper_id"])
        self.write_pdf_to_cache(pdf_path, response.content)
        self.logger.debug(
            f"Successfully downloaded PDF from {paper['paper_url']} and saved to {pdf_path} ({os.path.getsize(pdf_path)} bytes)"
        )
        return str(pdf_path)

    def get_pdf_text(self, paper: Union[Dict[str, Any], sqlite3.Row]) -> str:
        """Get the text content of a PDF file.

        Retrieves PDF content either from cache or by downloading, then extracts text.

        :param paper: Paper record containing 'paper_id' field
        :type paper: Union[Dict[str, Any], sqlite3.Row]
        :return: Extracted text content from the PDF
        :rtype: str
        """
        pdf_path = self.make_pdf_cache_path_from_paper_id(paper["paper_id"])
        if not pdf_path.exists():
            pdf_path = Path(self.download_pdf(paper))
        return self.extract_text(str(pdf_path))

    def extract_paper_id(self, url: str) -> str:
        """Extract the paper ID from the full URL.

        Parses a paper's URL to extract its unique identifier.

        :param url: Complete URL of the paper
        :type url: str
        :return: Paper's unique identifier
        :rtype: str
        """
        return Path(urlparse(url).path).name

    def make_pdf_cache_path_from_paper_id(self, id: str) -> Path:
        """Make a cache path from the paper ID.

        Constructs the full filesystem path for a paper's cached PDF file.

        :param id: Unique identifier of the paper
        :type id: str
        :return: Full path where the PDF should be cached
        :rtype: Path
        """
        self.ensure_directory_exists(self.pdf_cache_dir)
        return self.pdf_cache_dir / self.make_pdf_name_from_paper_id(id)

    def make_pdf_name_from_paper_id(self, id: str) -> str:
        """Make a PDF filename from the paper ID.

        Constructs the filename for a paper's PDF using its identifier.

        :param id: Unique identifier of the paper
        :type id: str
        :return: Generated PDF filename
        :rtype: str
        """
        return f"{id}.pdf"

    def _get_text_cache_path(self, pdf_path: Union[str, Path]) -> Path:
        """Get the cache file path for extracted text.

        :param pdf_path: Path to the PDF file
        :type pdf_path: Union[str, Path]
        :return: Path where cached text should be stored
        :rtype: Path
        """
        pdf_path = Path(pdf_path)
        return pdf_path.with_suffix(".md")

    def _read_cached_text(self, cache_path: Path) -> Optional[str]:
        """Read cached text if it exists.

        :param cache_path: Path to the cached text file
        :type cache_path: Path
        :return: Cached text if found, None otherwise
        :rtype: Optional[str]
        """
        if cache_path.exists():
            self.logger.debug(f"Found cached text at {cache_path}")
            return cache_path.read_text()
        return None

    def _write_text_cache(self, cache_path: Path, text: str) -> None:
        """Write extracted text to cache.

        :param cache_path: Path where to write the cache
        :type cache_path: Path
        :param text: Extracted text to cache
        :type text: str
        """
        cache_path.write_text(text)
        self.logger.debug(f"Cached extracted text to {cache_path}")

    def _perform_text_extraction(self, pdf_path: Path) -> str:
        """Perform the actual text extraction from PDF.

        :param pdf_path: Path to the PDF file
        :type pdf_path: Path
        :return: Extracted text
        :rtype: str
        :raises RuntimeError: If an unexpected error occurs, user interrupts, or operation times out
        """
        self.logger.debug(f"Extracting text from {pdf_path} (will time out in {constants.UTIL_PDF_TO_MARKDOWN_TIMEOUT_SECONDS} seconds)")
        try:
            with timeout(constants.UTIL_PDF_TO_MARKDOWN_TIMEOUT_SECONDS):
                chunks = pymupdf4llm.to_markdown(
                    str(pdf_path),
                    page_chunks=True,
                    graphics_limit=5000,
                    write_images=False,
                )
                text_chunks = [chunk["text"] for chunk in chunks]
                text = "\n\n".join(text_chunks).strip()
                return text
        except TimeoutError:
            message = f"PDF extraction timed out after {constants.UTIL_PDF_TO_MARKDOWN_TIMEOUT_SECONDS} seconds for {pdf_path}"
            self.logger.error(message)
            raise RuntimeError(message)
        except KeyboardInterrupt:
            message = f"User interrupted PDF extraction for {pdf_path}"
            self.logger.error(message)
            raise RuntimeError(message)
        except Exception as e:
            message = f"PDF conversion error for {pdf_path} content: {str(e)}"
            self.logger.error(message)
            raise RuntimeError(message)

    def extract_text(self, pdf_path: Union[str, Path]) -> str:
        """Extract text from the PDF file, using cache if available.

        :param pdf_path: Path to the PDF file
        :type pdf_path: Union[str, Path]
        :return: Extracted text
        :rtype: str
        :raises FileNotFoundError: If PDF file doesn't exist
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        cache_path = self._get_text_cache_path(path)
        cached_text = self._read_cached_text(cache_path)

        if cached_text is not None:
            return cached_text

        extracted_text = self._perform_text_extraction(path)
        self._write_text_cache(cache_path, extracted_text)

        return extracted_text

    def extract_xml(self, content: str) -> Optional[str]:
        """Extract XML content from the paper content.

        Searches for and extracts XML content enclosed in <results> tags.

        :param content: Full text content to search for XML
        :type content: str
        :return: Extracted XML string if found, None otherwise
        :rtype: Optional[str]
        """
        match = re.search(
            r"<results>(?:(?!</results>).)*</results>", content, re.DOTALL
        )
        return match.group(0) if match else None

    def clean_extracted_text(self, text: str) -> str:
        """Clean extracted text by removing indentation and extra whitespace.

        :param text: Text to clean
        :type text: str
        :return: Cleaned text
        :rtype: str
        """
        return textwrap.dedent(text).strip()

    def extract_question_chain_of_reasoning_answer(
        self, content: str
    ) -> Tuple[str, str, str]:
        """Parse the content to extract question, chain of reasoning, and answer.

        :param content: The content string containing XML to parse
        :type content: str
        :return: Tuple containing (question, chain_of_reasoning, answer)
        :rtype: Tuple[str, str, str]
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

        # Question doesn't exist in voicing, so make it optional
        if None in (chain_elem, answer_elem):
            raise AttributeError("Required XML elements missing")

        question = self.clean_extracted_text(
            question_elem.text if question_elem is not None else ""
        )
        chain_of_reasoning = self.clean_extracted_text(chain_elem.text)
        answer = self.clean_extracted_text(answer_elem.text)

        return question, chain_of_reasoning, answer

    def extract_question_chain_of_reasoning_answer_from_artifact(
        self, paper: sqlite3.Row, artifact_pattern: str
    ) -> Optional[Tuple[str, str, str]]:
        """
        Retrieve refined question, reasoning chain, and answer from paper artifact.

        Attempts to load and parse the artifact file for the given paper
        to extract the core components needed for voice transformation.

        :param paper: Database row containing paper metadata including paper_id
        :type paper: sqlite3.Row
        :param artifact_pattern: Pattern for the artifact file name
        :type artifact_pattern: str
        :return: Tuple containing (question, chain_of_reasoning, answer) if successful, None otherwise
        :rtype: Optional[Tuple[str, str, str]]
        """
        try:
            artifact_name = artifact_pattern.format(paper_id=paper["paper_id"])
            _, content = self.read_inference_artifact(artifact_name)
            return self.extract_question_chain_of_reasoning_answer(content)
        except (FileNotFoundError, ValueError, email.errors.MessageParseError) as e:
            self.logger.error(
                f"Failed to get data from artifact {artifact_name} for paper {paper['paper_id']}: {str(e)}"
            )
            return None

    def format_duration(self, seconds: float) -> str:
        """Format duration in seconds to a human readable string.

        :param seconds: Duration in seconds
        :type seconds: float
        :return: Formatted duration string (e.g., "2h 15m 30s")
        :rtype: str
        """
        duration = timedelta(seconds=seconds)
        hours = duration.seconds // 3600 + duration.days * 24
        minutes = (duration.seconds % 3600) // 60
        secs = duration.seconds % 60
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    def create_database(self) -> None:
        """Conditionally creates an SQLite database with the required tables and columns.

        :raises sqlite3.Error: If there's an issue with the SQLite operations
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
        status: str = constants.STATUS_PAPER_LINK_DOWNLOADED,
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
          WHERE p.processing_status = ?
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
        params: tuple = (status,)
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
        """Ensure that the directory exists.

        Creates the directory and any necessary parent directories if they don't exist.

        :param directory: Path to the directory to create
        :type directory: Path
        """
        directory.mkdir(parents=True, exist_ok=True)

    def read_inference_artifact(self, filename: str) -> Tuple[Dict[str, str], str]:
        """Read and parse an inference artifact file in RFC 5322 format.

        :param filename: Name of the inference artifact file
        :type filename: str
        :return: Tuple of (headers dict, content string)
        :rtype: Tuple[Dict[str, str], str]
        :raises FileNotFoundError: If the artifact file doesn't exist
        :raises email.errors.MessageParseError: If the file isn't valid RFC 5322 format
        """
        artifact_file_path = self.inference_artifacts_directory / filename
        try:
            raw_content = artifact_file_path.read_text()
            parser = email.parser.Parser(policy=self.EMAIL_POLICY)
            msg = parser.parsestr(raw_content)
            headers = dict(msg.items())
            content = msg.get_payload()
            self.logger.debug(
                f"Successfully read inference artifact from {artifact_file_path} "
                f"({len(headers)} headers, {len(content)} characters)"
            )
            return headers, content
        except FileNotFoundError:
            self.logger.error(f"Artifact file {artifact_file_path} not found")
            raise
        except email.errors.MessageParseError as e:
            self.logger.error(f"Failed to parse RFC 5322 format: {e}")
            raise

    def write_inference_artifact(
        self, filename: str, headers: Dict[str, str], content: str
    ) -> None:
        """Write an inference artifact file in RFC 5322 format.

        :param filename: Name of the file to write
        :type filename: str
        :param headers: Dictionary of header fields and values
        :type headers: Dict[str, str]
        :param content: Content body to write
        :type content: str
        """
        msg = email.message.EmailMessage(policy=self.EMAIL_POLICY)
        try:
            for name, value in headers.items():
                msg[name] = value
        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid RFC 5322 header format: {e}")
            raise ValueError(f"Invalid RFC 5322 header format: {e}")
        # Set content directly as plain text
        msg.set_payload(content)
        self.ensure_directory_exists(self.inference_artifacts_directory)
        artifact_file_path = self.inference_artifacts_directory / filename
        artifact_file_path.write_text(msg.as_string())
        self.logger.debug(
            f"Wrote inference artifact to {artifact_file_path} "
            f"({len(headers)} headers, {len(content)} characters)"
        )

    def write_training_artifact(self, filename: str, content: str) -> None:
        """Write training artifact to a file.

        Saves training artifact content as JSON to a file in the training artifacts directory.

        :param filename: Name of the file to write
        :type filename: str
        :param content: Content to serialize and write to the file
        :type content: str
        """
        self.ensure_directory_exists(self.training_artifacts_directory)
        artifact_file_path = self.training_artifacts_directory / filename
        artifact_file_path.write_text(json.dumps(content))
        self.logger.debug(f"Wrote training artifact to {artifact_file_path}")

    def read_training_artifact(self, filename: str) -> Dict[str, Any]:
        """Read training artifact from a file.

        :param filename: Name of the file to read
        :type filename: str
        :return: Deserialized content of the training artifact
        :rtype: Dict[str, Any]
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
            self.logger.error(
                f"Invalid JSON in training artifact {artifact_file_path}: {e}"
            )
            raise

    def validate_date(self, date_str: str, date_name: str) -> None:
        """Validate the format of a date string.

        :param date_str: The date string to validate
        :type date_str: str
        :param date_name: The name of the date parameter (for error reporting)
        :type date_name: str
        :raises ValueError: If the date format is invalid
        """
        self.logger.debug(f"Validating {date_name}: {date_str}")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self.logger.error(f"Invalid date format for {date_name}. Use YYYY-MM-DD.")
            raise ValueError(f"Invalid date format for {date_name}")

    def fetch_arxiv_categories(self) -> Dict[str, str]:
        """Fetch arXiv categories from the official taxonomy page.

        :return: Dictionary of category codes and names, or empty dict if no categories found
        :rtype: Dict[str, str]
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
        """Fetch papers from the database using a custom query.

        :param query: Custom SQL query to execute
        :type query: str
        :param params: Tuple of parameters for the query
        :type params: tuple
        :return: Generator of dictionaries containing paper information
        :rtype: Generator[sqlite3.Row, None, None]
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

    def get_paper_categories(
        self, paper: sqlite3.Row, stringify: bool = True
    ) -> Union[List[str], str]:
        """Get all categories for a specific paper.

        :param paper: Database row containing paper information
        :type paper: sqlite3.Row
        :param stringify: Whether to return categories as comma-separated string
        :type stringify: bool
        :return: List of categories or comma-separated string of categories
        :rtype: Union[List[str], str]
        :raises sqlite3.Error: If there's an issue with the database operations
        """
        query = """
        SELECT category
        FROM paper_categories
        WHERE paper_id = ?
        ORDER BY category
        """
        try:
            with get_db_connection(self.database) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (paper["id"],))
                categories = [row[0] for row in cursor.fetchall()]
                return ", ".join(categories) if stringify else categories
        except sqlite3.Error as e:
            self.logger.error(
                f"Database error fetching categories for paper {paper['id']}: {e}"
            )
            raise
