#!/usr/bin/env python3

"""Script for profiling research papers for Chain of Thought (CoT) extraction suitability.

This module implements a paper profiling system that evaluates research papers against
predefined criteria to determine their suitability for Chain of Thought extraction.
The system handles the complete profiling workflow including paper fetching, content
extraction, evaluation, and results storage.

The profiling process involves:
1. Fetching unprocessed papers from a SQLite database
2. Downloading and extracting text from PDF files
3. Running LWE templates to evaluate papers against profiling criteria
4. Parsing results and updating paper status in the database
5. Generating inference artifacts for successful profiles
"""

import argparse
import copy
import sqlite3
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Generator, Literal
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments for the paper profiler.

    :return: Namespace containing parsed command-line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Profile papers based on a set of rubric questions."
    )
    parser.add_argument(
        "--profiling-preset",
        type=str,
        default=constants.DEFAULT_PAPER_PROFILER_PRESET,
        help="Model configuration used to perform the profiling, default: %(default)s",
    )
    parser.add_argument(
        "--database",
        type=str,
        default=constants.DEFAULT_DB_NAME,
        help="Path to the SQLite database, default: %(default)s",
    )
    parser.add_argument(
        "--inference-artifacts-directory",
        type=str,
        default=constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        help="Directory for inference artifacts, default: %(default)s",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of papers to process, default: %(default)s",
    )
    parser.add_argument(
        "--selection-strategy",
        type=str,
        choices=["random", "category_balanced"],
        default="random",
        help="Strategy for paper selection: 'random' or 'category_balanced', default: %(default)s",
    )
    parser.add_argument(
        "--pdf-cache-dir",
        type=str,
        default=constants.DEFAULT_PDF_CACHE_DIR,
        help="PDF cache directory, default: %(default)s",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=constants.DEFAULT_PAPER_PROFILER_TEMPLATE,
        help="LWE paper profiler template name, default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperProfiler:
    """Handle paper profiling based on predefined rubric questions.

    This class manages the complete paper profiling workflow, including paper selection,
    content extraction, criteria evaluation, and results storage. It supports different
    paper selection strategies and configurable processing parameters.
    """

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        profiling_preset: str = constants.DEFAULT_PAPER_PROFILER_PRESET,
        database: str = constants.DEFAULT_DB_NAME,
        inference_artifacts_directory: str = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        selection_strategy: Literal["random", "category_balanced"] = "random",
        pdf_cache_dir: str = constants.DEFAULT_PDF_CACHE_DIR,
        template: str = constants.DEFAULT_PAPER_PROFILER_TEMPLATE,
    ):
        """Initialize the PaperProfiler with configuration parameters.

        :param profiling_preset: Model configuration used for profiling
        :type profiling_preset: str
        :param database: Path to the SQLite database
        :type database: str
        :param inference_artifacts_directory: Directory for storing inference artifacts
        :type inference_artifacts_directory: str
        :param limit: Maximum number of papers to process
        :type limit: Optional[int]
        :param selection_strategy: Strategy for paper selection
        :type selection_strategy: str
        :param pdf_cache_dir: Directory for caching PDF files
        :type pdf_cache_dir: str
        :param template: LWE paper profiler template name
        :type template: str
        :param debug: Enable debug logging
        :type debug: bool
        :raises ValueError: If category_balanced strategy is used without valid limit
        """
        self.profiling_preset = profiling_preset
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.limit = limit
        self.selection_strategy = selection_strategy
        if selection_strategy == "category_balanced" and (not limit or limit < 1):
            raise ValueError(
                "category_balanced strategy requires a positive limit value"
            )
        self.pdf_cache_dir = pdf_cache_dir
        self.template = template
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(
            database=self.database,
            inference_artifacts_directory=self.inference_artifacts_directory,
            pdf_cache_dir=self.pdf_cache_dir,
            lwe_default_preset=self.profiling_preset,
            logger=self.logger,
        )
        self.utils.setup_lwe()

    def run_lwe_template(self, paper_content: str) -> str:
        """Execute the LWE template against paper content.

        :param paper_content: Extracted text content of the paper
        :type paper_content: str
        :return: Template execution response
        :rtype: str
        :raises RuntimeError: If LWE template execution fails
        """
        self.logger.debug(f"Running LWE template '{self.template}'")
        template_vars = {"paper": paper_content}
        return self.utils.run_lwe_template(self.template, template_vars)

    def parse_xml(self, xml_string: str) -> Dict[str, int]:
        """Parse XML response to extract profiling criteria values.

        :param xml_string: XML response string to parse
        :type xml_string: str
        :return: Dictionary mapping criteria names to their boolean values (0 or 1)
        :rtype: Dict[str, int]
        :raises ValueError: If a required question is missing from the XML or XML is invalid
        """
        self.logger.debug("Starting XML parsing")
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse XML: {e}")
            raise ValueError(f"Invalid XML format: {e}")

        criteria = {}
        for question in constants.PAPER_PROFILING_CRITERIA:
            element = root.find(f".//{question}")
            if element is not None:
                value = element.text.strip()
                criteria[f"profiler_criteria_{question}"] = (
                    1 if value.lower() in ["yes", "y"] else 0
                )
            else:
                raise ValueError(f"{question} not found in XML")

        self.logger.debug("XML parsing completed successfully")
        return criteria

    def get_pretty_printed_rubric_questions(self, criteria: Dict[str, int]) -> str:
        """Format rubric questions and answers for human-readable output.

        :param criteria: Dictionary of criteria and their values
        :type criteria: Dict[str, int]
        :return: Formatted string of questions and Yes/No answers
        :rtype: str
        :raises KeyError: If a required criteria key is missing
        """
        self.logger.debug("Formatting rubric questions and answers")
        output = []
        try:
            for question in constants.PAPER_PROFILING_CRITERIA:
                key = f"profiler_criteria_{question}"
                if key not in criteria:
                    self.logger.error(f"Missing criteria key: {key}")
                    raise KeyError(f"Missing criteria key: {key}")
                answer = "Yes" if criteria[key] == 1 else "No"
                output.append(f"  {question}: {answer}")
                self.logger.debug(f"Processed question: {question} = {answer}")

            result = "\n".join(output)
            self.logger.debug("Successfully formatted all questions")
            return result
        except Exception as e:
            self.logger.error(f"Error formatting rubric questions: {e}")
            raise

    def write_inference_artifact(
        self, paper: sqlite3.Row, criteria: Dict[str, int], xml_content: str
    ) -> None:
        """Write profiling results and metadata to an inference artifact file.

        :param paper: Paper metadata and content
        :type paper: sqlite3.Row
        :param criteria: Dictionary of evaluated criteria values
        :type criteria: Dict[str, int]
        :param xml_content: Raw XML response content
        :type xml_content: str
        :raises KeyError: If required paper fields are missing
        """
        self.logger.debug(f"Writing inference artifact for paper {paper['paper_id']}")
        artifact_name = f"{paper['paper_id']}-paper-profiling.txt"

        content = f"""Paper URL: {paper['paper_url']}
Profiling preset: {self.profiling_preset}

Profiling results:

{self.get_pretty_printed_rubric_questions(criteria)}

----------------------

Raw Inference Output:

{xml_content}
"""
        self.utils.write_inference_artifact(artifact_name, content)
        self.logger.debug(f"Successfully wrote inference artifact: {artifact_name}")

    def _extract_and_validate_content(self, paper: sqlite3.Row) -> tuple[str, str, str]:
        """Extract and validate paper content through the processing pipeline.

        :param paper: Paper data from database
        :type paper: sqlite3.Row
        :return: Tuple containing (text content, LWE response, XML content)
        :rtype: tuple[str, str, str]
        :raises ValueError: If XML content cannot be extracted from response
        :raises RuntimeError: If LWE template execution fails
        """
        text = self.utils.get_pdf_text(paper)
        lwe_response = self.run_lwe_template(text)
        xml_content = self.utils.extract_xml(lwe_response)
        if not xml_content:
            raise ValueError("Could not extract XML content from LWE response")
        return text, lwe_response, xml_content

    def _process_criteria_and_update(
        self, paper: sqlite3.Row, xml_content: str
    ) -> None:
        """Process evaluation criteria and update paper status in database.

        :param paper: Paper data from database
        :type paper: sqlite3.Row
        :param xml_content: Extracted XML response content
        :type xml_content: str
        """
        criteria = self.parse_xml(xml_content)
        self.write_inference_artifact(paper, criteria, xml_content)
        data = copy.deepcopy(criteria)
        data["processing_status"] = constants.STATUS_PAPER_PROFILED
        self.utils.update_paper(paper["id"], data)

    def process_paper(self, paper: sqlite3.Row) -> None:
        """Process a single paper through the complete profiling pipeline.

        :param paper: Paper data containing id, paper_id, and paper_url
        :type paper: sqlite3.Row
        :raises ValueError: If XML content cannot be extracted from LWE response
        :raises RuntimeError: If LWE template execution fails
        :raises Exception: If paper processing fails for any other reason
        """
        try:
            _, _, xml_content = self._extract_and_validate_content(paper)
            self._process_criteria_and_update(paper, xml_content)
            self.logger.info(f"Successfully profiled paper {paper['paper_id']}")
        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(paper["id"], "failed_profiling")

    def fetch_papers(self) -> Generator[sqlite3.Row, None, None]:
        """Fetch unprocessed papers using configured selection strategy.

        :return: Generator yielding paper records from database
        :rtype: Generator[sqlite3.Row, None, None]
        """
        if self.selection_strategy == "random":
            return self.utils.fetch_papers_by_processing_status(
                status=constants.STATUS_PAPER_LINK_DOWNLOADED, limit=self.limit
            )
        else:  # category_balanced
            return self.utils.fetch_papers_by_processing_status_balanced_by_category(
                status=constants.STATUS_PAPER_LINK_DOWNLOADED, limit=self.limit
            )

    def run(self) -> None:
        """Execute the main paper profiling workflow.

        :raises SystemExit: If a critical error occurs during processing
        """
        try:
            papers = self.fetch_papers()
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("Paper profiling process completed")
        except Exception as e:
            self.logger.error(
                f"An error occurred during the paper profiling process: {e}"
            )
            raise


def main():
    """Main entry point for command-line interface.

    :raises SystemExit: If processing encounters a critical error
    """
    args = parse_arguments()
    profiler = PaperProfiler(
        limit=args.limit,
        debug=args.debug,
        profiling_preset=args.profiling_preset,
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        selection_strategy=args.selection_strategy,
        pdf_cache_dir=args.pdf_cache_dir,
        template=args.template,
    )
    profiler.run()


if __name__ == "__main__":
    main()
