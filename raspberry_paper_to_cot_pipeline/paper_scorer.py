#!/usr/bin/env python3
"""
This script scores papers based on profiling criteria.
It retrieves criteria from the database, calculates a suitability score, and updates the database.
"""

import argparse
import sqlite3
from typing import Any, Dict, List, Optional, Generator
import sys

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Score papers based on profiling criteria."
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
        help="Optional. Limit the number of papers to score. Default: no limit",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperScorer:
    """
    A class to handle scoring of papers based on profiling criteria.
    """

    def __init__(self, database: Optional[str], limit: Optional[int], debug: bool):
        """
        Initialize the PaperScorer.

        :param database: Path to the SQLite database
        :param limit: Limit the number of papers to process (optional)
        :param debug: Enable debug logging
        """
        self.database = database or constants.DEFAULT_DB_NAME
        self.limit = limit
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database, logger=self.logger)

    def build_criteria_columns(self) -> List[str]:
        """Build a list of criteria column names."""
        return [f"criteria_{c}" for c in constants.PROFILING_CRITERIA]

    def build_required_criteria_columns(self) -> List[str]:
        """Build a list of required criteria column names."""
        return [f"criteria_{c}" for c in constants.REQUIRED_PROFILING_CRITERIA]

    def missing_required_criteria(self, paper: Dict[str, Any]) -> bool:
        """
        Check if any required criteria are missing.

        :param paper: Paper data
        :return: True if any required criteria are missing, False otherwise
        """
        return any(int(paper[c]) == 0 for c in self.build_required_criteria_columns())

    def calculate_suitability_score(self, paper: Dict[str, Any]) -> int:
        """
        Calculate the suitability score based on criteria.

        :param paper: Paper data
        :return: Calculated suitability score
        """
        if self.missing_required_criteria(paper):
            return 0
        criteria = [int(paper[c]) for c in self.build_criteria_columns()]
        return sum(criteria)

    def fetch_papers_for_scoring(self) -> Generator[sqlite3.Row, None, None]:
        """
        Retrieve criteria for the paper from the database.

        :return: Generator of paper data
        """
        select_columns = (
            constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + self.build_criteria_columns()
        )
        return self.utils.fetch_papers_by_processing_status(
            status=constants.STATUS_PROFILED,
            select_columns=select_columns,
            limit=self.limit,
        )

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Execute the main logic of the paper scoring process.

        :param paper: Paper data
        """
        suitability_score = self.calculate_suitability_score(paper)
        data = {
            "processing_status": constants.STATUS_SCORED,
            "suitability_score": suitability_score,
        }
        self.utils.update_paper(paper["id"], data)
        self.logger.info(
            f"Scored paper {paper['paper_id']}, suitability score: {suitability_score}"
        )

    def run(self) -> None:
        """Run the paper scoring process."""
        self.logger.info(
            f"Starting paper scoring process. Database: {self.database}, Limit: {self.limit}"
        )
        try:
            papers = self.fetch_papers_for_scoring()
            processed_count = 0
            for paper in papers:
                self.process_paper(paper)
                processed_count += 1
                if processed_count % 1000 == 0:
                    self.logger.info(f"Processed {processed_count} papers so far.")
            self.logger.info(
                f"Paper scoring process completed. Total papers scored: {processed_count}"
            )
        except Exception as e:
            self.logger.error(
                f"An error occurred during the paper scoring process: {e}"
            )
            sys.exit(1)


def main():
    """Main function to run the script."""
    args = parse_arguments()
    scorer = PaperScorer(database=args.database, limit=args.limit, debug=args.debug)
    scorer.run()


if __name__ == "__main__":
    main()
