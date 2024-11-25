#!/usr/bin/env python3
"""Script for scoring papers based on Chain of Thought (CoT) voicing assessment criteria.

This module implements functionality to evaluate papers against defined voicing criteria
and calculate their suitability scores. It handles database operations for retrieving
criteria and updating final scores. Extends the BaseScorer class to provide specific
scoring logic for Chain of Thought voicing assessment.

The suitability score calculation follows these rules:
    - Sums all criteria scores if all required criteria are met (non-zero)
    - Returns 0 if any required criteria are missing or zero

The module provides both a command-line interface and programmatic usage through the
CoTVoicingScorer class.
"""

import argparse
from typing import Optional

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.base_scorer import BaseScorer


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    :return: Parsed command-line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Score papers based on CoT voicing assessment criteria."
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


class CoTVoicingScorer(BaseScorer):
    """Class for scoring papers based on CoT voicing assessment criteria.

    This class extends BaseScorer to implement specific scoring logic for Chain of Thought
    voicing assessment. It manages the evaluation of papers against defined criteria and
    calculates suitability scores based on both required and optional criteria.
    """

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        database: str = constants.DEFAULT_DB_NAME,
    ):
        """
        Initialize the CoTVoicingScorer.

        :param limit: Maximum number of papers to process
        :param debug: Enable debug logging
        :param database: Path to the SQLite database
        """
        super().__init__(limit=limit, debug=debug, database=database)
        self.criteria_list = constants.COT_VOICING_ASSESSMENT_CRITERIA
        self.required_criteria_list = constants.REQUIRED_COT_VOICING_ASSESSMENT_CRITERIA
        self.column_prefix = "cot_voicing_assessment_"
        self.scored_status = constants.STATUS_COT_VOICING_SCORED
        self.initial_status = constants.STATUS_COT_VOICING_ASSESSED
        self.score_field_name = "cot_voicing_assessment_suitability_score"


def main() -> None:
    """Main entry point for CLI usage.

    Parses command line arguments and initiates the scoring process for CoT voicing assessment.
    Creates a CoTVoicingScorer instance and runs the scoring pipeline.

    :return: None
    :rtype: None
    """
    args = parse_arguments()
    scorer = CoTVoicingScorer(
        limit=args.limit,
        debug=args.debug,
        database=args.database,
    )
    scorer.run()


if __name__ == "__main__":
    main()
