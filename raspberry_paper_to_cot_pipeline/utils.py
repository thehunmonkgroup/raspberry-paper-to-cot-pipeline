import logging
import requests
import pymupdf4llm
import re
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from lwe.core.config import Config
from lwe import ApiBackend


class Utils:
    def __init__(self, logger=None):
        self.logger = logger if logger else self.setup_logging("Utils", False)

    @staticmethod
    def setup_logging(logger_name: str, debug: bool) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(logger_name)

    def setup_lwe(self, default_preset: str) -> ApiBackend:
        """Set up LWE configuration and API backend."""
        config = Config()
        config.load_from_file()
        config.set("debug.log.enabled", True)
        config.set("model.default_preset", default_preset)
        lwe_backend = ApiBackend(config)
        lwe_backend.set_return_only(True)
        return lwe_backend

    def run_lwe_template(self, lwe_backend: ApiBackend, template: str, template_vars: dict) -> Tuple[bool, str, str]:
        """
        Run the LWE template with the given variables.

        :param lwe_backend: LWE API backend
        :param template: Template name
        :param template_vars: Template variables
        :return: Response on success
        """
        success, response, user_message = lwe_backend.run_template(template, template_vars)
        if not success:
            message = f"Error running LWE template: {user_message}"
            self.logger.error(message)
            raise RuntimeError(message)
        return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def download_pdf(self, url: str, pdf_cache_path: str) -> None:
        """
        Download PDF from the given URL.

        :param url: URL of the PDF to download
        :param pdf_cache_path: Path to store the downloaded PDF
        """
        response = requests.get(url)
        response.raise_for_status()
        with open(pdf_cache_path, 'wb') as f:
            f.write(response.content)
        self.logger.debug(f"Downloaded PDF from {url} to {pdf_cache_path}")

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
