#!/usr/bin/env python3
"""
This script cleans paper URLs in the SQLite database by checking their accessibility
and updating or deleting entries accordingly.
"""

import argparse
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
        "--limit",
        type=int,
        help="Optional. Limit the number of papers to clean. Default: no limit",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperCleaner:
    """
    A class to handle cleaning of paper URLs in the SQLite database.
    """

    def __init__(self, database: Optional[str], limit: Optional[int], debug: bool):
        """
        Initialize the PaperCleaner.

        :param database: Path to the SQLite database
        :param limit: Limit the number of papers to process (optional)
        :param debug: Enable debug logging
        """
        self.database = database or constants.DEFAULT_DB_NAME
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
        :raises requests.RequestException: If the URL is not accessible
        """
        response = requests.head(url, allow_redirects=True, timeout=15)
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
        except requests.RequestException:
            self.logger.warning(f"URL not accessible after retries: {url}")
            return False

    def process_paper(self, paper_id: int, paper_url: str) -> None:
        """
        Process a single paper by checking its URL accessibility and updating the database.

        :param paper_id: The ID of the paper to process
        :param paper_url: The URL of the paper to check
        """
        self.logger.info(f"Processing paper ID {paper_id} with URL: {paper_url}")
        try:
            if self.is_url_accessible(paper_url):
                self.utils.update_paper_status(paper_id, constants.STATUS_VERIFIED)
                self.logger.info(
                    f"Paper ID {paper_id} ({paper_url}) is accessible. Status updated to 'verified'."
                )
            else:
                self.utils.update_paper_status(paper_id, constants.STATUS_MISSING)
                self.logger.warning(
                    f"Paper ID {paper_id} ({paper_url}) is inaccessible. Marked as missing in the database."
                )
        except Exception as e:
            self.logger.error(f"Error processing paper {paper_id} ({paper_url}): {e}")

    def run(self) -> None:
        """Run the paper cleaning process."""
        self.logger.info(
            f"Starting paper cleaning process. Database: {self.database}, Limit: {self.limit}"
        )
        try:
            papers = self.utils.fetch_papers_by_processing_status(
                status=constants.STATUS_READY_TO_CLEAN, limit=self.limit
            )
            processed_count = 0
            for paper in papers:
                self.process_paper(paper["id"], paper["paper_url"])
                processed_count += 1
                if processed_count % 1000 == 0:
                    self.logger.info(f"Processed {processed_count} papers so far.")
            self.logger.info(
                f"Paper cleaning process completed. Total papers processed: {processed_count}"
            )
        except Exception as e:
            self.logger.error(
                f"An error occurred during the paper cleaning process: {e}"
            )
            sys.exit(1)


def main():
    """Main function to run the script."""
    args = parse_arguments()
    cleaner = PaperCleaner(database=args.database, limit=args.limit, debug=args.debug)
    cleaner.run()


if __name__ == "__main__":
    main()
