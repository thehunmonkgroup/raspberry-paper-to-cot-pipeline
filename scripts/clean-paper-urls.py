#!/usr/bin/env python3
"""
This script cleans paper URLs in the SQLite database by checking their accessibility
and updating or deleting entries accordingly.
"""

import argparse
import logging
import sqlite3
from typing import Optional
from contextlib import contextmanager
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import requests

READY_TO_CLEAN_STATUS = 'ready_to_clean'

@contextmanager
def get_db_connection(database_path):
    conn = sqlite3.connect(database_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.isolation_level = "IMMEDIATE"
    try:
        yield conn
    finally:
        conn.close()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Clean paper URLs in the SQLite database.")
    parser.add_argument("--database", type=str, default="papers.db", help="Path to the SQLite database")
    parser.add_argument("--limit", type=int, help="Optional. Limit the number of papers to clean")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperCleaner:
    """
    A class to handle cleaning of paper URLs in the SQLite database.
    """

    def __init__(self, database: str, limit: Optional[int], debug: bool):
        """
        Initialize the PaperCleaner.

        :param database: Path to the SQLite database
        :param limit: Limit the number of papers to process (optional)
        :param debug: Enable debug logging
        """
        self.database = database
        self.limit = limit
        self.debug = debug
        self.logger = logging.getLogger(__name__)

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    def fetch_papers(self):
        """Fetch papers from the SQLite database."""
        query = """
        SELECT id, paper_url FROM papers
        WHERE processing_status = ?
        ORDER BY RANDOM()
        """
        params = [READY_TO_CLEAN_STATUS]
        if self.limit is not None:
            query += " LIMIT ?"
            params.append(self.limit)

        self.logger.debug("Fetching papers from database")
        with get_db_connection(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor:
                yield row['id'], row['paper_url']
        self.logger.debug("Finished fetching papers from database")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True
    )
    def check_url_accessibility(self, url: str) -> bool:
        """
        Check if the given URL is accessible.

        :param url: The URL to check
        :return: True if accessible, False otherwise
        """
        response = requests.head(url, allow_redirects=True, timeout=10)
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

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=1, max=2),
        retry=retry_if_exception_type(sqlite3.OperationalError),
        reraise=True
    )
    def update_paper_status(self, paper_id: int, status: str) -> None:
        """
        Update the processing status of a paper in the database.

        :param paper_id: The ID of the paper to update
        :param status: The new status to set
        """
        query = "UPDATE papers SET processing_status = ? WHERE id = ?"
        self.logger.debug(f"Attempting to update paper status: ID={paper_id}, status={status}")
        with get_db_connection(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (status, paper_id))
            conn.commit()
        self.logger.debug(f"Successfully updated paper status: ID={paper_id}, status={status}")

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=1, max=2),
        retry=retry_if_exception_type(sqlite3.OperationalError),
        reraise=True
    )
    def delete_paper(self, paper_id: int) -> None:
        """
        Delete a paper and its categories from the database.

        :param paper_id: The ID of the paper to delete
        """
        queries = [
            "DELETE FROM paper_categories WHERE paper_id = ?",
            "DELETE FROM papers WHERE id = ?"
        ]
        self.logger.debug(f"Attempting to delete paper: ID={paper_id}")
        with get_db_connection(self.database) as conn:
            try:
                cursor = conn.cursor()
                for query in queries:
                    cursor.execute(query, (paper_id,))
                conn.commit()
                self.logger.debug(f"Successfully deleted paper: ID={paper_id}")
            except sqlite3.Error as e:
                conn.rollback()
                self.logger.error(f"Error deleting paper: ID={paper_id}, error={str(e)}")
                raise

    def process_paper(self, paper_id: int, paper_url: str) -> None:
        """
        Process a single paper by checking its URL accessibility and updating the database.

        :param paper_id: The ID of the paper to process
        :param paper_url: The URL of the paper to check
        """
        self.logger.info(f"Processing paper ID {paper_id} with URL: {paper_url}")
        if self.is_url_accessible(paper_url):
            try:
                self.update_paper_status(paper_id, "cleaned")
                self.logger.info(f"Paper ID {paper_id} ({paper_url}) is accessible. Status updated to 'cleaned'.")
            except Exception as e:
                self.logger.error(f"Failed to update status of paper {paper_id} ({paper_url}): {e}")
        else:
            try:
                self.delete_paper(paper_id)
                self.logger.warning(f"Paper ID {paper_id} ({paper_url}) is inaccessible. Deleted from the database.")
            except Exception as e:
                self.logger.error(f"Failed to delete missing paper {paper_id} ({paper_url}): {e}")

    def run(self) -> None:
        """Run the paper cleaning process."""
        self.setup_logging()
        self.logger.info(f"Starting paper cleaning process. Database: {self.database}, Limit: {self.limit}")

        papers_generator = self.fetch_papers()
        processed_count = 0

        for paper_id, paper_url in papers_generator:
            self.process_paper(paper_id, paper_url)
            processed_count += 1

            if processed_count % 1000 == 0:
                self.logger.info(f"Processed {processed_count} papers so far.")

        self.logger.info(f"Paper cleaning process completed. Total papers processed: {processed_count}")


def main():
    """Main function to run the script."""
    args = parse_arguments()
    cleaner = PaperCleaner(database=args.database, limit=args.limit, debug=args.debug)
    cleaner.run()


if __name__ == "__main__":
    main()
