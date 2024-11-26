#!/usr/bin/env python3

"""
Quality assessment module for Chain of Thought (CoT) extractions from research papers.

This module evaluates Chain of Thought extractions from research papers against defined
quality criteria. It manages the complete assessment workflow including paper loading,
criteria evaluation, and report generation.

The module implements a systematic assessment process that:
1. Loads papers with completed CoT extractions from database
2. Executes LWE templates for criteria evaluation
3. Parses assessment results and updates paper status
4. Generates detailed assessment artifacts for tracking

Assessment criteria evaluated:
- Source fidelity: Accuracy of extracted information
- Reasoning integrity: Logical coherence of chain of thought
- Training utility: Value for training purposes
- Structural quality: Format and completeness of extraction
"""

import argparse
import copy
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple
import sqlite3
import sys
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments for the CoT quality assessment process.

    Configures and processes command line arguments for controlling the assessment
    workflow. Sets up required paths, processing limits, and execution parameters.

    :param: None
    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Assess Chain of Thought extractions from papers."
    )
    parser.add_argument(
        "--assessor-preset",
        type=str,
        default=constants.DEFAULT_COT_QUALITY_ASSESSOR_PRESET,
        help="Model configuration used for assessment, default: %(default)s",
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
        "--template",
        type=str,
        default=constants.DEFAULT_COT_QUALITY_ASSESSOR_TEMPLATE,
        help="LWE assessment template name, default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class CoTQualityAssessor:
    """Handles quality assessment of Chain of Thought (CoT) extractions from research papers.

    This class implements the core functionality for evaluating CoT extractions against
    defined quality criteria. It manages the assessment workflow including loading papers,
    running evaluations, and generating assessment artifacts.

    Attributes:
        assessor_preset (str): Model configuration used for assessment
        database (str): Path to the SQLite database
        inference_artifacts_directory (str): Directory for storing assessment artifacts
        limit (Optional[int]): Maximum number of papers to process
        template (str): Name of the LWE assessment template
        debug (bool): Debug logging flag
        logger (logging.Logger): Configured logger instance
        utils (Utils): Utility instance for common operations
    """

    def __init__(
        self,
        limit: Optional[int] = 1,
        debug: bool = False,
        assessor_preset: str = constants.DEFAULT_COT_QUALITY_ASSESSOR_PRESET,
        database: str = constants.DEFAULT_DB_NAME,
        inference_artifacts_directory: str = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        template: str = constants.DEFAULT_COT_QUALITY_ASSESSOR_TEMPLATE,
    ) -> None:
        """
        Initialize the CoTQualityAssessor with configuration parameters.

        Sets up the assessor instance with provided configuration parameters and
        initializes required utilities and logging.

        :param limit: Maximum number of papers to process
        :type limit: Optional[int]
        :param debug: Enable debug logging
        :type debug: bool
        :param assessor_preset: Model configuration for assessment
        :type assessor_preset: str
        :param database: Path to SQLite database
        :type database: str
        :param inference_artifacts_directory: Directory for storing assessment artifacts
        :type inference_artifacts_directory: str
        :param template: LWE assessment template name
        :type template: str
        :return: None
        :rtype: None
        """
        self.assessor_preset = assessor_preset
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.limit = limit
        self.template = template
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(
            database=self.database,
            inference_artifacts_directory=self.inference_artifacts_directory,
            lwe_default_preset=self.assessor_preset,
            logger=self.logger,
        )
        self.utils.setup_lwe()

    def parse_xml(self, xml_string: str) -> Dict[str, int]:
        """Parse assessment criteria values from XML response string.

        Extracts boolean values for each defined assessment criterion from the XML
        structure. Validates presence of all required criteria and converts text
        responses to binary values.

        :param xml_string: XML formatted assessment response
        :type xml_string: str
        :return: Dictionary mapping criteria names to binary values (0 or 1)
        :rtype: Dict[str, int]
        :raises ValueError: If any required criterion is missing from XML
        """
        root = ET.fromstring(xml_string)
        criteria = {}
        for criterion in constants.COT_QUALITY_ASSESSMENT_CRITERIA:
            element = root.find(f".//{criterion}")
            if element is not None:
                value = element.text.strip()
                criteria[f"cot_quality_assessment_criteria_{criterion}"] = (
                    1 if value.lower() in ["yes", "y"] else 0
                )
            else:
                raise ValueError(f"{criterion} not found in XML")
        return criteria

    def get_pretty_printed_criteria(self, criteria: Dict[str, int]) -> str:
        """
        Format assessment criteria and values into a human-readable string.

        Converts the criteria dictionary into a formatted multi-line string where each
        criterion is displayed with its corresponding Yes/No value.

        :param criteria: Dictionary mapping criteria names to binary values (0 or 1)
        :type criteria: Dict[str, int]
        :return: Formatted string with one criterion per line
        :rtype: str
        """
        output = []
        for criterion in constants.COT_QUALITY_ASSESSMENT_CRITERIA:
            answer = (
                "Yes"
                if criteria[f"cot_quality_assessment_criteria_{criterion}"] == 1
                else "No"
            )
            output.append(f"  {criterion}: {answer}")
        return "\n".join(output)

    def write_assessment_artifact(
        self, paper: sqlite3.Row, criteria: Dict[str, int], xml_content: str
    ) -> None:
        """
        Write assessment results and metadata to an artifact file.

        Creates a formatted artifact file containing paper metadata, assessment results,
        and raw inference output for archival and debugging purposes.

        :param paper: Database row containing paper metadata (paper_id, paper_url)
        :type paper: sqlite3.Row
        :param criteria: Dictionary of assessment criteria results
        :type criteria: Dict[str, int]
        :param xml_content: Raw XML output from the assessment
        :type xml_content: str
        :return: None
        :rtype: None
        """
        artifact_name = constants.COT_QUALITY_ASSESSMENT_ARTIFACT_PATTERN.format(
            paper_id=paper["paper_id"]
        )
        content = f"""Paper URL: {paper['paper_url']}
CoT assessment preset: {self.assessor_preset}

CoT assessment results:

{self.get_pretty_printed_criteria(criteria)}

----------------------

Raw Inference Output:

{xml_content}
"""
        self.utils.write_inference_artifact(artifact_name, content)

    def check_required_criteria(self, criteria: Dict[str, int]) -> bool:
        """
        Verify that all required quality assessment criteria are satisfied.

        Checks each required criterion defined in REQUIRED_COT_QUALITY_ASSESSMENT_CRITERIA
        against the provided criteria values to ensure they meet minimum quality standards.

        :param criteria: Dictionary mapping criteria names to binary values (0 or 1)
        :type criteria: Dict[str, int]
        :return: True if all required criteria are met, False otherwise
        :rtype: bool
        """
        for criterion in constants.REQUIRED_COT_QUALITY_ASSESSMENT_CRITERIA:
            if criteria[f"cot_quality_assessment_criteria_{criterion}"] != 1:
                return False
        return True

    def run_assessment(
        self, paper_content: str, question: str, chain_of_reasoning: str, answer: str
    ) -> Tuple[Dict[str, int], str]:
        """
        Execute quality assessment template and process the results.

        Runs the LWE template with provided paper content and CoT components,
        then processes the response to extract assessment criteria results.

        :param paper_content: Full text content of the research paper
        :type paper_content: str
        :param question: Extracted research question
        :type question: str
        :param chain_of_reasoning: Extracted reasoning chain
        :type chain_of_reasoning: str
        :param answer: Extracted answer/conclusion
        :type answer: str
        :return: Tuple containing (criteria dictionary, raw XML response)
        :rtype: Tuple[Dict[str, int], str]
        :raises ValueError: If XML content cannot be extracted from response
        """
        lwe_response = self.utils.run_lwe_template(
            self.template,
            {
                "paper": paper_content,
                "question": question,
                "chain_of_reasoning": chain_of_reasoning,
                "answer": answer,
            },
        )
        xml_content = self.utils.extract_xml(lwe_response)
        if not xml_content:
            raise ValueError("Could not extract XML content from LWE response")

        criteria = self.parse_xml(xml_content)
        return criteria, xml_content

    def update_assessment_results(
        self, paper_id: str, criteria: Dict[str, int]
    ) -> None:
        """
        Update paper record with quality assessment results.

        Stores the assessment criteria results and updates the paper's processing
        status in the database.

        :param paper_id: Database ID of the paper
        :type paper_id: str
        :param criteria: Dictionary mapping criteria names to assessment results
        :type criteria: Dict[str, int]
        :return: None
        :rtype: None
        """
        data = copy.deepcopy(criteria)
        data["processing_status"] = constants.STATUS_COT_QUALITY_ASSESSED
        self.utils.update_paper(paper_id, data)

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Execute quality assessment workflow for a single paper.

        Processes an individual paper through the complete assessment pipeline:
        1. Extracts text content from PDF
        2. Retrieves refinement data
        3. Runs quality assessment
        4. Generates assessment artifact
        5. Updates paper status

        :param paper: Database row containing paper metadata (id, paper_id, paper_url)
        :type paper: sqlite3.Row
        :return: None
        :rtype: None
        """
        self.logger.info(
            f"Asssssing paper {paper['paper_id']}"
        )
        try:
            text = self.utils.get_pdf_text(paper)
            refinement_data = self.utils.extract_question_chain_of_reasoning_answer_from_artifact(paper, constants.COT_REFINEMENT_ARTIFACT_PATTERN)
            if not refinement_data:
                raise ValueError(
                    "Could not retrieve refinement data for paper"
                )

            question, chain_of_reasoning, answer = refinement_data
            criteria, xml_content = self.run_assessment(
                text, question, chain_of_reasoning, answer
            )
            self.write_assessment_artifact(paper, criteria, xml_content)
            self.update_assessment_results(paper["id"], criteria)
            self.logger.info(
                f"Successfully assessed paper {paper['paper_id']} - Status: {constants.STATUS_COT_QUALITY_ASSESSED}"
            )

        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_QUALITY_ASSESSMENT
            )

    def run(self) -> None:
        """Execute the main Chain of Thought quality assessment workflow.

        Orchestrates the complete assessment process:
            1. Fetches papers with STATUS_COT_EXTRACTED status
            2. Processes each paper through quality assessment
            3. Updates paper status and stores assessment results
            4. Generates assessment artifacts
        """
        try:
            papers = self.utils.fetch_papers_by_processing_status(
                status=constants.STATUS_COT_EXTRACTED,
                limit=self.limit,
            )
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("CoT quality assessment process completed")
        except Exception as e:
            self.logger.error(
                f"An error occurred during the CoT quality assessment process: {e}"
            )
            sys.exit(1)


def main() -> None:
    """
    Main entry point for the CoT quality assessment CLI.

    Parses command line arguments and initializes the assessment process.
    Handles the complete workflow from paper loading through assessment.

    :return: None
    :rtype: None
    """
    args = parse_arguments()
    assessor = CoTQualityAssessor(
        limit=args.limit,
        debug=args.debug,
        assessor_preset=args.assessor_preset,
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        template=args.template,
    )
    assessor.run()


if __name__ == "__main__":
    main()
