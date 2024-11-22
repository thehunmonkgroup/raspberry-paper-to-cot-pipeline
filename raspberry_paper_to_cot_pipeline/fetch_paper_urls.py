#!/usr/bin/env python3

"""Script for fetching arXiv papers based on date range and categories.

This module implements functionality to fetch and process arXiv papers for specified
categories within a given date range. It provides a command-line interface for
interacting with the arXiv API and managing paper metadata.

Key features:
    - Fetches papers using arXiv API with configurable parameters
    - Supports custom date ranges and category filtering
    - Dynamically retrieves latest arXiv category taxonomy
    - Stores paper metadata in SQLite database
    - Provides configuration display and category listing utilities
"""

import argparse
import sys
from datetime import datetime
from typing import List

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils
from raspberry_paper_to_cot_pipeline.fetch_arxiv_paper_urls_by_category import (
    ArxivPaperUrlFetcher,
)


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments for the script.

    Sets up argument parser with all required and optional arguments for
    controlling paper fetching behavior.

    :return: Namespace containing all parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Pull arXiv papers based on date range and categories."
    )
    parser.add_argument(
        "--begin",
        default=constants.FETCH_DEFAULT_BEGIN_DATE,
        help="Start date for paper filtering (YYYY-MM-DD). Default: %(default)s",
    )
    parser.add_argument(
        "--end",
        default=constants.FETCH_DEFAULT_END_DATE,
        help="End date for paper filtering (YYYY-MM-DD). Default: %(default)s",
    )
    parser.add_argument(
        "--category",
        help="Comma-separated list of categories. Default: use default categories",
    )
    parser.add_argument(
        "--config", action="store_true", help="Display current configuration and exit"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Display all available categories with descriptions and exit",
    )
    parser.add_argument(
        "--database",
        type=str,
        default=constants.DEFAULT_DB_NAME,
        help="Name of the SQLite database file. Default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


class ArxivPaperUrlFetcherCLI:
    """Command-line interface for fetching arXiv papers.

    This class encapsulates the functionality to initiate and manage the paper
    fetching process, including configuration management, category validation,
    and process orchestration.

    :param begin: Start date for paper filtering (YYYY-MM-DD)
    :type begin: str
    :param end: End date for paper filtering (YYYY-MM-DD)
    :type end: str
    :param category: Comma-separated list of categories
    :type category: str
    :param config: Flag to display current configuration
    :type config: bool
    :param list: Flag to display all available categories
    :type list: bool
    :param database: Path to SQLite database file
    :type database: str
    :param debug: Flag to enable debug mode
    :type debug: bool
    :raises ValueError: If provided dates or categories are invalid
    """

    def __init__(
        self,
        begin: str,
        end: str,
        category: str,
        config: bool,
        list: bool,
        database: str,
        debug: bool,
    ):
        """
        Initialize the ArxivPaperUrlFetcherCLI.

        :param begin: Start date for paper filtering
        :param end: End date for paper filtering
        :param category: Comma-separated list of categories
        :param config: Flag to display current configuration
        :param list: Flag to display all available categories
        :param database: Name of the SQLite database file
        :param debug: Flag to enable debug mode
        """
        self.begin = begin
        self.end = end
        self.category = category
        self.config = config
        self.list = list
        self.database = database
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database, logger=self.logger)

    def display_config(self) -> None:
        """Display the current configuration settings.

        Prints the configured date range and category settings along with
        category descriptions from the arXiv taxonomy.

        :return: None
        :rtype: None
        """
        print("Current configuration:")
        print(f"Begin date: {self.begin}")
        print(f"End date: {self.end}")
        print("Categories:")
        arxiv_taxonomy_map = self.utils.fetch_arxiv_categories()
        for category in constants.ARXIV_DEFAULT_CATEGORIES:
            description = arxiv_taxonomy_map.get(category, "Unknown")
            print(f"* {category:<20} {description}")

    def display_categories(self) -> None:
        """Display all available arXiv categories with descriptions.

        Fetches the complete arXiv taxonomy and prints each category code
        along with its full description in a formatted list.

        :return: None
        :rtype: None
        """
        print("Available arXiv categories:")
        arxiv_taxonomy_map = self.utils.fetch_arxiv_categories()
        for category, description in arxiv_taxonomy_map.items():
            print(f"* {category:<20} {description}")

    def get_categories(self) -> List[str]:
        """Get and validate the list of categories to process.

        Retrieves categories from either user input or default settings.
        Validates each category against the official arXiv taxonomy.

        :return: List of validated arXiv category codes
        :rtype: List[str]
        :raises ValueError: If any specified category codes are not found in the arXiv taxonomy
        """
        self.logger.debug("Getting categories list")
        categories = (
            [cat.strip() for cat in self.category.split(",")]
            if self.category
            else constants.ARXIV_DEFAULT_CATEGORIES
        )
        self.logger.debug(f"Using categories: {categories}")

        valid_categories = set(self.utils.fetch_arxiv_categories().keys())
        invalid_categories = [cat for cat in categories if cat not in valid_categories]
        if invalid_categories:
            raise ValueError(f"Invalid category codes: {', '.join(invalid_categories)}")
        return categories

    def should_show_info(self) -> bool:
        """Check if information display mode is requested.

        Determines if the script should display configuration or category
        information and exit based on command line flags.

        :return: True if information was displayed and script should exit, False otherwise
        :rtype: bool
        """
        if self.config:
            self.display_config()
            return True
        elif self.list:
            self.display_categories()
            return True
        return False

    def validate_dates(self) -> None:
        """Validate the begin and end dates for paper filtering.

        Ensures both dates are in valid YYYY-MM-DD format and that the end
        date occurs after the begin date.

        :return: None
        :rtype: None
        :raises ValueError: If dates are in invalid format or end date is not after begin date
        """
        self.logger.debug(f"Validating dates: begin={self.begin}, end={self.end}")
        self.utils.validate_date(self.begin, "--begin")
        self.utils.validate_date(self.end, "--end")
        begin_date = datetime.strptime(self.begin, "%Y-%m-%d")
        end_date = datetime.strptime(self.end, "%Y-%m-%d")
        self.logger.debug(f"Parsed dates: begin={begin_date}, end={end_date}")
        if end_date <= begin_date:
            self.logger.error(f"Invalid date range: {begin_date} to {end_date}")
            raise ValueError("End date must be after begin date")

    def process_categories(self) -> None:
        """Process each category for paper fetching.

        Iterates through validated categories and initiates paper fetching for each one.
        Handles keyboard interruptions gracefully to allow clean shutdown.

        :return: None
        :rtype: None
        :raises KeyboardInterrupt: If user interrupts the process
        :raises Exception: If paper fetching fails for any category
        """
        categories = self.get_categories()
        fetcher = ArxivPaperUrlFetcher(self.database, self.debug)
        for category in categories:
            self.logger.info(f"Fetching papers for category: {category}")
            try:
                fetcher.run(category, self.begin, self.end)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received. Stopping the process.")
                break

    def run(self) -> None:
        """
        Run the arXiv paper fetcher.

        This method orchestrates the entire process of fetching arXiv papers based on
        the provided command-line arguments. It handles configuration display, category
        listing, date validation, and paper fetching for each specified category.

        :raises ValueError: If date validation fails
        :raises KeyboardInterrupt: If process is interrupted by user
        :raises Exception: For any other unexpected errors
        """
        try:
            if self.should_show_info():
                return
            self.validate_dates()
            self.process_categories()
        except ValueError as e:
            self.logger.error(f"Validation error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            self.logger.error("Process interrupted by user")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    """Main entry point of the script.

    Parses command line arguments and initiates the paper fetching process.

    :return: None
    :rtype: None
    """
    args = parse_arguments()
    cli = ArxivPaperUrlFetcherCLI(
        begin=args.begin,
        end=args.end,
        category=args.category,
        config=args.config,
        list=args.list,
        database=args.database,
        debug=args.debug,
    )
    cli.run()


if __name__ == "__main__":
    main()
