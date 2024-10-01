#!/usr/bin/env python3

import argparse
import time
import logging
import sqlite3
import requests
import sys
import signal
from pathlib import Path
from requests.exceptions import RequestException
from dateutil.parser import parse as parse_date
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEFAULT_DB_NAME = 'papers.db'
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_url TEXT,
    paper_category TEXT,
    processing_status TEXT,
    criteria_clear_question INT,
    criteria_definitive_answer INT,
    criteria_complex_reasoning INT,
    criteria_coherent_structure INT,
    criteria_layperson_comprehensible INT,
    criteria_minimal_jargon INT,
    criteria_illustrative_examples INT,
    criteria_significant_insights INT,
    criteria_verifiable_steps INT,
    criteria_overall_suitability INT,
    UNIQUE(paper_url, paper_category)
);
"""
MAX_EMPTY_RESULTS_ATTEMPTS = 25

class ArxivPaperFetcher:
    def __init__(self, database=None, debug_mode=False):
        self.setup_logging(debug_mode)
        self.logger = logging.getLogger(__name__)
        self.database = database or DEFAULT_DB_NAME
        self.create_database()

    def setup_logging(self, debug_mode):
        """
        Set up logging configuration.

        Args:
            debug_mode (bool): If True, set logging level to DEBUG, otherwise INFO.
        """
        log_level = logging.DEBUG if debug_mode else logging.INFO
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    def create_database(self) -> None:
        """
        Conditionally creates an SQLite database with the required table and columns.

        This method connects to the SQLite database specified by self.database,
        creates the necessary table if it doesn't exist, and handles any errors
        that may occur during the process.

        Raises:
            sqlite3.Error: If there's an issue with the SQLite operations.
        """
        db_path = Path(self.database)
        self.logger.info(f"Creating/connecting to database: {db_path}")

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(CREATE_TABLE_QUERY)
                conn.commit()
            self.logger.info(f"Database '{db_path}' is ready.")
        except sqlite3.Error as e:
            self.logger.error(f"An error occurred while creating database {db_path}: {e}")
            raise

    def fetch_arxiv_papers(self, categories, date_filter_begin, date_filter_end, start_index):
        """
        Fetch papers from arXiv within the specified date range and categories.

        Args:
            categories (list): List of arXiv categories to search.
            date_filter_begin (str): Start date for paper filter (YYYY-MM-DD).
            date_filter_end (str): End date for paper filter (YYYY-MM-DD).
            start_index (int): Starting index for the search.

        Returns:
            list: List of arXiv IDs for papers within the specified date range and categories.
        """
        self.logger.info('Searching for papers from %s to %s in categories: %s, starting from index %d',
                         date_filter_begin, date_filter_end, ', '.join(categories), start_index)

        params = self._construct_query_params(categories, start_index)
        results = []
        fetched = start_index
        attempts = 0

        while True:
            root = self._fetch_arxiv_data(params)
            if root is None:
                return []

            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if entries:
                attempts = 0
                for entry in entries:
                    fetched += 1
                    arxiv_id = self._process_entry(entry, date_filter_begin, date_filter_end)
                    if arxiv_id is None:
                        continue
                    if arxiv_id == 'BREAK':
                        break
                    results.append(arxiv_id)

                params['start'] += len(entries)
            else:
                attempts += 1

            if self._should_stop_fetching(root, fetched, entries, results, date_filter_end, attempts):
                break

        self.logger.info('Total papers fetched: %d, stored: %d', fetched, len(results))
        return results

    def _construct_query_params(self, categories, start_index):
        """Construct the query parameters for the arXiv API."""
        category_query = ' OR '.join([f'cat:{cat}' for cat in categories])
        return {
            'search_query': f'({category_query})',
            'start': start_index,
            'max_results': 1000,
            'sortBy': 'lastUpdatedDate',
            'sortOrder': 'ascending'
        }

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=(retry_if_exception_type(RequestException) | retry_if_exception_type(ParseError)),
        reraise=True
    )
    def _fetch_arxiv_data(self, params):
        """Fetch data from arXiv API and return the XML root."""
        base_url = 'https://export.arxiv.org/api/query'
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            self.logger.error('Error fetching papers from arXiv: %s', response.text)
            raise RequestException(f"HTTP status code: {response.status_code}")
        try:
            return ET.fromstring(response.content)
        except ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            self.logger.debug(f"Response content: {response.content[:1000]}...")  # Log first 1000 characters
            raise

    def _process_entry(self, entry, date_filter_begin, date_filter_end):
        """Process a single entry from the arXiv API response."""
        updated_date = parse_date(entry.find('{http://www.w3.org/2005/Atom}updated').text).date()
        if updated_date < parse_date(date_filter_begin).date():
            self.logger.debug('Skipping paper updated before start date: %s', updated_date)
            return None
        if updated_date > parse_date(date_filter_end).date():
            self.logger.debug('Reached papers after end date. Stopping search.')
            return 'BREAK'
        return entry.find('{http://www.w3.org/2005/Atom}id').text.split('/')[-1]

    def _should_stop_fetching(self, root, fetched, entries, results, date_filter_end, attempts):
        """Determine if we should stop fetching more results."""
        if attempts >= MAX_EMPTY_RESULTS_ATTEMPTS:
            self.logger.warning(f'Reached maximum number of attempts ({MAX_EMPTY_RESULTS_ATTEMPTS}) without fetching any results. Stopping search.')
            return True
        total_results = int(root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults').text)
        if fetched >= total_results:
            return True
        self.logger.info('Fetched %d papers, stored %d papers, total results: %d', fetched, len(results), total_results)
        if entries:
            last_updated_date = parse_date(root.findall('{http://www.w3.org/2005/Atom}entry')[-1].find('{http://www.w3.org/2005/Atom}updated').text).date()
            return last_updated_date > parse_date(date_filter_end).date()
        else:
            time.sleep(1)
            self.logger.debug('No entries returned. Sleeping for 1 second...')
            return False

    def generate_pdf_urls(self, arxiv_ids):
        """
        Generate PDF download URLs for given arXiv IDs.

        Args:
            arxiv_ids (list): List of arXiv IDs.

        Returns:
            list: List of PDF download URLs.
        """
        return [f'https://export.arxiv.org/pdf/{arxiv_id}.pdf' for arxiv_id in arxiv_ids]

    def write_urls_to_database(self, urls, category):
        """
        Write URLs and category to the SQLite database.

        Args:
            urls (list): List of URLs to write.
            category (str): arXiv category of the papers.
        """
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO papers (paper_url, paper_category)
                    VALUES (?, ?)
                    """,
                    [(url, category) for url in urls]
                )
                conn.commit()
            self.logger.info('Successfully wrote %d new entries with category %s to the database', cursor.rowcount, category)
        except sqlite3.Error as e:
            self.logger.error('Error writing to database: %s', str(e))
            sys.exit(1)

    def run(self, category, date_filter_begin, date_filter_end, start_index=0):
        """
        Run the arXiv paper search and URL generation process.

        Args:
            category (str): arXiv category to search.
            date_filter_begin (str): Start date for the search in YYYY-MM-DD format.
            date_filter_end (str): End date for the search in YYYY-MM-DD format.
            start_index (int): Starting index for the search.
        """
        self.logger.debug('Starting arXiv paper search with category=%s, date_filter_begin=%s, date_filter_end=%s, start_index=%d',
                          category, date_filter_begin, date_filter_end, start_index)

        try:
            arxiv_ids = self.fetch_arxiv_papers([category], date_filter_begin, date_filter_end, start_index)
            if not arxiv_ids:
                self.logger.warning('No papers found for the given criteria.')
                return

            pdf_urls = self.generate_pdf_urls(arxiv_ids)
            self.write_urls_to_database(pdf_urls, category)

            self.logger.info('Process completed successfully.')
        except RequestException as e:
            self.logger.error(f"Network error occurred: {e}")
        except ParseError as e:
            self.logger.error(f"XML parsing error occurred: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self.logger.debug("", exc_info=True)  # Log full traceback at debug level

def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Search arXiv for recent papers and generate PDF download links.')
    parser.add_argument('--category', type=str, required=True,
                        help='arXiv category to search.')
    parser.add_argument('--date-filter-begin', type=str, required=True,
                        help='Start date for paper filter (YYYY-MM-DD).')
    parser.add_argument('--date-filter-end', type=str, required=True,
                        help='End date for paper filter (YYYY-MM-DD).')
    parser.add_argument('--start-index', type=int, default=0,
                        help='Starting index for the search. Default: 0')
    parser.add_argument('--database', type=str, default=DEFAULT_DB_NAME,
                        help='Name of the SQLite database file (default: %(default)s)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging.')
    return parser.parse_args()

def signal_handler(signum, frame):
    """
    Handle interrupt signal (Ctrl+C).
    """
    print("\nInterrupt received. Exiting gracefully...")
    sys.exit(0)

def main():
    """
    Main function to handle command-line execution.
    """
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    args = parse_arguments()
    fetcher = ArxivPaperFetcher(args.database, debug_mode=args.debug)
    try:
        fetcher.run(args.category, args.date_filter_begin, args.date_filter_end, args.start_index)
    except KeyboardInterrupt:
        print("\nInterrupt received. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
