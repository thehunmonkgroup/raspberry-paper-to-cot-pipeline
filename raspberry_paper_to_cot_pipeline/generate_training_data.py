#!/usr/bin/env python3
"""Generate consolidated training data from individual paper training artifacts.

This script processes papers that have been quality scored and combines their training
artifacts into a single consolidated training file. It performs the following:

- Checks paper suitability scores against a configurable minimum threshold
- Collects individual training artifacts for papers meeting the threshold
- Combines qualified artifacts into a single JSONL training file
- Handles error recovery and logging throughout the process

The script is designed to be run as part of the paper-to-CoT pipeline after
quality assessment has been completed.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, Generator, Tuple
import sys

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    :return: Namespace containing the parsed command-line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate consolidated training data from paper training artifacts."
    )
    parser.add_argument(
        "--database",
        type=str,
        default=constants.DEFAULT_DB_NAME,
        help="Path to the SQLite database. Default: %(default)s",
    )
    parser.add_argument(
        "--suitability-score",
        type=int,
        default=constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        help="Minimum suitability score required. Default: %(default)s",
    )
    parser.add_argument(
        "--training-file-name",
        type=str,
        default=constants.DEFAULT_CONSOLIDATED_TRAINING_FILENAME,
        help="Name of the output training file. Default: %(default)s",
    )
    parser.add_argument(
        "--training-artifacts-directory",
        type=str,
        default=constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        help="Directory containing training artifacts. Default: %(default)s",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional. Limit the number of papers to process. Default: no limit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


class TrainingDataGenerator:
    """Handle generation of consolidated training data from paper artifacts.

    This class manages the process of collecting and combining training artifacts from
    papers that meet quality criteria. It provides functionality for:

    - Fetching qualified papers from the database
    - Processing individual paper training artifacts
    - Combining artifacts into a consolidated training file
    - Progress tracking and error handling

    :ivar database: Path to the SQLite database
    :type database: str
    :ivar suitability_score: Minimum required suitability score
    :type suitability_score: int
    :ivar training_file_name: Name of the output training file
    :type training_file_name: str
    :ivar training_artifacts_directory: Directory containing training artifacts
    :type training_artifacts_directory: Path
    :ivar limit: Maximum number of papers to process
    :type limit: Optional[int]
    :ivar debug: Enable debug logging
    :type debug: bool
    :ivar logger: Logger instance for this class
    :type logger: logging.Logger
    :ivar utils: Utility class instance
    :type utils: Utils
    """

    # Number of papers to process before logging progress
    PROGRESS_REPORT_INTERVAL = 100

    def __init__(
        self,
        database: str = constants.DEFAULT_DB_NAME,
        suitability_score: int = constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        training_file_name: str = constants.DEFAULT_CONSOLIDATED_TRAINING_FILENAME,
        training_artifacts_directory: Path = constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        limit: Optional[int] = None,
        debug: bool = False,
    ):
        """Initialize the TrainingDataGenerator.

        :param database: Path to the SQLite database
        :type database: str
        :param suitability_score: Minimum required suitability score
        :type suitability_score: int
        :param training_file_name: Name of the output training file
        :type training_file_name: str
        :param training_artifacts_directory: Directory containing training artifacts
        :type training_artifacts_directory: Union[str, Path]
        :param limit: Maximum number of papers to process
        :type limit: Optional[int]
        :param debug: Enable debug logging
        :type debug: bool
        """
        self.database = database
        self.suitability_score = suitability_score
        self.training_file_name = training_file_name
        self.training_artifacts_directory = Path(training_artifacts_directory)
        self.limit = limit
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(
            database=self.database,
            training_artifacts_directory=self.training_artifacts_directory,
            logger=self.logger,
        )

    def fetch_qualified_papers(self) -> Generator[sqlite3.Row, None, None]:
        """Fetch papers that have been quality scored.

        Retrieves papers from the database that have completed quality scoring,
        ordered by their processing date.

        :return: Generator yielding qualified paper records
        :rtype: Generator[sqlite3.Row, None, None]
        """
        select_columns = constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + [
            "cot_quality_assessment_suitability_score"
        ]
        self.logger.debug(
            f"Fetching papers with status {constants.STATUS_COT_QUALITY_SCORED}, "
            f"columns: {select_columns}, limit: {self.limit}"
        )
        return self.utils.fetch_papers_by_processing_status(
            status=constants.STATUS_COT_QUALITY_SCORED,
            select_columns=select_columns,
            limit=self.limit,
        )

    def process_paper(self, paper: sqlite3.Row) -> Optional[Dict[str, Any]]:
        """Process a single paper's training data if it meets criteria.

        Checks if the paper meets the minimum suitability score and attempts to
        load its training artifact if qualified.

        :param paper: Paper record from database
        :type paper: sqlite3.Row
        :return: Training data dictionary if paper qualifies and artifact exists, None otherwise
        :rtype: Optional[Dict[str, Any]]
        """
        score = paper["cot_quality_assessment_suitability_score"]
        if score < self.suitability_score:
            self.logger.info(
                f"Skipping paper {paper['paper_id']}: score {score} below threshold {self.suitability_score}"
            )
            return None

        try:
            filename = constants.TRAINING_ARTIFACT_PATTERN.format(
                paper_id=paper["paper_id"]
            )
            return self.utils.read_training_artifact(filename)
        except FileNotFoundError:
            self.logger.warning(
                f"Training artifact not found for paper {paper['paper_id']}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Error processing training data for paper {paper['paper_id']}: {e}"
            )
            return None

    def initialize_output_file(self) -> Path:
        """Create and initialize the output file for writing training data.

        Creates the output directory if it doesn't exist, removes any existing
        output file, and creates a new empty file.

        :return: Path object pointing to the initialized output file
        :rtype: Path
        :raises OSError: If file creation or directory creation fails
        """
        self.logger.debug(
            f"Initializing output file in {self.training_artifacts_directory}"
        )
        self.utils.ensure_directory_exists(self.training_artifacts_directory)

        output_path = self.training_artifacts_directory / self.training_file_name
        self.logger.debug(f"Removing existing file if present: {output_path}")
        output_path.unlink(missing_ok=True)

        self.logger.debug(f"Creating new empty file: {output_path}")
        output_path.touch()
        return output_path

    def append_training_data(
        self, output_path: Path, data: Dict[str, Any], paper_id: str
    ) -> None:
        """Append a single training data entry to the JSONL file.

        Converts the training data dictionary to JSON and appends it as a new
        line to the output file.

        :param output_path: Path to the output JSONL file
        :type output_path: Path
        :param data: Dictionary containing the training data to append
        :type data: Dict[str, Any]
        :param paper_id: ID of the paper being processed
        :type paper_id: str
        :raises IOError: If writing to the file fails
        """
        self.logger.debug(
            f"Appending training data entry for paper {paper_id} to {output_path}"
        )
        with open(output_path, "a") as f:
            f.write(json.dumps(data) + "\n")

    def process_papers(self, output_path: Path) -> Tuple[int, int]:
        """Process all papers and return counts.

        Iterates through qualified papers, processes their training data, and
        writes successful results to the output file. Tracks and reports progress
        periodically.

        :param output_path: Path to the output file where training data will be written
        :type output_path: Path
        :return: Tuple containing counts of processed and skipped papers
        :rtype: Tuple[int, int]
        :raises Exception: If any unhandled error occurs during processing
        """
        processed_count = 0
        skipped_count = 0

        for paper in self.fetch_qualified_papers():
            self.logger.debug(f"Processing paper {paper['paper_id']}")
            data = self.process_paper(paper)
            if data:
                self.append_training_data(output_path, data, paper["paper_id"])
                processed_count += 1
                self.logger.debug(f"Successfully processed paper {paper['paper_id']}")
            else:
                skipped_count += 1
                self.logger.debug(f"Skipped paper {paper['paper_id']}")

            if (
                processed_count % self.PROGRESS_REPORT_INTERVAL == 0
                and processed_count > 0
            ):
                self.logger.info(
                    f"Processed {processed_count} papers, skipped {skipped_count}"
                )

        return processed_count, skipped_count

    def run(self) -> None:
        """Run the training data generation process.

        Orchestrates the complete training data generation workflow:
        - Initializes the output file
        - Processes all qualified papers
        - Reports final statistics
        - Handles any errors that occur

        :raises SystemExit: With code 1 if an unrecoverable error occurs
        """
        self.logger.info(
            f"Starting training data generation. "
            f"Database: {self.database}, "
            f"Minimum score: {self.suitability_score}, "
            f"Limit: {self.limit}"
        )

        try:
            output_path = self.initialize_output_file()
            processed_count, skipped_count = self.process_papers(output_path)

            if processed_count > 0:
                self.logger.info(
                    f"Training data generation completed. "
                    f"Processed: {processed_count}, "
                    f"Skipped: {skipped_count}, "
                    f"Output file: {output_path}"
                )
            else:
                self.logger.warning("No training data was generated")

        except Exception as e:
            self.logger.error(f"An error occurred during training data generation: {e}")
            sys.exit(1)


def main():
    """Main entry point for CLI usage.

    Parses command line arguments and runs the training data generation process.
    """
    args = parse_arguments()
    generator = TrainingDataGenerator(
        database=args.database,
        suitability_score=args.suitability_score,
        training_file_name=args.training_file_name,
        training_artifacts_directory=args.training_artifacts_directory,
        limit=args.limit,
        debug=args.debug,
    )
    generator.run()


if __name__ == "__main__":
    main()
