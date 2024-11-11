"""Base class for paper scoring implementations."""

import sqlite3
import sys
from typing import Any, Dict, List, Optional, Generator

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


class BaseScorer:
    """Base class for paper scoring implementations."""

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        database: str = constants.DEFAULT_DB_NAME,
    ):
        """
        Initialize the BaseScorer.

        :param limit: Maximum number of papers to process
        :param debug: Enable debug logging
        :param database: Path to the SQLite database
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
        :return: List of column names with prefix
        """
        criteria = self.required_criteria_list if required_only else self.criteria_list
        return [f"{self.column_prefix}{c}" for c in criteria]

    def missing_required_criteria(self, paper: Dict[str, Any]) -> bool:
        """
        Check if any required criteria are missing or zero.

        :param paper: Paper data dictionary containing criteria scores
        :return: True if any required criteria are missing or zero
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

    def calculate_suitability_score(self, paper: sqlite3.Row) -> int:
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
        Retrieve papers for scoring from database.

        :return: Generator of paper data
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
        except sqlite3.Error as e:
            self.logger.error(f"Database error fetching papers: {e}")
            raise

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Process a single paper.

        :param paper: Paper data as a sqlite3.Row containing criteria fields and metadata
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
        except (KeyError, sqlite3.Error) as e:
            self.logger.error(
                f"Failed to process paper {paper.get('paper_id', 'unknown')}: {e}"
            )
            raise

    def run(self) -> None:
        """
        Run the scoring process.

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
                if processed_count % 1000 == 0:
                    self.logger.info(f"Processed {processed_count} papers so far.")
            self.logger.info(
                f"Scoring process completed. Total papers scored: {processed_count}"
            )
        except Exception as e:
            self.logger.error(f"An error occurred during the scoring process: {e}")
            sys.exit(1)
