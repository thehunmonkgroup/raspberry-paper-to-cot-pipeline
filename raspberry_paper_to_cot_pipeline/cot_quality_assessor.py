#!/usr/bin/env python3

"""
This script assesses the quality of Chain of Thought (CoT) extractions from research papers.

It processes papers that have completed CoT extraction and evaluates them against a set of
criteria including source fidelity, reasoning integrity, training utility, and structural
quality.

The assessment process involves:
1. Loading papers with completed CoT extractions
2. Running LWE templates to evaluate against the assessment criteria
3. Parsing results and updating paper status in the database
4. Generating assessment artifacts for tracking
"""

import argparse
import copy
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple
import sys
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
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
    """
    A class to handle quality assessment of Chain of Thought extractions.
    """

    def __init__(
        self,
        limit: Optional[int],
        debug: bool = False,
        assessor_preset: str = constants.DEFAULT_COT_QUALITY_ASSESSOR_PRESET,
        database: str = constants.DEFAULT_DB_NAME,
        inference_artifacts_directory: str = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        template: str = constants.DEFAULT_COT_QUALITY_ASSESSOR_TEMPLATE,
    ):
        """
        Initialize the CoTQualityAssessor with individual arguments.

        :param assessor_preset: Model configuration used for assessment
        :param database: Path to the SQLite database
        :param inference_artifacts_directory: Directory for inference artifacts
        :param limit: Number of papers to process
        :param template: LWE assessment template name
        :param debug: Enable debug logging
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
        """
        Parse the XML string to extract assessment criteria values.

        :param xml_string: XML string to parse
        :return: Dictionary of criteria and their values
        :raises ValueError: If a required criterion is not found in the XML
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
        Get a pretty-printed string of assessment criteria and their values.

        :param criteria: Dictionary of criteria and their values
        :return: Pretty-printed string of criteria and values
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
        self, paper: Dict[str, Any], criteria: Dict[str, int], xml_content: str
    ) -> None:
        """
        Write assessment results to an artifact file.

        :param paper: Paper data
        :param criteria: Dictionary of criteria and their values
        :param xml_content: Raw XML content
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
        Check if all required assessment criteria are met.

        :param criteria: Dictionary of criteria and their values
        :return: True if all required criteria are met, False otherwise
        """
        for criterion in constants.REQUIRED_COT_QUALITY_ASSESSMENT_CRITERIA:
            if criteria[f"cot_quality_assessment_criteria_{criterion}"] != 1:
                return False
        return True

    def get_refinement_data(
        self, paper: Dict[str, Any]
    ) -> Optional[Tuple[str, str, str]]:
        """
        Get question, chain of reasoning, and answer from refinement artifact.

        :param paper: Paper data dictionary
        :return: Tuple of (question, chain_of_reasoning, answer) or None if retrieval fails
        """
        try:
            artifact_name = constants.COT_REFINEMENT_ARTIFACT_PATTERN.format(
                paper_id=paper["paper_id"]
            )
            refinement_content = self.utils.read_inference_artifact(artifact_name)
            return self.utils.extract_question_chain_of_reasoning_answer(
                refinement_content
            )
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(
                f"Failed to get refinement data for paper {paper['paper_id']}: {str(e)}"
            )
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_QUALITY_ASSESSMENT
            )
            return None

    def run_assessment(
        self, paper_content: str, question: str, chain_of_reasoning: str, answer: str
    ) -> Tuple[Dict[str, int], str]:
        """
        Run assessment template and process results.

        :param paper_content: Text content of the paper
        :param question: Question to verify
        :param chain_of_reasoning: Chain of reasoning to verify
        :param answer: Answer to verify
        :return: Tuple of (criteria dict, xml content)
        :raises ValueError: If XML content cannot be extracted
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
        Update paper with assessment results.

        :param paper_id: ID of the paper
        :param criteria: Dictionary of assessment criteria results
        """
        data = copy.deepcopy(criteria)
        data["processing_status"] = constants.STATUS_COT_QUALITY_ASSESSED
        self.utils.update_paper(paper_id, data)

    def process_paper(self, paper: Dict[str, Any]) -> None:
        """
        Process a single paper through the assessment pipeline.

        :param paper: Paper data dictionary containing id, paper_id, and paper_url
        """
        try:
            text = self.utils.get_pdf_text(paper)
            refinement_data = self.get_refinement_data(paper)
            if not refinement_data:
                return

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
        """Execute the main logic of the CoT quality assessment process."""
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


def main():
    """Main entry point for CLI usage."""
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