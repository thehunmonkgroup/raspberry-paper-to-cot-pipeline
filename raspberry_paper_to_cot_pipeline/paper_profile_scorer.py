#!/usr/bin/env python3
"""Script for scoring research papers based on profiling criteria.

This module implements paper scoring functionality by evaluating papers against
defined profiling criteria stored in a database. It calculates suitability scores
by combining required and optional criteria evaluations.

The scoring logic works as follows:
- Retrieves scoring criteria from the database
- Evaluates each paper against all criteria
- Calculates final score as sum of all criteria IF all required criteria are met
- Sets score to 0 if any required criteria score is 0
- Updates database with final scores
"""

import argparse
from typing import Optional

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.base_scorer import BaseScorer


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the paper scoring script.

    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
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


class PaperProfileScorer(BaseScorer):
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
        Initialize the PaperProfileScorer.

        :param limit: Maximum number of papers to process
        :param debug: Enable debug logging
        :param database: Path to the SQLite database
        """
        super().__init__(limit=limit, debug=debug, database=database)
        self.criteria_list = constants.PAPER_PROFILING_CRITERIA
        self.required_criteria_list = constants.REQUIRED_PAPER_PROFILING_CRITERIA
        self.column_prefix = "profiler_criteria_"
        self.scored_status = constants.STATUS_PAPER_PROFILE_SCORED
        self.initial_status = constants.STATUS_PAPER_PROFILED
        self.score_field_name = "profiler_suitability_score"


def main() -> None:
    """Execute the paper scoring process.
    """
    args = parse_arguments()
    scorer = PaperProfileScorer(
        limit=args.limit,
        debug=args.debug,
        database=args.database,
    )
    scorer.run()


if __name__ == "__main__":
    main()
