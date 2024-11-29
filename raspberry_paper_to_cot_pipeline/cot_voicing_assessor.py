#!/usr/bin/env python3

"""
Voice assessment module for Chain of Thought (CoT) transformations.

This module evaluates voice-transformed Chain of Thought content against defined
criteria to ensure proper first-person transformation while maintaining content
accuracy. It manages the complete assessment workflow including:
1. Loading papers with completed voice transformations
2. Comparing against original refined content
3. Evaluating voice requirements and content preservation
4. Generating detailed assessment artifacts

Assessment criteria evaluated:
- Content preservation: Structural integrity and information fidelity
- Factual accuracy: Grounding in paper and academic integrity
- Voice requirements: First-person narrative, removal of source references
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
    Parse and validate command-line arguments for the voice assessment process.

    Configures and processes command line arguments for controlling the assessment
    workflow. Sets up required paths, processing limits, and execution parameters.

    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Assess voice transformation of Chain of Thought content."
    )
    parser.add_argument(
        "--assessor-preset",
        type=str,
        default=constants.DEFAULT_COT_VOICING_ASSESSOR_PRESET,
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
        default=constants.DEFAULT_COT_VOICING_ASSESSOR_TEMPLATE,
        help="LWE assessment template name, default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class CoTVoicingAssessor:
    """Handles voice assessment of Chain of Thought (CoT) transformations.

    This class implements the core functionality for evaluating voice-transformed
    CoT content against defined criteria. It manages the assessment workflow including
    loading papers, running evaluations, and generating assessment artifacts.
    """

    def __init__(
        self,
        limit: Optional[int] = 1,
        assessor_preset: str = constants.DEFAULT_COT_VOICING_ASSESSOR_PRESET,
        database: str = constants.DEFAULT_DB_NAME,
        inference_artifacts_directory: str = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        template: str = constants.DEFAULT_COT_VOICING_ASSESSOR_TEMPLATE,
        debug: bool = False,
    ) -> None:
        """
        Initialize the CoTVoicingAssessor with configuration parameters.

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
        """
        self.limit = limit
        self.assessor_preset = assessor_preset
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
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

        Extracts boolean values for each defined voice assessment criterion from
        the XML structure.

        :param xml_string: XML formatted assessment response
        :type xml_string: str
        :return: Dictionary mapping criteria names to binary values (0 or 1)
        :rtype: Dict[str, int]
        :raises ValueError: If any required criterion is missing from XML
        """
        root = ET.fromstring(xml_string)
        criteria = {}
        for criterion in constants.COT_VOICING_ASSESSMENT_CRITERIA:
            element = root.find(f".//{criterion}")
            if element is not None:
                value = self.utils.clean_extracted_text(element.text)
                criteria[f"cot_voicing_assessment_{criterion}"] = (
                    1 if value.lower() in ["yes", "y"] else 0
                )
            else:
                raise ValueError(f"{criterion} not found in XML")
        return criteria

    def get_pretty_printed_criteria(self, criteria: Dict[str, int]) -> str:
        """
        Format assessment criteria and values into a human-readable string.

        :param criteria: Dictionary mapping criteria names to binary values (0 or 1)
        :type criteria: Dict[str, int]
        :return: Formatted string with one criterion per line
        :rtype: str
        """
        output = []
        for criterion in constants.COT_VOICING_ASSESSMENT_CRITERIA:
            answer = (
                "Yes" if criteria[f"cot_voicing_assessment_{criterion}"] == 1 else "No"
            )
            output.append(f"  {criterion}: {answer}")
        return "\n".join(output)

    def write_assessment_artifact(
        self, paper: sqlite3.Row, criteria: Dict[str, int], xml_content: str
    ) -> None:
        """
        Write assessment results and metadata to an artifact file.

        :param paper: Database row containing paper metadata
        :type paper: sqlite3.Row
        :param criteria: Dictionary of assessment criteria results
        :type criteria: Dict[str, int]
        :param xml_content: Raw XML output from the assessment
        :type xml_content: str
        """
        artifact_name = constants.COT_VOICING_ASSESMENT_ARTIFACT_PATTERN.format(
            paper_id=paper["paper_id"]
        )
        headers = {
            constants.ARTIFACT_HEADER_KEY_PAPER_URL: paper["paper_url"],
            constants.ARTIFACT_HEADER_KEY_MODEL_PRESET: self.assessor_preset,
        }
        content = f"""CoT voicing assessment results:

{self.get_pretty_printed_criteria(criteria)}

----------------------

Raw Inference Output:

{xml_content}
"""
        self.utils.write_inference_artifact(artifact_name, headers, content)

    def run_assessment(
        self,
        paper_content: str,
        original_content: Tuple[str, str, str],
        voiced_content: Tuple[str, str, str],
    ) -> Tuple[Dict[str, int], str]:
        """
        Execute voice assessment template and process the results.

        :param paper_content: Full text content of the research paper
        :type paper_content: str
        :param original_content: Original (question, chain_of_reasoning, answer)
        :type original_content: Tuple[str, str, str]
        :param voiced_content: Voiced (question, chain_of_reasoning, answer)
        :type voiced_content: Tuple[str, str, str]
        :return: Tuple containing (criteria dictionary, raw XML response)
        :rtype: Tuple[Dict[str, int], str]
        """
        orig_q, orig_c, orig_a = original_content
        _, voiced_c, voiced_a = voiced_content

        lwe_response = self.utils.run_lwe_template(
            self.template,
            {
                "paper": paper_content,
                "original_question": orig_q,
                "original_chain_of_reasoning": orig_c,
                "original_answer": orig_a,
                "question": orig_q,
                "chain_of_reasoning": voiced_c,
                "answer": voiced_a,
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
        Update paper record with voice assessment results.

        :param paper_id: Database ID of the paper
        :type paper_id: str
        :param criteria: Dictionary mapping criteria names to assessment results
        :type criteria: Dict[str, int]
        """
        data = copy.deepcopy(criteria)
        data["processing_status"] = constants.STATUS_COT_VOICING_ASSESSED
        self.utils.update_paper(paper_id, data)

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Execute voice assessment workflow for a single paper.

        :param paper: Database row containing paper metadata
        :type paper: sqlite3.Row
        """
        self.logger.info(f"Asssssing paper {paper['paper_id']}")
        try:
            text = self.utils.get_pdf_text(paper)
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

            criteria, xml_content = self.run_assessment(
                text, original_content, voiced_content
            )
            self.write_assessment_artifact(paper, criteria, xml_content)
            self.update_assessment_results(paper["id"], criteria)
            self.logger.info(
                f"Successfully assessed paper {paper['paper_id']} - Status: {constants.STATUS_COT_VOICING_ASSESSED}"
            )

        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_VOICING_ASSESSMENT
            )

    def run(self) -> None:
        """Execute the main Chain of Thought voice assessment workflow.

        Orchestrates the complete assessment process:
            1. Fetches papers with completed voice transformations
            2. Processes each paper through voice assessment
            3. Updates paper status and stores assessment results
            4. Generates assessment artifacts
        """
        try:
            papers = self.utils.fetch_papers_by_processing_status(
                status=constants.STATUS_COT_VOICED,
                limit=self.limit,
            )
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("CoT voice assessment process completed")
        except Exception as e:
            self.logger.error(
                f"An error occurred during the CoT voice assessment process: {e}"
            )
            sys.exit(1)


def main() -> None:
    """
    Main entry point for the CoT voice assessment CLI.

    Parses command line arguments and initializes the assessment process.
    """
    args = parse_arguments()
    assessor = CoTVoicingAssessor(
        limit=args.limit,
        assessor_preset=args.assessor_preset,
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        template=args.template,
        debug=args.debug,
    )
    assessor.run()


if __name__ == "__main__":
    main()
