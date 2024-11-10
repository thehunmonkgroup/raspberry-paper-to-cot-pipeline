#!/usr/bin/env python3
"""
This script scores papers based on profiling criteria.
It retrieves criteria from the database, calculates a suitability score based on required
and optional criteria, and updates the database with the final score.

The suitability score is calculated as the sum of all criteria scores, but only if all
required criteria are met (non-zero). If any required criteria are missing or zero,
the final score will be 0.
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

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        database: str = constants.DEFAULT_DB_NAME,
    ):
        """
        Initialize the PaperScorer.

        :param database: Path to the SQLite database
        :param limit: Limit the number of papers to process (optional)
        :param debug: Enable debug logging
        """
        self.limit = limit
        self.debug = debug
        self.database = database
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database, logger=self.logger)

    def build_criteria_columns(self, required_only: bool = False) -> List[str]:
        """
        Build a list of criteria column names.

        :param required_only: If True, return only required criteria columns
        :return: List of column names prefixed with 'profiler_criteria_'
        """
        criteria = (
            constants.REQUIRED_PROFILING_CRITERIA
            if required_only
            else constants.PROFILING_CRITERIA
        )
        return [f"profiler_criteria_{c}" for c in criteria]

    def missing_required_criteria(self, paper: Dict[str, Any]) -> bool:
        """
        Check if any required criteria are missing or zero.

        :param paper: Paper data dictionary containing criteria scores
        :return: True if any required criteria are missing or zero, False otherwise
        :raises KeyError: If required criteria fields are missing from paper data
        """
        try:
            return any(
                int(paper[c]) == 0
                for c in self.build_criteria_columns(required_only=True)
            )
        except KeyError as e:
            self.logger.error(f"Missing required criteria field in paper data: {e}")
            raise

    def calculate_suitability_score(self, paper: Dict[str, Any]) -> int:
        """
        Calculate the suitability score based on criteria.

        The score is the sum of all criteria values if all required criteria are non-zero.
        Returns 0 if any required criteria are missing or zero.

        :param paper: Paper data dictionary containing criteria scores
        :return: Calculated suitability score (0 if required criteria not met)
        :raises KeyError: If criteria fields are missing from paper data
        """
        try:
            if self.missing_required_criteria(paper):
                return 0
            criteria = [int(paper[c]) for c in self.build_criteria_columns()]
            return sum(criteria)
        except KeyError as e:
            self.logger.error(f"Missing criteria field in paper data: {e}")
            raise

    def fetch_papers_for_scoring(self) -> Generator[sqlite3.Row, None, None]:
        """
        Retrieve criteria for the paper from the database.

        :return: Generator of paper data
        """
        select_columns = (
            constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + self.build_criteria_columns()
        )
        return self.utils.fetch_papers_by_processing_status(
            status=constants.STATUS_PAPER_PROFILED,
            select_columns=select_columns,
            limit=self.limit,
        )

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Execute the main logic of the paper scoring process.

        :param paper: Paper data as a sqlite3.Row containing criteria fields and paper metadata
        :return: None
        :raises KeyError: If required paper fields are missing
        :raises sqlite3.Error: If database update fails
        """
        try:
            suitability_score = self.calculate_suitability_score(paper)
            data = {
                "processing_status": constants.STATUS_PAPER_PROFILE_SCORED,
                "profiler_suitability_score": suitability_score,
            }
            self.utils.update_paper(paper["id"], data)
            self.logger.info(
                f"Paper {paper['paper_id']} scored and updated to status {constants.STATUS_PAPER_PROFILE_SCORED}, "
                f"suitability score: {suitability_score}"
            )
        except (KeyError, sqlite3.Error) as e:
            self.logger.error(
                f"Failed to process paper {paper.get('paper_id', 'unknown')}: {e}"
            )
            raise

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
    """Main entry point for CLI usage."""
    args = parse_arguments()
    scorer = PaperScorer(
        limit=args.limit,
        debug=args.debug,
        database=args.database,
    )
    scorer.run()


if __name__ == "__main__":
    main()
