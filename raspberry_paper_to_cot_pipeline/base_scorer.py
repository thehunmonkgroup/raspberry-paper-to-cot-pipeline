"""
Base class for paper scoring implementations.

This module provides a base class that implements common functionality for scoring
research papers based on defined criteria. It handles database interactions,
criteria validation, and score calculations while providing extension points
for specific scoring implementations.
"""

import sqlite3
import sys
from typing import List, Optional, Generator

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils

BATCH_LOG_SIZE = 1000


class BaseScorer:
    """
    Base class for paper scoring implementations.

    Provides core functionality for scoring papers against defined criteria sets.
    Handles database operations, criteria validation, and score calculations.
    Subclasses must override criteria_list, required_criteria_list, column_prefix,
    scored_status, initial_status, and score_field_name.

    Note: This class expects debug logging to be configured via command-line arguments
    in the implementing script.

    :ivar criteria_list: List of all scoring criteria names
    :type criteria_list: List[str]
    :ivar required_criteria_list: List of required criteria names
    :type required_criteria_list: List[str]
    :ivar column_prefix: Prefix for database column names
    :type column_prefix: str
    :ivar scored_status: Status to set after scoring
    :type scored_status: str
    :ivar initial_status: Status to look for when selecting papers
    :type initial_status: str
    :ivar score_field_name: Name of the field to store the final score
    :type score_field_name: str
    """

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        database: str = constants.DEFAULT_DB_NAME,
    ):
        """
        Initialize the BaseScorer.

        :param limit: Maximum number of papers to process
        :type limit: Optional[int]
        :param debug: Enable debug logging
        :type debug: bool
        :param database: Path to the SQLite database
        :type database: str
        """
        self.limit = limit
        self.debug = debug
        self.database = database
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database, logger=self.logger)

        # These must be overridden by subclasses
        self.criteria_list: List[str] = []
        self.required_criteria_list: List[str] = []
        self.column_prefix: str = ""
        self.scored_status: str = ""
        self.initial_status: str = ""
        self.score_field_name: str = ""

    def build_criteria_columns(self, required_only: bool = False) -> List[str]:
        """
        Build list of criteria column names.

        :param required_only: If True, return only required criteria columns
        :type required_only: bool
        :return: List of column names with prefix
        :rtype: List[str]
        """
        criteria = self.required_criteria_list if required_only else self.criteria_list
        return [f"{self.column_prefix}{c}" for c in criteria]

    def _get_criteria_score(self, paper: sqlite3.Row, column: str) -> int:
        """
        Get score for a single criterion.

        :param paper: Paper data row
        :type paper: sqlite3.Row
        :param column: Column name to get score from
        :type column: str
        :return: Integer score value
        :rtype: int
        :raises KeyError: If criterion field is missing
        :raises ValueError: If score value is invalid
        """
        try:
            return int(paper[column])
        except KeyError:
            self.logger.error(f"Missing criteria field: {column}")
            raise
        except ValueError:
            self.logger.error(f"Invalid score value for {column}")
            raise

    def missing_required_criteria(self, paper: sqlite3.Row) -> bool:
        """
        Check if any required criteria are missing or zero.

        :param paper: Paper data row containing criteria scores
        :type paper: sqlite3.Row
        :return: True if any required criteria are missing or zero
        :rtype: bool
        :raises KeyError: If required criteria fields are missing
        """
        required_columns = self.build_criteria_columns(required_only=True)
        return any(
            self._get_criteria_score(paper, col) == 0 for col in required_columns
        )

    def calculate_suitability_score(self, paper: sqlite3.Row) -> int:
        """
        Calculate the suitability score based on criteria.

        The score is the sum of all criteria values if all required criteria are non-zero.
        Returns 0 if any required criteria are missing or zero.

        :param paper: Paper data dictionary containing criteria scores
        :type paper: sqlite3.Row
        :return: Calculated suitability score (0 if required criteria not met)
        :rtype: int
        :raises KeyError: If criteria fields are missing from paper data
        """
        try:
            if self.missing_required_criteria(paper):
                return 0
            criteria = [int(paper[c]) for c in self.build_criteria_columns()]
            return sum(criteria)
        except KeyError as key_error:
            self.logger.error(f"Missing criteria field in paper data: {key_error}")
            raise

    def fetch_papers_for_scoring(self) -> Generator[sqlite3.Row, None, None]:
        """
        Retrieve papers for scoring from database.

        :return: Generator yielding paper data rows
        :rtype: Generator[sqlite3.Row, None, None]
        :raises sqlite3.Error: If database operations fail
        """
        select_columns = (
            constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + self.build_criteria_columns()
        )
        try:
            yield from self.utils.fetch_papers_by_processing_status(
                status=self.initial_status,
                select_columns=select_columns,
                limit=self.limit,
            )
        except sqlite3.Error as db_error:
            self.logger.error(f"Database error fetching papers: {db_error}")
            raise

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Process a single paper by calculating and storing its score.

        :param paper: Paper data as a sqlite3.Row containing criteria fields and metadata
        :type paper: sqlite3.Row
        :raises KeyError: If required paper fields are missing
        :raises sqlite3.Error: If database update fails
        """
        try:
            suitability_score = self.calculate_suitability_score(paper)
            data = {
                "processing_status": self.scored_status,
                self.score_field_name: suitability_score,
            }
            self.utils.update_paper(paper["id"], data)
            self.logger.info(
                f"Paper {paper['paper_id']} scored and updated to status {self.scored_status}, "
                f"suitability score: {suitability_score}"
            )
        except (KeyError, sqlite3.Error) as processing_error:
            self.logger.error(
                f"Failed to process paper {paper.get('paper_id', 'unknown')}: {processing_error}"
            )
            raise

    def run(self) -> None:
        """
        Run the scoring process for all eligible papers.

        Processes papers in batches, calculating and storing scores for each.
        Exits with status code 1 if an unrecoverable error occurs.

        :raises SystemExit: If an unrecoverable error occurs
        """
        self.logger.info(
            f"Starting scoring process. Database: {self.database}, Limit: {self.limit}"
        )
        try:
            papers = self.fetch_papers_for_scoring()
            processed_count = 0
            for paper in papers:
                self.process_paper(paper)
                processed_count += 1
                if processed_count % BATCH_LOG_SIZE == 0:
                    self.logger.info(f"Processed {processed_count} papers so far.")
            self.logger.info(
                f"Scoring process completed. Total papers scored: {processed_count}"
            )
        except Exception as processing_error:
            self.logger.error(
                f"An error occurred during the scoring process: {processing_error}"
            )
            sys.exit(1)
