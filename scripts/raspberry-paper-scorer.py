#!/usr/bin/env python3

"""
This script scores papers based on profiling criteria.
It retrieves criteria from the database, calculates a suitability score, and updates the database.
"""

import argparse
import sqlite3
import logging
from typing import Dict, List

REQUIRED_CRITERIA: List[str] = [
    "criteria_clear_question",
    "criteria_definitive_answer",
    "criteria_complex_reasoning",
]


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Score papers based on profiling criteria."
    )
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperScorer:
    """
    A class to handle paper scoring based on profiling criteria.
    """

    def __init__(self, database: str, paper_id: str, paper_url: str, debug: bool):
        """
        Initialize the PaperScorer with individual arguments.

        :param database: Path to the SQLite database
        :param paper_id: ID of the paper in the database
        :param paper_url: URL of the paper
        :param debug: Enable debug logging
        """
        self.database = database
        self.paper_id = paper_id
        self.paper_url = paper_url
        self.debug = debug
        self.setup_logging()

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def missing_required_criteria(self, criteria: Dict[str, int]) -> bool:
        """
        Check if any required criteria are missing.

        :param criteria: Dictionary of criteria and their values
        :return: True if any required criteria are missing, False otherwise
        """
        return any(criteria[c] == 0 for c in REQUIRED_CRITERIA)

    def calculate_suitability_score(self, criteria: Dict[str, int]) -> int:
        """
        Calculate the suitability score based on criteria.

        :param criteria: Dictionary of criteria and their values
        :return: Calculated suitability score
        """
        return 0 if self.missing_required_criteria(criteria) else sum(criteria.values())

    def update_database(self, suitability_score: int) -> None:
        """
        Update the processing status and suitability score of the paper in the database.

        :param suitability_score: Calculated suitability score
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE papers
                SET processing_status = 'scored', suitability_score = ?
                WHERE id = ?
            """,
                (suitability_score, self.paper_id),
            )
            conn.commit()
            print(
                f"Updated suitability score for paper {self.paper_url} to {suitability_score}"
            )
            print(f"Set processing status for paper {self.paper_url} to 'scored'")
            self.logger.debug(f"Updated database for paper {self.paper_id}")
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_criteria_from_database(self) -> Dict[str, int]:
        """
        Retrieve criteria for the paper from the database.

        :return: Dictionary of criteria and their values
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT criteria_clear_question, criteria_definitive_answer, criteria_complex_reasoning,
                       criteria_coherent_structure, criteria_layperson_comprehensible, criteria_minimal_jargon,
                       criteria_illustrative_examples, criteria_significant_insights, criteria_verifiable_steps,
                       criteria_overall_suitability
                FROM papers
                WHERE id = ?
            """,
                (self.paper_id,),
            )
            result = cursor.fetchone()
            if result:
                return {
                    "criteria_clear_question": result[0],
                    "criteria_definitive_answer": result[1],
                    "criteria_complex_reasoning": result[2],
                    "criteria_coherent_structure": result[3],
                    "criteria_layperson_comprehensible": result[4],
                    "criteria_minimal_jargon": result[5],
                    "criteria_illustrative_examples": result[6],
                    "criteria_significant_insights": result[7],
                    "criteria_verifiable_steps": result[8],
                    "criteria_overall_suitability": result[9],
                }
            else:
                raise ValueError(f"No criteria found for paper ID {self.paper_id}")
        finally:
            if conn:
                conn.close()

    def run(self) -> None:
        """Execute the main logic of the paper scoring process."""
        criteria = self.get_criteria_from_database()
        suitability_score = self.calculate_suitability_score(criteria)
        self.update_database(suitability_score)
        self.logger.info("Paper scoring process completed successfully")


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    scorer = PaperScorer(
        database=args.database,
        paper_id=args.paper_id,
        paper_url=args.paper_url,
        debug=args.debug,
    )
    scorer.run()


if __name__ == "__main__":
    main()
