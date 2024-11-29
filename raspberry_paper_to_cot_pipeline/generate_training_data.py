#!/usr/bin/env python3
"""Generate consolidated training data from individual paper training artifacts.

This script processes papers that have been quality scored and combines their training
artifacts into a single consolidated training file. It performs the following:

- Checks paper suitability scores against configurable minimum thresholds
- Collects individual training artifacts for papers meeting the thresholds
- Combines qualified artifacts into a single JSONL training file
- Handles error recovery and logging throughout the process

The script is designed to be run as part of the paper-to-CoT pipeline after
quality assessment has been completed.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, Generator, Tuple, Union, TextIO
import sys

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    :return: Namespace containing the parsed command-line arguments
    :rtype: argparse.Namespace
    :raises ArgumentError: If invalid argument values are provided
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
        "--cot-quality-assessment-suitability-score",
        type=int,
        default=constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        help="Minimum CoT quality assessment suitability score required. Default: %(default)s",
    )
    parser.add_argument(
        "--cot-voicing-assessment-suitability-score",
        type=int,
        default=constants.COT_VOICING_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        help="Minimum CoT voicing assessment suitability score required. Default: %(default)s",
    )
    parser.add_argument(
        "--jsonl-training-file-name",
        type=str,
        default=constants.DEFAULT_JSONL_TRAINING_FILENAME,
        help="Name of the JSONL training data output file. Default: %(default)s",
    )
    parser.add_argument(
        "--human-readable-training-stub",
        type=str,
        default=constants.DEFAULT_HUMAN_READABLE_TRAINING_STUB,
        help="Stub name of the human-readable markdown training data output file. Default: %(default)s",
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
    """

    # Number of papers to process before logging progress
    PROGRESS_REPORT_INTERVAL = 100

    def __init__(
        self,
        database: str = constants.DEFAULT_DB_NAME,
        cot_quality_assessment_suitability_score: int = constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        cot_voicing_assessment_suitability_score: int = constants.COT_VOICING_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        jsonl_training_file_name: str = constants.DEFAULT_JSONL_TRAINING_FILENAME,
        human_readable_stub: str = constants.DEFAULT_HUMAN_READABLE_TRAINING_STUB,
        training_artifacts_directory: Union[
            str, Path
        ] = constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        limit: Optional[int] = None,
        debug: bool = False,
    ):
        """Initialize the TrainingDataGenerator.

        :param database: Path to the SQLite database
        :type database: str
        :param cot_quality_assessment_suitability_score: Minimum required suitability score for CoT quality assessment
        :type cot_quality_assessment_suitability_score: int
        :param cot_voicing_assessment_suitability_score: Minimum required suitability score for CoT voicing assessment
        :type cot_voicing_assessment_suitability_score: int
        :param jsonl_training_file_name: Name of the JSONL training data output file
        :type jsonl_training_file_name: str
        :param human_readable_stub: Stub for the human-readable training data output file
        :type human_readable_stub: str
        :param training_artifacts_directory: Directory containing training artifacts
        :type training_artifacts_directory: Union[str, Path]
        :param limit: Maximum number of papers to process
        :type limit: Optional[int]
        :param debug: Enable debug logging
        :type debug: bool
        """
        self.database = database
        self.cot_quality_assessment_suitability_score = (
            cot_quality_assessment_suitability_score
        )
        self.cot_voicing_assessment_suitability_score = (
            cot_voicing_assessment_suitability_score
        )
        self.jsonl_training_file_name = jsonl_training_file_name
        self.human_readable_stub = human_readable_stub
        self.preset_files: Dict[str, TextIO] = {}
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

        :return: Generator yielding qualified paper records with quality assessment scores
        :rtype: Generator[sqlite3.Row, None, None]
        """
        select_columns = constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + [
            "cot_quality_assessment_suitability_score",
            "cot_voicing_assessment_suitability_score",
        ]
        self.logger.debug(
            f"Fetching papers with status {constants.STATUS_COT_VOICING_SCORED}, "
            f"columns: {select_columns}, limit: {self.limit}"
        )
        return self.utils.fetch_papers_by_processing_status(
            status=constants.STATUS_COT_VOICING_SCORED,
            select_columns=select_columns,
            limit=self.limit,
        )

    def paper_qualifies_for_training_data(self, paper: sqlite3.Row) -> bool:
        """Checks if a paper meets the minimum suitability scores.

        :param paper: Paper record from database
        :type paper: sqlite3.Row
        :return: True if paper meets minimum suitability scores, False otherwise
        :rtype: bool
        """
        quality_score = paper["cot_quality_assessment_suitability_score"]
        voicing_score = paper["cot_voicing_assessment_suitability_score"]
        if quality_score < self.cot_quality_assessment_suitability_score:
            self.logger.info(
                f"Skipping paper {paper['paper_id']}: CoT quality score {quality_score} below threshold {self.cot_quality_assessment_suitability_score}"
            )
            return False
        if voicing_score < self.cot_voicing_assessment_suitability_score:
            self.logger.info(
                f"Skipping paper {paper['paper_id']}: CoT voicing score {voicing_score} below threshold {self.cot_voicing_assessment_suitability_score}"
            )
            return False
        self.logger.debug(
            f"Paper {paper['paper_id']} meets minimum suitability scores"
        )
        return True

    def fetch_human_readable_training_data_for_paper(
        self, paper: sqlite3.Row
    ) -> Optional[Dict[str, Any]]:
        """Fetches a single paper's human-readable training data

        :param paper: Paper record from database
        :type paper: sqlite3.Row
        :return: Paper inference data dictionary if artifacts exist, None otherwise
        :rtype: Optional[Dict[str, Any]]
        """

        try:
            original_content = (
                self.utils.extract_question_chain_of_reasoning_answer_from_artifact(
                    paper, constants.COT_REFINEMENT_ARTIFACT_PATTERN
                )
            )
            voiced_content = (
                self.utils.extract_question_chain_of_reasoning_answer_from_artifact(
                    paper, constants.COT_VOICING_ARTIFACT_PATTERN
                )
            )
            if not original_content or not voiced_content:
                raise ValueError(
                    "Could not retrieve original data or voiced data for paper"
                )
            model_preset = self.extract_model_preset_name(paper)
            orig_q, _, _ = original_content
            _, voiced_c, voiced_a = voiced_content
            return {
                "paper_id": paper["paper_id"],
                "paper_url": paper["paper_url"],
                "model_preset": model_preset,
                "question": orig_q,
                "chain_of_reasoning": voiced_c,
                "answer": voiced_a,
            }
        except Exception as e:
            self.logger.error(
                f"Error retrieving training data for paper {paper['paper_id']}: {e}"
            )
            return None

    def fetch_training_data_for_paper(self, paper: sqlite3.Row) -> Optional[Dict[str, Any]]:
        """Loads a single paper's training data.

        :param paper: Paper record from database
        :type paper: sqlite3.Row
        :return: Training data dictionary if the artifact exists, None otherwise
        :rtype: Optional[Dict[str, Any]]
        """
        try:
            filename = constants.TRAINING_ARTIFACT_PATTERN.format(
                paper_id=paper["paper_id"]
            )
            return self.utils.read_training_artifact(filename)
        except FileNotFoundError:
            self.logger.error(
                f"Training artifact not found for paper {paper['paper_id']}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Error processing training data for paper {paper['paper_id']}: {e}"
            )
            return None

    def _get_human_readable_filename(self, preset: str) -> str:
        """Generate full filename for a specific preset.

        :param preset: Model preset name
        :type preset: str
        :return: Complete filename for the preset's output file
        :rtype: str
        """
        return f"{self.human_readable_stub}-{preset}.md"

    def _clean_existing_human_readable_files(self) -> None:
        """Remove any existing human readable training files."""
        pattern = f"{self.human_readable_stub}-*.md"
        for file in self.training_artifacts_directory.glob(pattern):
            self.logger.debug(f"Removing existing file: {file}")
            file.unlink()

    def _get_or_create_preset_file(self, preset: str) -> TextIO:
        """Get or create file handle for a preset.

        :param preset: Model preset name
        :type preset: str
        :return: File handle for writing
        :rtype: TextIO
        """
        if preset not in self.preset_files:
            filename = self._get_human_readable_filename(preset)
            filepath = self.training_artifacts_directory / filename
            self.preset_files[preset] = open(filepath, 'a')
            self.logger.debug(f"Created new file for preset {preset}: {filepath}")
        return self.preset_files[preset]

    def _close_preset_files(self) -> None:
        """Close all open preset files."""
        for preset, file in self.preset_files.items():
            self.logger.debug(f"Closing file for preset {preset}")
            file.close()
        self.preset_files.clear()

    def initialize_output_files(self) -> Path:
        """Create and initialize the output files for writing training data.

        Creates the output directory if it doesn't exist, removes any existing
        output files, and creates new empty files.

        :return: Path object pointing to the initialized JSONL file
        :rtype: Path
        """
        self.logger.debug(
            f"Initializing output files in {self.training_artifacts_directory}"
        )
        self.utils.ensure_directory_exists(self.training_artifacts_directory)

        jsonl_path = self.training_artifacts_directory / self.jsonl_training_file_name
        self.logger.debug(f"Removing existing JSONL file if present: {jsonl_path}")
        jsonl_path.unlink(missing_ok=True)
        self.logger.debug(f"Creating new empty JSONL file: {jsonl_path}")
        jsonl_path.touch()

        self._clean_existing_human_readable_files()

        return jsonl_path

    def extract_model_preset_name(self, paper: sqlite3.Row) -> str:
        """Extract model preset from the voiced artifact.

        :param paper: Paper record from database
        :type paper: sqlite3.Row
        :return: Model preset string
        :rtype: str
        """
        try:
            filename = constants.COT_VOICING_ARTIFACT_PATTERN.format(
                paper_id=paper["paper_id"]
            )
            headers, _ = self.utils.read_inference_artifact(filename)
            if constants.ARTIFACT_HEADER_KEY_MODEL_PRESET in headers:
                return headers[constants.ARTIFACT_HEADER_KEY_MODEL_PRESET]
            self.logger.warning(
                f"Could not find model preset in voiced artifact for paper {paper['paper_id']}"
            )
        except Exception as e:
            self.logger.warning(
                f"Could not extract model preset for paper {paper['paper_id']}: {e}"
            )
        return "unknown"

    def _format_markdown_entry(self, data: Dict[str, Any]) -> str:
        """Format markdown entry

        :param data: Training data dictionary containing paper info and content
        :type data: Dict[str, Any]
        :return: Formatted markdown entry
        :rtype: str
        """
        return f"""---

