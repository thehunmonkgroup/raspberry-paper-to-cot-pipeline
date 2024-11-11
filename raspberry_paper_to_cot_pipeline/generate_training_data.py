#!/usr/bin/env python3
"""
This script generates consolidated training data from individual paper training artifacts.

It processes papers that have been quality scored, checking their suitability scores
against a minimum threshold. For papers that meet the threshold, their individual
training artifacts are collected and combined into a single training file.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator, Tuple
import sys

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
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
    """
    A class to handle generation of consolidated training data from paper artifacts.
    """

    def __init__(
        self,
        database: str = constants.DEFAULT_DB_NAME,
        suitability_score: int = constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        training_file_name: str = constants.DEFAULT_CONSOLIDATED_TRAINING_FILENAME,
        training_artifacts_directory: Path = constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        limit: Optional[int] = None,
        debug: bool = False,
    ):
        """
        Initialize the TrainingDataGenerator.

        :param database: Path to the SQLite database
        :param suitability_score: Minimum required suitability score
        :param training_file_name: Name of the output training file
        :param training_artifacts_directory: Directory containing training artifacts
        :param limit: Maximum number of papers to process
        :param debug: Enable debug logging
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
        """
        Fetch papers that have been quality scored.

        :return: Generator of qualified papers
        """
        select_columns = constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + [
            "cot_quality_assessment_suitability_score"
        ]
        return self.utils.fetch_papers_by_processing_status(
            status=constants.STATUS_COT_QUALITY_SCORED,
            select_columns=select_columns,
            limit=self.limit,
        )

    def process_paper(self, paper: sqlite3.Row) -> Optional[Dict[str, Any]]:
        """
        Process a single paper's training data if it meets criteria.

        :param paper: Paper data dictionary
        :return: Training data if paper qualifies, None otherwise
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
        """Create and initialize the output file."""
        self.utils.ensure_directory_exists(self.training_artifacts_directory)
        output_path = self.training_artifacts_directory / self.training_file_name
        output_path.unlink(missing_ok=True)
        output_path.touch()
        return output_path

    def append_training_data(self, output_path: Path, data: Dict[str, Any]) -> None:
        """Append single training data entry to JSONL file."""
        with open(output_path, 'a') as f:
            f.write(json.dumps(data) + '\n')

    def process_papers(self, output_path: Path) -> Tuple[int, int]:
        """
        Process all papers and return counts.

        :param output_path: Path to the output file
        :return: Tuple of (processed_count, skipped_count)
        """
        processed_count = 0
        skipped_count = 0

        for paper in self.fetch_qualified_papers():
            data = self.process_paper(paper)
            if data:
                self.append_training_data(output_path, data)
                processed_count += 1
            else:
                skipped_count += 1

            if processed_count % 100 == 0 and processed_count > 0:
                self.logger.info(
                    f"Processed {processed_count} papers, skipped {skipped_count}"
                )

        return processed_count, skipped_count

    def run(self) -> None:
        """Run the training data generation process."""
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
    """Main entry point for CLI usage."""
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
