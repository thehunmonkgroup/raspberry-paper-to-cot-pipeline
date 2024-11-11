#!/usr/bin/env python3

"""
This script fetches arXiv papers based on specified categories and date range.
It uses the arXiv API to retrieve paper information, stores the results in a SQLite database,
and handles pagination and error recovery.
"""

import argparse
import time
import logging
import sqlite3
import requests
import sys
import signal
from requests.exceptions import RequestException
from dateutil.parser import parse as parse_date
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from urllib.parse import urlparse
import os.path
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from typing import List, Tuple, Dict, Optional, Any, Union, Literal
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


class ArxivPaperUrlFetcher:
    """
    A class to fetch and process arXiv paper URLs.

    This class handles the retrieval of paper URLs from arXiv's API, processes them,
    and stores them in a SQLite database. It supports pagination, error recovery,
    and graceful interruption.

    Attributes:
        database (str): Path to the SQLite database file
        debug (bool): Enable debug logging if True
        logger (logging.Logger): Logger instance for this class
        utils (Utils): Utility class instance for database operations
        interrupt_received (bool): Flag to track interrupt signals
    """

    def __init__(
        self, database: str = constants.DEFAULT_DB_NAME, debug: bool = False
    ) -> None:
        self.interrupt_received = False
        self.database = database
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database, logger=self.logger)
        self.utils.create_database()

    def fetch_arxiv_papers(
        self,
        categories: List[str],
        date_filter_begin: str,
        date_filter_end: str,
        start_index: int,
    ) -> List[Tuple[str, str]]:
        """
        Fetch papers from arXiv within the specified date range and categories.

        Args:
            categories (List[str]): List of arXiv categories to search.
            date_filter_begin (str): Start date for paper filter (YYYY-MM-DD).
            date_filter_end (str): End date for paper filter (YYYY-MM-DD).
            start_index (int): Starting index for the search.

        Returns:
            List[Tuple[str, str]]: List of tuples containing arXiv paper IDs and PDF URLs for papers within the specified date range and categories.

        Raises:
            RequestException: If there's an error fetching data from the arXiv API.
        """
        self.logger.info(
            "Searching for papers from %s to %s in categories: %s, starting from index %d",
            date_filter_begin,
            date_filter_end,
            ", ".join(categories),
            start_index,
        )

        params = self._construct_query_params(categories, start_index)
        results = []
        fetched = start_index
        attempts = 0

        try:
            while True:
                if self.interrupt_received:
                    self.logger.info("Interrupt received. Stopping paper fetch.")
                    break
                root = self._fetch_arxiv_data(params)
                if root is None:
                    return []
                entries = []
                if root is False:
                    if params["max_results"] == constants.FETCH_MAX_RESULTS_DEFAULT:
                        params["max_results"] = constants.FETCH_MAX_RESULTS_FALLBACK
                        self.logger.warning(
                            f"Reducing max_results to {constants.FETCH_MAX_RESULTS_FALLBACK} due to XML parsing error."
                        )
                    attempts += 1
                else:
                    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                    if entries:
                        attempts = 0
                        for entry in entries:
                            fetched += 1
                            result = self._process_entry(
                                entry, date_filter_begin, date_filter_end
                            )
                            if result is None:
                                continue
                            if result == "BREAK":
                                break
                            results.append(result)

                        params["start"] += len(entries)
                    else:
                        attempts += 1

                if self._should_stop_fetching(
                    root, fetched, entries, results, date_filter_end, attempts
                ):
                    break
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received. Stopping paper fetch.")
            self.interrupt_received = True

        self.logger.info("Total papers fetched: %d, stored: %d", fetched, len(results))
        return results

    def _construct_query_params(
        self, categories: List[str], start_index: int
    ) -> Dict[str, Union[str, int]]:
        """
        Construct the query parameters for the arXiv API.

        Args:
            categories: List of arXiv categories to search
            start_index: Starting index for the search

        Returns:
            Dictionary containing the query parameters for the arXiv API
        """
        category_query = " OR ".join([f"cat:{cat}" for cat in categories])
        return {
            "search_query": f"({category_query})",
            "start": start_index,
            "max_results": constants.FETCH_MAX_RESULTS_DEFAULT,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "ascending",
        }

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=(retry_if_exception_type(RequestException)),
        reraise=True,
    )
    def _fetch_arxiv_data(self, params: Dict[str, Any]) -> Optional[ET.Element]:
        """
        Fetch data from arXiv API and return the XML root.

        Args:
            params: Query parameters for the API request

        Returns:
            Parsed XML Element if successful, None if parsing fails

        Raises:
            RequestException: If the HTTP request fails or returns non-200 status
            ParseError: If the XML response cannot be parsed
        """
        base_url = "https://export.arxiv.org/api/query"
        self.logger.debug("Fetching papers from arXiv: %s: %s", base_url, params)
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            self.logger.error("Error fetching papers from arXiv: %s", response.text)
            raise RequestException(f"HTTP status code: {response.status_code}")
        try:
            return ET.fromstring(response.content)
        except ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            self.logger.debug(
                f"Response content: {response.content[:1000]}..."
            )  # Log first 1000 characters
            return False

    def _process_entry(
        self, entry: ET.Element, date_filter_begin: str, date_filter_end: str
    ) -> Optional[Union[Tuple[str, str], Literal["BREAK"]]]:
        """
        Process a single entry from the arXiv API response.

        Args:
            entry: XML element containing the paper entry
            date_filter_begin: Start date for filtering papers (YYYY-MM-DD)
            date_filter_end: End date for filtering papers (YYYY-MM-DD)

        Returns:
            Tuple of (paper_id, pdf_url) if valid,
            "BREAK" if we should stop processing,
            None if entry should be skipped

        Raises:
            ValueError: If date parsing fails
        """
        updated_date = parse_date(
            entry.find("{http://www.w3.org/2005/Atom}updated").text
        ).date()
        if updated_date < parse_date(date_filter_begin).date():
            self.logger.debug(
                "Skipping paper updated before start date: %s", updated_date
            )
            return None
        if updated_date > parse_date(date_filter_end).date():
            self.logger.debug("Reached papers after end date. Stopping search.")
            return "BREAK"
        id_url = entry.find("{http://www.w3.org/2005/Atom}id").text
        paper_id = os.path.basename(urlparse(id_url).path)
        pdf_link = entry.find(
            "{http://www.w3.org/2005/Atom}link[@title='pdf'][@type='application/pdf']"
        )
        if pdf_link is not None:
            return paper_id, pdf_link.get("href")
        else:
            self.logger.warning(f"PDF link not found for entry: {paper_id}")
            return None

    def _should_stop_fetching(
        self,
        root: Optional[ET.Element],
        fetched: int,
        entries: List[ET.Element],
        results: List[Tuple[str, str]],
        date_filter_end: str,
        attempts: int,
    ) -> bool:
        """
        Determine if we should stop fetching more results.

        Args:
            root: Parsed XML root element
            fetched: Number of papers fetched so far
            entries: List of paper entries from current response
            results: List of processed results
            date_filter_end: End date for paper filtering
            attempts: Number of consecutive empty result attempts

        Returns:
            True if we should stop fetching, False otherwise
        """
        if attempts >= constants.FETCH_MAX_EMPTY_RESULTS_ATTEMPTS:
            self.logger.warning(
                f"Reached maximum number of attempts ({constants.FETCH_MAX_EMPTY_RESULTS_ATTEMPTS}) without fetching any results. Stopping search."
            )
            return True
        if root is False:
            return False
        total_results = int(
            root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults").text
        )
        if fetched >= total_results:
            return True
        self.logger.info(
            "Fetched %d papers, stored %d papers, total results: %d",
            fetched,
            len(results),
            total_results,
        )
        if entries:
            last_updated_date = parse_date(
                root.findall("{http://www.w3.org/2005/Atom}entry")[-1]
                .find("{http://www.w3.org/2005/Atom}updated")
                .text
            ).date()
            return last_updated_date > parse_date(date_filter_end).date()
        else:
            time.sleep(1)
            self.logger.debug(
                f"No entries returned for current batch. Sleeping for 1 second before retry (attempt {attempts}/{constants.FETCH_MAX_EMPTY_RESULTS_ATTEMPTS})"
            )
            return False

    def generate_pdf_data(
        self, arxiv_paper_data: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """
        Process the retrieved paper data.

        Args:
            arxiv_paper_data (list): List of tuples containing arXiv paper IDs and PDF URLs.

        Returns:
            list: List of tuples containing paper IDs and processed PDF download URLs.
        """
        processed_data = []
        for paper_id, url in arxiv_paper_data:
            path = urlparse(url).path
            processed_url = f"{constants.ARXIV_EXPORT_BASE}{path}"
            if not processed_url.endswith(".pdf"):
                processed_url += ".pdf"
            processed_data.append((paper_id, processed_url))
        return processed_data

    def write_pdf_data_to_database(self, paper_data, category):
        """
        Write paper data and category to the SQLite database.

        Args:
            paper_data (list): List of tuples containing paper IDs and URLs to write.
            category (str): arXiv category of the papers.
        """
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()

                # Use a transaction for efficiency and atomicity
                conn.execute("BEGIN TRANSACTION")

                # Insert papers
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO papers (paper_id, paper_url, processing_status)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (paper_id, url, constants.STATUS_PAPER_LINK_DOWNLOADED)
                        for paper_id, url in paper_data
                    ],
                )

                # Get the paper_ids for the inserted/existing papers
                paper_ids = [paper_id for paper_id, _ in paper_data]
                cursor.execute(
                    """
                    SELECT id, paper_id FROM papers
                    WHERE paper_id IN ({})
                    """.format(
                        ",".join(["?"] * len(paper_ids))
                    ),
                    paper_ids,
                )
                ids_map = {row[1]: row[0] for row in cursor.fetchall()}

                # Insert categories
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO paper_categories (paper_id, category)
                    VALUES (?, ?)
                    """,
                    [
                        (ids_map[paper_id], category)
                        for paper_id in paper_ids
                        if paper_id in ids_map
                    ],
                )
                self.logger.info(f"Inserted {cursor.rowcount} new category entries")

                conn.commit()

            self.logger.info(
                f"Successfully processed {len(paper_data)} papers with category {category}"
            )
        except sqlite3.Error as e:
            self.logger.error("Error writing to database: %s", str(e))
            sys.exit(1)

    def category_exists_in_database(self, category):
        """
        Check if the given category already exists in the database.

        Args:
            category (str): arXiv category to check.

        Returns:
            bool: True if the category exists, False otherwise.
        """
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM paper_categories WHERE category = ?", (category,)
            )
            count = cursor.fetchone()[0]
            return count > 0

    def run(
        self,
        category: str,
        date_filter_begin: str,
        date_filter_end: str,
        start_index: int = 0,
    ) -> None:
        """
        Run the arXiv paper search and URL generation process.

        Args:
            category: arXiv category to search
            date_filter_begin: Start date for the search in YYYY-MM-DD format
            date_filter_end: End date for the search in YYYY-MM-DD format
            start_index: Starting index for the search

        Raises:
            RequestException: If network errors occur during paper fetching
            sqlite3.Error: If database operations fail
            ValueError: If date parsing fails
        """
        # Register this instance for interrupt handling
        signal_handler.active_fetcher = self
        self.logger.debug(
            "Starting arXiv paper search with category=%s, date_filter_begin=%s, date_filter_end=%s, start_index=%d",
            category,
            date_filter_begin,
            date_filter_end,
            start_index,
        )

        try:
            # Check if the category already exists in the database
            if self.category_exists_in_database(category):
                self.logger.info(
                    f"Category {category} already exists in the database. Skipping."
                )
                return

            arxiv_paper_data = self.fetch_arxiv_papers(
                [category], date_filter_begin, date_filter_end, start_index
            )
            if self.interrupt_received:
                self.logger.info("Interrupt received. Exiting.")
                return

            if not arxiv_paper_data:
                self.logger.warning("No papers found for the given criteria.")
                return

            processed_paper_data = self.generate_pdf_data(arxiv_paper_data)
            self.write_pdf_data_to_database(processed_paper_data, category)

            self.logger.info("Process completed successfully.")
        except RequestException as e:
            self.logger.error(f"Network error occurred: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self.logger.debug("", exc_info=True)  # Log full traceback at debug level


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Search arXiv for recent papers and generate PDF download links."
    )
    parser.add_argument(
        "--category", type=str, required=True, help="arXiv category to search."
    )
    parser.add_argument(
        "--date-filter-begin",
        type=str,
        required=True,
        help="Start date for paper filter (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--date-filter-end",
        type=str,
        required=True,
        help="End date for paper filter (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Starting index for the search. Default: 0",
    )
    parser.add_argument(
        "--database",
        type=str,
        default=constants.DEFAULT_DB_NAME,
        help="Name of the SQLite database file (default: %(default)s)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def signal_handler(signum: int, frame: Any) -> None:
    """
    Handle interrupt signal (Ctrl+C).

    Args:
        signum: Signal number
        frame: Current stack frame (not used)

    Note:
        This handler sets the interrupt flag on the active fetcher instance
        to allow for graceful shutdown.
    """
    print("\nInterrupt received. Exiting gracefully...")
    if hasattr(signal_handler, "active_fetcher"):
        signal_handler.active_fetcher.interrupt_received = True


def main():
    """
    Main function to handle command-line execution.
    """
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    args = parse_arguments()
    fetcher = ArxivPaperUrlFetcher(args.database, debug=args.debug)
    try:
        fetcher.run(
            args.category,
            args.date_filter_begin,
            args.date_filter_end,
            args.start_index,
        )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