### Metadata
- **Paper URL**: {data['paper_url']}

### Question
{data['question']}

### Chain of Reasoning
{data['chain_of_reasoning']}

### Answer
{data['answer']}
"""

    def append_markdown_entry(self, data: Dict[str, Any]) -> None:
        """Append a markdown entry to the appropriate preset file.

        :param data: Training data dictionary containing paper info and content
        :type data: Dict[str, Any]
        """
        preset = data['model_preset']
        preset_file = self._get_or_create_preset_file(preset)
        entry = self._format_markdown_entry(data)
        preset_file.write(entry + "\n")

    def append_training_data(self, output_path: Path, paper: sqlite3.Row, data: Dict[str, Any]) -> None:
        """Append a single training data entry to the JSONL file.

        Converts the training data dictionary to JSON and appends it as a new
        line to the output file.

        :param output_path: Path to the output JSONL file
        :type output_path: Path
        :param paper: Paper record from database
        :type paper: sqlite3.Row
        :param data: Dictionary containing the training data to append
        :type data: Dict[str, Any]
        """
        self.logger.debug(
            f"Appending training data entry for paper {paper['paper_id']} to {output_path}"
        )
        with open(output_path, "a") as f:
            f.write(json.dumps(data) + "\n")

    def process_papers(self, jsonl_path: Path) -> Tuple[int, int]:
        """Process all papers and return counts.

        Iterates through qualified papers, processes their training data, and
        writes successful results to the output file. Tracks and reports progress
        periodically.

        :param output_path: Path to the output file where training data will be written
        :type output_path: Path
        :return: Tuple containing counts of processed and skipped papers
        :rtype: Tuple[int, int]
        """
        processed_count = 0
        skipped_count = 0

        for paper in self.fetch_qualified_papers():
            self.logger.debug(f"Processing paper {paper['paper_id']}")
            if not self.paper_qualifies_for_training_data(paper):
                skipped_count += 1
                continue
            training_data = self.fetch_training_data_for_paper(paper)
            human_data = self.fetch_human_readable_training_data_for_paper(paper)
            if training_data:
                self.append_training_data(jsonl_path, paper, training_data)
                if human_data:
                    self.append_markdown_entry(human_data)
                processed_count += 1
                self.logger.info(f"Successfully processed paper {paper['paper_id']}")
            else:
                skipped_count += 1
                self.logger.debug(f"Skipped paper {paper['paper_id']}")
            if (
                processed_count % self.PROGRESS_REPORT_INTERVAL == 0
                and processed_count > 0
            ):
                total = processed_count + skipped_count
                percentage = (processed_count / total * 100) if total > 0 else 0
                self.logger.info(
                    f"Generated {processed_count} training examples ({percentage:.1f}% of total processed)"
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
            f"Minimum CoT quaility score: {self.cot_quality_assessment_suitability_score}, "
            f"Minimum CoT voicing score: {self.cot_voicing_assessment_suitability_score}, "
            f"Limit: {self.limit}"
        )

        try:
            jsonl_path = self.initialize_output_files()
            self.logger.info(f"JSONL output file: {jsonl_path}")
            processed_count, skipped_count = self.process_papers(jsonl_path)

            if processed_count > 0:
                self.logger.info(
                    f"Training data generation completed. "
                    f"Processed: {processed_count}, "
                    f"Skipped: {skipped_count}, "
                    f"JSONL output: {jsonl_path}"
                )
            else:
                self.logger.warning("No training data was generated")

        except Exception as e:
            self.logger.error(f"An error occurred during training data generation: {e}")
            sys.exit(1)
        finally:
            self._close_preset_files()


def main():
    """Main entry point for CLI usage.

    Parses command line arguments and runs the training data generation process.

    :raises SystemExit: With code 1 if an unrecoverable error occurs
    :raises ArgumentError: If invalid command line arguments are provided
    """
    args = parse_arguments()
    generator = TrainingDataGenerator(
        database=args.database,
        cot_quality_assessment_suitability_score=args.cot_quality_assessment_suitability_score,
        cot_voicing_assessment_suitability_score=args.cot_voicing_assessment_suitability_score,
        jsonl_training_file_name=args.jsonl_training_file_name,
        human_readable_stub=args.human_readable_training_stub,
        training_artifacts_directory=args.training_artifacts_directory,
        limit=args.limit,
        debug=args.debug,
    )
    generator.run()


if __name__ == "__main__":
    main()
