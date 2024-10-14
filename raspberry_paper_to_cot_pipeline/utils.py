import logging
import requests
import pymupdf4llm
import re
import os
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from lwe.core.config import Config
from lwe import ApiBackend


class Utils:
    def __init__(self, pdf_cache_path: str, lwe_default_preset: str, logger=None):
        self.pdf_cache_path = pdf_cache_path
        self.lwe_default_preset = lwe_default_preset
        self.logger = logger if logger else self.setup_logging("Utils", False)
        self.lwe_backend = self.setup_lwe()

    @staticmethod
    def setup_logging(logger_name: str, debug: bool) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(logger_name)

    def setup_lwe(self) -> ApiBackend:
        """Set up LWE configuration and API backend."""
        config = Config()
        config.load_from_file()
        config.set("debug.log.enabled", True)
        config.set("model.default_preset", self.lwe_default_preset)
        lwe_backend = ApiBackend(config)
        lwe_backend.set_return_only(True)
        return lwe_backend

    def run_lwe_template(self, template: str, template_vars: dict, overrides: dict = None) -> str:
        """
        Run the LWE template with the given variables.

        :param lwe_backend: LWE API backend
        :param template: Template name
        :param template_vars: Template variables
        :return: Response on success
        """
        overrides = overrides or {}
        success, response, user_message = self.lwe_backend.run_template(template, template_vars, overrides)
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
    def download_pdf(self, url: str) -> str:
        """
        Download PDF from the given URL.

        :param url: URL of the PDF to download
        :return: Path to the downloaded PDF file
        """
        response = requests.get(url)
        response.raise_for_status()
        pdf_path = self.make_pdf_cache_path_from_paper_url(url)
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        self.logger.debug(f"Downloaded PDF from {url} to {pdf_path}")
        return str(pdf_path)

    def get_pdf_text(self, url: str) -> str:
        """
        Get the text content of a PDF file.

        :param url: URL of the PDF
        :return: Extracted text from the PDF
        """
        pdf_path = self.make_pdf_cache_path_from_paper_url(url)
        if not pdf_path.exists():
            pdf_path = self.download_pdf(url)
        return self.extract_text(pdf_path)

    def extract_paper_id(self, url: str) -> str:
        """
        Extract the paper ID from the full URL.

        :param url: Full URL of the paper
        :return: Extracted paper ID
        """
        return os.path.basename(urlparse(url).path)

    def make_pdf_cache_path_from_paper_url(self, url: str) -> str:
        """
        Make a cache patch from the paper URL.

        :param url: Full URL of the paper
        :return: Full path to the PDF in the cache
        """
        return Path(self.pdf_cache_path) / self.make_pdf_name_from_paper_url(url)

    def make_pdf_name_from_paper_url(self, url: str) -> str:
        """
        Make a PDF name from the paper URL.

        :param url: Full URL of the paper
        :return: Name of the PDF file
        """
        return f"{self.extract_paper_id(url)}.pdf"

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
