"""Base class for paper scoring implementations.

This module provides a base class that implements common functionality for scoring
research papers based on defined criteria. It handles database interactions,
criteria validation, and score calculations while providing extension points
for specific scoring implementations.

The module implements a scoring system that:
- Manages database connections for paper data
- Validates scoring criteria
- Calculates composite scores
- Provides extensible base functionality for specific scoring implementations
"""

import sqlite3
from typing import List, Optional, Generator

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils

BATCH_LOG_SIZE = 1000


class BaseScorer:
    """Base class for paper scoring implementations.

    Provides core functionality for scoring papers against defined criteria sets.
    Handles database operations, criteria validation, and score calculations.
    Subclasses must override the following class attributes to implement specific
    scoring behavior.

    Note: This class expects debug logging to be configured via command-line arguments
    in the implementing script.

    :ivar criteria_list: List of all scoring criteria names
    :type criteria_list: List[str]
    :ivar required_criteria_list: List of required criteria names that must be non-zero
    :type required_criteria_list: List[str]
    :ivar column_prefix: Prefix for database column names storing criteria scores
    :type column_prefix: str
    :ivar scored_status: Status value to set after paper scoring is complete
    :type scored_status: str
    :ivar initial_status: Status value to look for when selecting papers to score
    :type initial_status: str
    :ivar score_field_name: Database field name for storing the final calculated score
    :type score_field_name: str
    :ivar limit: Maximum number of papers to process
    :type limit: Optional[int]
    :ivar debug: Enable debug logging
    :type debug: bool
    :ivar database: Path to the SQLite database
    :type database: str
    :ivar logger: Configured logging instance
    :type logger: logging.Logger
    :ivar utils: Utility class instance for common operations
    :type utils: Utils
    """

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        database: str = constants.DEFAULT_DB_NAME,
    ):
        """Initialize the BaseScorer with configuration parameters.

        Sets up logging, utilities, and initializes base configuration for the scoring
        process. Subclasses must override class attributes after calling super().__init__().

        :param limit: Maximum number of papers to process, None for unlimited
        :type limit: Optional[int]
        :param debug: Enable debug logging output
        :type debug: bool
        :param database: Path to the SQLite database file
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
        """Build list of database column names for scoring criteria.

        Generates column names by combining the column prefix with criteria names.
        Can return either all criteria columns or only required criteria columns.

        :param required_only: If True, return only required criteria columns
        :type required_only: bool
        :return: List of prefixed column names for criteria
        :rtype: List[str]
        """
        criteria = self.required_criteria_list if required_only else self.criteria_list
        return [f"{self.column_prefix}{c}" for c in criteria]

    def _get_criteria_score(self, paper: sqlite3.Row, column: str) -> int:
        """Extract and validate the score for a single criterion from paper data.

        Retrieves the score value from the specified column and ensures it is
        a valid integer score.

        :param paper: Database row containing paper scoring data
        :type paper: sqlite3.Row
        :param column: Name of the database column containing the score
        :type column: str
        :return: Validated integer score value
        :rtype: int
        :raises KeyError: If the specified criterion field is missing
        :raises ValueError: If the score value cannot be converted to an integer
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
        """Check if any required scoring criteria are missing or have zero scores.

        Validates that all required criteria have valid non-zero scores in the
        paper data. Used to determine if a paper meets minimum scoring requirements.

        :param paper: Database row containing paper scoring data
        :type paper: sqlite3.Row
        :return: True if any required criteria are missing or have zero scores
        :rtype: bool
        """
        required_columns = self.build_criteria_columns(required_only=True)
        return any(
            self._get_criteria_score(paper, col) == 0 for col in required_columns
        )

    def calculate_suitability_score(self, paper: sqlite3.Row) -> int:
        """Calculate the overall suitability score for a paper.

        Computes a composite score by summing all criteria values, but only if
        all required criteria have non-zero scores. Returns 0 if any required
        criteria are missing or have zero scores.

        :param paper: Database row containing paper scoring data
        :type paper: sqlite3.Row
        :return: Calculated suitability score, or 0 if requirements not met
        :rtype: int
        :raises KeyError: If any criteria fields are missing from paper data
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
        """Retrieve unscored papers from the database for processing.

        Yields papers that have the initial_status and have not yet been scored,
        respecting the configured paper limit if set.

        :return: Generator yielding paper data rows from the database
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
        """Process a single paper by calculating and storing its suitability score.

        Calculates the paper's suitability score and updates the database with
        the score and new processing status. Logs the scoring outcome for tracking.

        :param paper: Database row containing paper data and scoring criteria
        :type paper: sqlite3.Row
        :raises KeyError: If required paper fields or criteria are missing
        :raises sqlite3.Error: If database update operations fail
        """
        self.logger.debug(
            f"Scoring paper {paper['paper_id']}"
        )
        try:
            suitability_score = self.calculate_suitability_score(paper)
            data = {
                "processing_status": self.scored_status,
                self.score_field_name: suitability_score,
            }
            self.utils.update_paper(paper["id"], data)
            self.logger.debug(
                f"Paper {paper['paper_id']} scored and updated to status {self.scored_status}, "
                f"suitability score: {suitability_score}"
            )
        except (KeyError, sqlite3.Error) as processing_error:
            self.logger.error(
                f"Failed to process paper {paper.get('paper_id', 'unknown')}: {processing_error}"
            )
            raise

    def run(self) -> None:
        """Execute the complete paper scoring process.

        Processes all eligible papers in batches, calculating and storing
        suitability scores. Provides progress logging and handles errors.
        Terminates with exit code 1 if an unrecoverable error occurs.
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
            raise
