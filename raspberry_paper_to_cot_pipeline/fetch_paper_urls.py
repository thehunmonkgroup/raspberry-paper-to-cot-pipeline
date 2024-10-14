#!/usr/bin/env python3

"""
Fetch arXiv papers based on date range and categories.

This script provides functionality to fetch arXiv papers for specified categories
within a given date range. It uses the arXiv API to retrieve paper information
and can dynamically fetch the latest category taxonomy from the arXiv website.
"""

import argparse
import sys
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils
from raspberry_paper_to_cot_pipeline.fetch_arxiv_paper_urls_by_category import ArxivPaperUrlFetcher


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
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
    """
    Command-line interface for fetching arXiv papers.

    This class encapsulates the functionality to initiate the paper fetching process.
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

    def validate_date(self, date_str: str, date_name: str) -> None:
        """
        Validate the format of a date string.

        :param date_str: The date string to validate
        :param date_name: The name of the date parameter (for error reporting)
        :raises ValueError: If the date format is invalid
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self.logger.error(f"Invalid date format for {date_name}. Use YYYY-MM-DD.")
            raise ValueError(f"Invalid date format for {date_name}")

    def fetch_arxiv_categories(self) -> Dict[str, str]:
        """
        Fetch arXiv categories from the official taxonomy page.

        :return: Dictionary of category codes and names
        :raises requests.RequestException: If there's an error fetching the categories
        """
        response = requests.get(constants.ARXIV_TAXONOMY_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        categories = {}
        taxonomy_list = soup.find("div", id="category_taxonomy_list")
        if taxonomy_list:
            for accordion_body in taxonomy_list.find_all(
                "div", class_="accordion-body"
            ):
                for column in accordion_body.find_all(
                    "div", class_="column is-one-fifth"
                ):
                    h4 = column.find("h4")
                    if h4:
                        category_code = h4.contents[0].strip()
                        category_name = (
                            h4.find("span").text.strip() if h4.find("span") else ""
                        )
                        # Remove parentheses from the category name
                        category_name = category_name.strip("()")
                        categories[category_code] = category_name
        return categories

    def display_config(self) -> None:
        """Display the current configuration."""
        print("Current configuration:")
        print(f"Begin date: {self.begin}")
        print(f"End date: {self.end}")
        print("Categories:")
        arxiv_taxonomy_map = self.fetch_arxiv_categories()
        for category in constants.ARXIV_DEFAULT_CATEGORIES:
            description = arxiv_taxonomy_map.get(category, "Unknown")
            print(f"* {category:<20} {description}")

    def display_categories(self) -> None:
        """Display all available arXiv categories with descriptions."""
        print("Available arXiv categories:")
        arxiv_taxonomy_map = self.fetch_arxiv_categories()
        for category, description in arxiv_taxonomy_map.items():
            print(f"* {category:<20} {description}")

    def get_categories(self) -> List[str]:
        """
        Get the list of categories to process.

        :return: List of category codes
        """
        if self.category:
            return [cat.strip() for cat in self.category.split(",")]
        return constants.ARXIV_DEFAULT_CATEGORIES

    def run(self) -> None:
        """
        Run the arXiv paper fetcher.

        This method orchestrates the entire process of fetching arXiv papers based on
        the provided command-line arguments. It handles configuration display, category
        listing, date validation, and paper fetching for each specified category.

        :raises Exception: For any other unexpected errors
        """
        try:
            self.fetch_arxiv_categories()

            if self.config:
                self.display_config()
                return
            elif self.list:
                self.display_categories()
                return

            self.validate_date(self.begin, "--begin")
            self.validate_date(self.end, "--end")

            categories = self.get_categories()
            fetcher = ArxivPaperUrlFetcher(self.database, self.debug)

            for category in categories:
                self.logger.info(f"Fetching papers for category: {category}")
                try:
                    fetcher.run(category, self.begin, self.end)
                except KeyboardInterrupt:
                    self.logger.info(
                        "Keyboard interrupt received. Stopping the process."
                    )
                    break
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            sys.exit(1)


def main():
    """Main entry point of the script."""
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
