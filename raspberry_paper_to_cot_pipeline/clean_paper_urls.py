#!/usr/bin/env python3
"""
Clean paper URLs in the SQLite database.

This module provides functionality to verify and clean paper URLs stored in the database.
It checks URL accessibility and updates paper status accordingly. Papers with accessible
URLs are marked as 'verified', while those with inaccessible URLs are marked as 'missing'.

The module supports batch processing, retry mechanisms, and configurable logging.
"""

import argparse
import sqlite3
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import requests
import sys

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils

# Retry configuration constants
RETRY_ATTEMPTS = 2
RETRY_MULTIPLIER = 1
RETRY_MIN = 1
RETRY_MAX = 5


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Clean paper URLs in the SQLite database."
    )
    parser.add_argument(
        "--database",
        type=str,
        default=constants.DEFAULT_DB_NAME,
        help="Path to the SQLite database. Default: %(default)s",
    )
    parser.add_argument(
        "--skip-cleaning",
        action="store_true",
        help="Skip cleaning and mark all papers as verified",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional. Limit the number of papers to clean. Default: no limit",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperCleaner:
    """
    Handle cleaning of paper URLs in the SQLite database.

    This class verifies the accessibility of paper URLs stored in the database
    and updates their status accordingly. Papers with accessible URLs are marked
    as 'verified', while those with inaccessible URLs are marked as 'missing'.

    The class implements retry mechanisms for URL checking and maintains proper
    database connections using context managers.

    :ivar database: Path to the SQLite database
    :type database: str
    :ivar skip_cleaning: Flag to skip cleaning and mark all as verified
    :type skip_cleaning: bool
    :ivar limit: Maximum number of papers to process
    :type limit: Optional[int]
    :ivar debug: Enable debug logging if True
    :type debug: bool
    :ivar logger: Configured logging instance
    :type logger: logging.Logger
    :ivar utils: Utility class instance
    :type utils: Utils
    """

    def __init__(
        self,
        database: str = constants.DEFAULT_DB_NAME,
        skip_cleaning: bool = False,
        limit: Optional[int] = None,
        debug: bool = False,
    ):
        """
        Initialize the PaperCleaner.

        :param database: Path to the SQLite database
        :param skip_cleaning: Skip cleaning and mark all papers as verified
        :param limit: Limit the number of papers to process (optional)
        :param debug: Enable debug logging
        """
        self.database = database
        self.skip_cleaning = skip_cleaning
        self.limit = limit
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database, logger=self.logger)

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER, min=RETRY_MIN, max=RETRY_MAX
        ),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def check_url_accessibility(self, url: str) -> bool:
        """
        Check if the given URL is accessible.

        :param url: The URL to check
        :type url: str
        :return: True if accessible, False otherwise
        :rtype: bool
        :raises requests.RequestException: If the URL cannot be accessed due to HTTP errors,
            timeout, or other request-related issues
        """
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=constants.PAPER_URL_REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            self.logger.warning(f"URL NOT accessible: {url}")
            raise requests.RequestException(f"URL not accessible: {url}")
        self.logger.debug(f"URL accessible: {url}")
        return True

    def is_url_accessible(self, url: str) -> bool:
        """
        Wrapper method to handle retries for URL accessibility check.

        :param url: The URL to check
        :type url: str
        :return: True if accessible, False otherwise
        :rtype: bool
        """
        try:
            return self.check_url_accessibility(url)
        except requests.RequestException as e:
            self.logger.warning(
                f"URL not accessible after retries: {url}. Error: {str(e)}"
            )
            return False

    def process_paper(self, paper_id: int, paper_url: str) -> None:
        """
        Process a single paper by checking its URL accessibility and updating the database.

        :param paper_id: The ID of the paper to process
        :type paper_id: int
        :param paper_url: The URL of the paper to check
        :type paper_url: str
        :raises sqlite3.Error: If there's an issue with database operations
        :raises Exception: If an unexpected error occurs during processing
        """
        self.logger.info(f"Processing paper ID {paper_id} with URL: {paper_url}")
        try:
            if self.is_url_accessible(paper_url):
                self.utils.update_paper_status(
                    paper_id, constants.STATUS_PAPER_LINK_VERIFIED
                )
                self.logger.info(
                    f"Paper ID {paper_id} ({paper_url}) is accessible. Status updated to 'verified'."
                )
            else:
                self.utils.update_paper_status(paper_id, constants.STATUS_PAPER_MISSING)
                self.logger.warning(
                    f"Paper ID {paper_id} ({paper_url}) is inaccessible. Marked as missing in the database."
                )
        except sqlite3.Error as e:
            self.logger.error(f"Database error processing paper {paper_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing paper {paper_id}: {e}")
            raise

    def _setup_cleaning_process(self) -> None:
        """
        Log initial setup information for the cleaning process.

        Sets up logging with initial configuration details including database path,
        processing limits, and cleaning mode.
        """
        self.logger.info(
            f"Starting paper cleaning process. Database: {self.database}, "
            f"Limit: {self.limit}, Skip cleaning: {self.skip_cleaning}"
        )
        self.logger.debug(
            f"Configuration details:\n"
            f"  - Database path: {self.database}\n"
            f"  - Processing limit: {self.limit if self.limit else 'No limit'}\n"
            f"  - Skip cleaning mode: {self.skip_cleaning}\n"
            f"  - Debug mode: {self.debug}\n"
            f"  - Retry attempts: {RETRY_ATTEMPTS}\n"
            f"  - Retry wait: {RETRY_MIN}-{RETRY_MAX}s (multiplier: {RETRY_MULTIPLIER})"
        )

    def _process_papers(self) -> int:
        """
        Process all papers that need cleaning.

        Fetches papers with downloaded status and processes them in batches,
        updating their status based on URL accessibility.

        :return: Number of papers processed
        :rtype: int
        :raises sqlite3.Error: If database operations fail
        """
        papers = self.utils.fetch_papers_by_processing_status(
            status=constants.STATUS_PAPER_LINK_DOWNLOADED, limit=self.limit
        )
        processed_count = 0
        for paper in papers:
            self.logger.debug(
                f"Processing paper ID {paper['id']} with URL {paper['paper_url']} for CoT extraction"
            )
            self.process_paper(paper["id"], paper["paper_url"])
            processed_count += 1
            self._log_progress(processed_count)
        return processed_count

    def run(self) -> None:
        """
        Run the paper cleaning process.

        This method orchestrates the entire cleaning process, either marking all papers
        as verified if skip_cleaning is True, or checking each paper's URL accessibility
        and updating their status accordingly.

        :raises SystemExit: If an unrecoverable error occurs during processing
        """
        try:
            self._setup_cleaning_process()

            if self.skip_cleaning:
                self.logger.debug(
                    "Skip cleaning flag is set, marking all papers as verified"
                )
                self.mark_all_papers_as_verified()
            else:
                self.logger.debug(
                    f"Fetching papers with '{constants.STATUS_PAPER_LINK_DOWNLOADED}' status (limit: {self.limit})"
                )
                processed_count = self._process_papers()
                self.logger.info(
                    f"Paper cleaning process completed. Total papers processed: {processed_count}"
                )
        except Exception as e:
            self.logger.error(
                f"An error occurred during the paper cleaning process: {e}"
            )
            sys.exit(1)

    def _log_progress(self, processed_count: int) -> None:
        """
        Log progress of paper processing at regular intervals.

        :param processed_count: Number of papers processed so far
        :type processed_count: int
        """
        if processed_count % constants.PAPER_URL_PROGRESS_LOG_BATCH_SIZE == 0:
            self.logger.info(f"Processed {processed_count} papers so far.")

    def mark_all_papers_as_verified(self) -> None:
        """
        Mark all papers with STATUS_PAPER_LINK_DOWNLOADED as STATUS_PAPER_LINK_VERIFIED.

        Updates the processing status of all papers from downloaded to verified state,
        skipping the actual URL verification process.

        :raises sqlite3.Error: If there's an issue with database operations
        """
        self.logger.debug(
            f"Preparing to mark all papers with status '{constants.STATUS_PAPER_LINK_DOWNLOADED}' as '{constants.STATUS_PAPER_LINK_VERIFIED}'"
        )
        try:
            with self.utils.get_db_connection(self.database) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE papers
                    SET processing_status = ?
                    WHERE processing_status = ?
                    """,
                    (
                        constants.STATUS_PAPER_LINK_VERIFIED,
                        constants.STATUS_PAPER_LINK_DOWNLOADED,
                    ),
                )
                updated_count = cursor.rowcount
                conn.commit()
            self.logger.info(
                f"Marked {updated_count} papers as verified, skipping cleaning process."
            )
        except sqlite3.Error as e:
            self.logger.error(f"Database error while marking papers as verified: {e}")
            raise


def main():
    """
    Main function to run the script.

    Parses command line arguments and initializes the PaperCleaner to process URLs.
    """
    args = parse_arguments()
    cleaner = PaperCleaner(
        database=args.database,
        skip_cleaning=args.skip_cleaning,
        limit=args.limit,
        debug=args.debug,
    )
    cleaner.run()


if __name__ == "__main__":
    main()
