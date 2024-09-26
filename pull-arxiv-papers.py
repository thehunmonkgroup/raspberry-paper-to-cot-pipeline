#!/usr/bin/env python3

import argparse
import time
import logging
import requests
import sys
import signal
from dateutil.parser import parse as parse_date
import xml.etree.ElementTree as ET

class ArxivPaperFetcher:
    def __init__(self, debug_mode=False):
        self.setup_logging(debug_mode)
        self.logger = logging.getLogger(__name__)

    def setup_logging(self, debug_mode):
        """
        Set up logging configuration.

        Args:
            debug_mode (bool): If True, set logging level to DEBUG, otherwise INFO.
        """
        log_level = logging.DEBUG if debug_mode else logging.INFO
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

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

        while True:
            root = self._fetch_arxiv_data(params)
            if root is None:
                return []

            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if entries:
                for entry in entries:
                    fetched += 1
                    arxiv_id = self._process_entry(entry, date_filter_begin, date_filter_end)
                    if arxiv_id is None:
                        continue
                    if arxiv_id == 'BREAK':
                        break
                    results.append(arxiv_id)

                params['start'] += len(entries)

            if self._should_stop_fetching(root, fetched, entries, results, date_filter_end):
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

    def _fetch_arxiv_data(self, params):
        """Fetch data from arXiv API and return the XML root."""
        base_url = 'http://export.arxiv.org/api/query'
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            self.logger.error('Error fetching papers from arXiv: %s', response.text)
            return None
        return ET.fromstring(response.content)

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

    def _should_stop_fetching(self, root, fetched, entries, results, date_filter_end):
        """Determine if we should stop fetching more results."""
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
        return [f'http://export.arxiv.org/pdf/{arxiv_id}.pdf' for arxiv_id in arxiv_ids]

    def write_urls_to_file(self, urls, output_file):
        """
        Write URLs to the specified output file.

        Args:
            urls (list): List of URLs to write.
            output_file (str): Name of the output file.
        """
        try:
            with open(output_file, 'w') as f:
                for url in urls:
                    f.write(f'{url}\n')
            self.logger.info('Successfully wrote %d URLs to %s', len(urls), output_file)
        except IOError as e:
            self.logger.error('Error writing to file %s: %s', output_file, str(e))
            sys.exit(1)

    def run(self, categories, date_filter_begin, date_filter_end, start_index, output_file):
        """
        Run the arXiv paper search and URL generation process.

        Args:
            categories (list): List of arXiv categories to search.
            date_filter_begin (str): Start date for the search in YYYY-MM-DD format.
            date_filter_end (str): End date for the search in YYYY-MM-DD format.
            start_index (int): Starting index for the search.
            output_file (str): Name of the output file.
        """
        self.logger.debug('Starting arXiv paper search with categories=%s, date_filter_begin=%s, date_filter_end=%s, start_index=%d, output_file=%s',
                          categories, date_filter_begin, date_filter_end, start_index, output_file)

        arxiv_ids = self.fetch_arxiv_papers(categories, date_filter_begin, date_filter_end, start_index)
        if not arxiv_ids:
            self.logger.error('No papers found or error occurred during fetch. Exiting.')
            sys.exit(1)

        pdf_urls = self.generate_pdf_urls(arxiv_ids)
        self.write_urls_to_file(pdf_urls, output_file)

        self.logger.info('Process completed successfully.')

def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Search arXiv for recent papers and generate PDF download links.')
    parser.add_argument('--category', type=str, required=True, action='append',
                        help='arXiv category to search. Can be specified multiple times.')
    parser.add_argument('--date-filter-begin', type=str, required=True,
                        help='Start date for paper filter (YYYY-MM-DD).')
    parser.add_argument('--date-filter-end', type=str, required=True,
                        help='End date for paper filter (YYYY-MM-DD).')
    parser.add_argument('--start-index', type=int, default=0,
                        help='Starting index for the search. Default: 0')
    parser.add_argument('--output', type=str, default='papers.txt',
                        help='Output file name for the list of paper URLs. Default: papers.txt')
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
    fetcher = ArxivPaperFetcher(debug_mode=args.debug)
    try:
        fetcher.run(args.category, args.date_filter_begin, args.date_filter_end, args.start_index, args.output)
    except KeyboardInterrupt:
        print("\nInterrupt received. Exiting gracefully...")
        sys.exit(0)

if __name__ == '__main__':
    main()
