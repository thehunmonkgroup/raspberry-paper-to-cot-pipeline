#!/usr/bin/env python3
"""
This script cleans paper URLs in the SQLite database by checking their accessibility
and updating or deleting entries accordingly.
"""

import argparse
import sqlite3
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


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
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
    A class to handle cleaning of paper URLs in the SQLite database.

    This class verifies the accessibility of paper URLs stored in the database
    and updates their status accordingly. Papers with accessible URLs are marked
    as 'verified', while those with inaccessible URLs are marked as 'missing'.
    It supports batch processing with optional limits and can skip the verification
    process if needed.

    The class uses retry mechanisms for URL checking and maintains proper database
    connections using context managers.
    """

    def __init__(
        self,
        database: str = constants.DEFAULT_DB_NAME,
        skip_cleaning: bool = False,
        limit: int = None,
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
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def check_url_accessibility(self, url: str) -> bool:
        """
        Check if the given URL is accessible.

        :param url: The URL to check
        :return: True if accessible, False otherwise
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
        :return: True if accessible, False otherwise
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
        :param paper_url: The URL of the paper to check
        :raises sqlite3.Error: If there's an issue with database operations
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

    def run(self) -> None:
        """
        Run the paper cleaning process.

        This method orchestrates the entire cleaning process, either marking all papers
        as verified if skip_cleaning is True, or checking each paper's URL accessibility
        and updating their status accordingly.

        :raises SystemExit: If an unrecoverable error occurs during processing
        """
        self.logger.info(
            f"Starting paper cleaning process. Database: {self.database}, "
            f"Limit: {self.limit}, Skip cleaning: {self.skip_cleaning}"
        )
        try:
            if self.skip_cleaning:
                self.logger.debug(
                    "Skip cleaning flag is set, marking all papers as verified"
                )
                self.mark_all_papers_as_verified()
            else:
                self.logger.debug(
                    f"Fetching papers with '{constants.STATUS_PAPER_LINK_DOWNLOADED}' status using {self.selection_strategy} strategy (limit: {self.limit})"
                )
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
        """
        if processed_count % constants.PAPER_URL_PROGRESS_LOG_BATCH_SIZE == 0:
            self.logger.info(f"Processed {processed_count} papers so far.")

    def mark_all_papers_as_verified(self) -> None:
        """
        Mark all papers with STATUS_PAPER_LINK_DOWNLOADED as STATUS_PAPER_LINK_VERIFIED.

        :raises sqlite3.Error: If there's an issue with database operations
        """
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
    """Main function to run the script."""
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
