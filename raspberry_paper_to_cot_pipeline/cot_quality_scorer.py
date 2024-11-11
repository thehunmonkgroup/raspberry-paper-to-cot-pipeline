#!/usr/bin/env python3
"""
This script scores papers based on Chain of Thought (CoT) quality assessment criteria.
It retrieves criteria from the database, calculates a suitability score based on required
and optional criteria, and updates the database with the final score.

The suitability score is calculated as the sum of all criteria scores, but only if all
required criteria are met (non-zero). If any required criteria are missing or zero,
the final score will be 0.
"""

import argparse
import sys
from typing import Optional

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.base_scorer import BaseScorer


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Score papers based on CoT quality assessment criteria."
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


class CoTQualityScorer(BaseScorer):
    """
    A class to handle scoring of papers based on CoT quality assessment criteria.
    """

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        database: str = constants.DEFAULT_DB_NAME,
    ):
        """
        Initialize the CoTQualityScorer.

        :param limit: Maximum number of papers to process
        :param debug: Enable debug logging
        :param database: Path to the SQLite database
        """
        super().__init__(limit=limit, debug=debug, database=database)
        self.criteria_list = constants.COT_QUALITY_ASSESSMENT_CRITERIA
        self.required_criteria_list = constants.REQUIRED_COT_QUALITY_ASSESSMENT_CRITERIA
        self.column_prefix = "cot_quality_assessment_criteria_"
        self.scored_status = constants.STATUS_COT_QUALITY_SCORED
        self.initial_status = constants.STATUS_COT_QUALITY_ASSESSED
        self.score_field_name = "cot_quality_assessment_suitability_score"


def main():
    """Main entry point for CLI usage."""
    args = parse_arguments()
    scorer = CoTQualityScorer(
        limit=args.limit,
        debug=args.debug,
        database=args.database,
    )
    scorer.run()


if __name__ == "__main__":
    main()
