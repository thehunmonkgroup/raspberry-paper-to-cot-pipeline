#!/usr/bin/env python3

"""
Voice transformation module for Chain of Thought (CoT) extractions from research papers.

This module transforms quality-assessed Chain of Thought extractions into a consistent
first-person narrative voice while maintaining factual accuracy. It manages the complete
transformation workflow including:
1. Loading quality-assessed papers from database
2. Executing LWE templates for voice transformation
3. Validating transformed content
4. Generating transformation artifacts
"""

import argparse
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
import sqlite3
import sys
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments for the CoT voice transformation process.

    Configures and processes command line arguments for controlling the voice
    transformation workflow. Sets up required paths and execution parameters.

    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Transform Chain of Thought extractions into first-person narrative."
    )
    parser.add_argument(
        "--voicing-preset",
        type=str,
        default=constants.DEFAULT_COT_VOICING_PRESET,
        help="Model configuration used for voice transformation, default: %(default)s",
    )
    parser.add_argument(
        "--suitability-score",
        type=int,
        default=constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        help="Minimum suitability score required. Default: %(default)s",
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
        default=constants.DEFAULT_COT_VOICING_TEMPLATE,
        help="LWE voice transformation template name, default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class CoTVoicing:
    """Handles voice transformation of Chain of Thought (CoT) extractions.

    This class implements the core functionality for transforming CoT extractions into
    a consistent first-person narrative voice. It manages the transformation workflow
    including loading papers, running transformations, and generating artifacts.
    """

    def __init__(
        self,
        limit: Optional[int] = 1,
        voicing_preset: str = constants.DEFAULT_COT_VOICING_PRESET,
        database: str = constants.DEFAULT_DB_NAME,
        suitability_score: int = constants.COT_QUALITY_ASSESSMENT_DEFAULT_SUITABILITY_SCORE,
        inference_artifacts_directory: str = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        template: str = constants.DEFAULT_COT_VOICING_TEMPLATE,
        debug: bool = False,
    ) -> None:
        """
        Initialize the CoTVoicer with configuration parameters.

        Sets up the voicer instance with provided configuration parameters and
        initializes required utilities and logging.

        :param limit: Maximum number of papers to process
        :type limit: Optional[int]
        :param voicing_preset: Model configuration for transformation
        :type voicing_preset: str
        :param database: Path to SQLite database
        :type database: str
        :ivar suitability_score: Minimum required suitability score
        :type suitability_score: int
        :param inference_artifacts_directory: Directory for storing transformation artifacts
        :type inference_artifacts_directory: str
        :param template: LWE transformation template name
        :type template: str
        :param debug: Enable debug logging
        :type debug: bool
        """
        self.voicing_preset = voicing_preset
        self.database = database
        self.suitability_score = suitability_score
        self.inference_artifacts_directory = inference_artifacts_directory
        self.limit = limit
        self.template = template
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(
            database=self.database,
            inference_artifacts_directory=self.inference_artifacts_directory,
            lwe_default_preset=self.voicing_preset,
            logger=self.logger,
        )
        self.utils.setup_lwe()

    def extract_transformed_content(self, xml_string: str) -> Tuple[str, str]:
        """
        Extract transformed chain of reasoning and answer from XML response.

        :param xml_string: XML formatted transformation response
        :type xml_string: str
        :return: Tuple containing (question, chain_of_reasoning, answer)
        :rtype: Tuple[str, str]
        :raises ValueError: If XML content is invalid or missing required elements
        """
        if not xml_string:
            raise ValueError("Empty XML string")

        root = ET.fromstring(xml_string)
        transformed = root.find(".//content")
        if transformed is None:
            raise ValueError("Missing content element")

        chain = transformed.find(".//chain_of_reasoning")
        answer = transformed.find(".//answer")

        if None in (chain, answer):
            raise ValueError("Missing required transformation elements")

        return (
            self.utils.clean_extracted_text(chain.text),
            self.utils.clean_extracted_text(answer.text),
        )

    def write_voicing_artifact(
        self,
        paper: sqlite3.Row,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        raw_content: str,
    ) -> None:
        """
        Write voice transformation results to an artifact file.

        Creates a formatted artifact file containing the transformed question,
        reasoning chain, and answer, along with metadata and raw inference output.

        :param paper: Paper data containing paper_id and paper_url
        :type paper: sqlite3.Row
        :param question: Original question
        :type question: str
        :param chain_of_reasoning: Transformed reasoning chain
        :type chain_of_reasoning: str
        :param answer: Transformed answer
        :type answer: str
        :param raw_content: Raw XML output from the transformation
        :type raw_content: str
        """
        artifact_name = constants.COT_VOICING_ARTIFACT_PATTERN.format(
            paper_id=paper["paper_id"]
        )
        headers = {
            constants.ARTIFACT_HEADER_KEY_PAPER_URL: paper["paper_url"],
            constants.ARTIFACT_HEADER_KEY_MODEL_PRESET: self.voicing_preset,
        }
        content = f"""Transformed Content:

----------------------

Question:

{question}

Chain of Reasoning:

{chain_of_reasoning}

Answer:

{answer}

------------

Raw Content:

{raw_content}
"""
        self.utils.write_inference_artifact(artifact_name, headers, content)

    def write_training_artifact(
        self,
        paper: sqlite3.Row,
        question: str,
        chain_of_reasoning: str,
        answer: str,
    ) -> None:
        """Write the final training data artifact to a JSONL file.

        Creates a training data entry in JSONL format containing the system message,
        question as user input, and reasoning chain with answer as assistant response.

        :param paper: Paper data containing paper_id
        :type paper: sqlite3.Row
        :param question: Final refined question
        :type question: str
        :param chain_of_reasoning: Final refined reasoning chain
        :type chain_of_reasoning: str
        :param answer: Final refined answer
        :type answer: str
        """
        artifact_name = f"{paper['paper_id']}-training-data.jsonl"
        training_data = {
            "system": constants.TRAINING_SYSTEM_MESSAGE,
            "user": question,
            "assistant": f"{chain_of_reasoning}\n\nAnswer: {answer}",
        }
        self.utils.write_training_artifact(artifact_name, training_data)

    def process_voicing(
        self,
        paper_content: str,
        question: str,
        chain_of_reasoning: str,
        answer: str,
    ) -> Tuple[str, str, str]:
        """
        Execute voice transformation template and process the results.

        :param paper_content: Full text content of the research paper
        :type paper_content: str
        :param question: Quality-assessed question
        :type question: str
        :param chain_of_reasoning: Quality-assessed reasoning chain
        :type chain_of_reasoning: str
        :param answer: Quality-assessed answer
        :type answer: str
        :return: Tuple containing (transformed_chain, transformed_answer, raw_response)
        :rtype: Tuple[str, str, str]
        :raises ValueError: If transformation response is invalid
        """
        voicing_response = self.utils.run_lwe_template(
            self.template,
            {
                "paper": paper_content,
                "question": question,
                "chain_of_reasoning": chain_of_reasoning,
                "answer": answer,
            },
        )

        xml_content = self.utils.extract_xml(voicing_response)
        if not xml_content:
            raise ValueError("Could not extract XML content from voicing response")

        transformed_c, transformed_a = self.extract_transformed_content(xml_content)
        return transformed_c, transformed_a, voicing_response

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Execute voice transformation workflow for a single paper.

        Processes an individual paper through the complete transformation pipeline:
        1. Extracts text content from PDF
        2. Retrieves quality-assessed data
        3. Runs voice transformation
        4. Generates transformation artifact
        5. Updates paper status

        :param paper: Database row containing paper metadata
        :type paper: sqlite3.Row
        """
        score = paper["cot_quality_assessment_suitability_score"]
        if score < self.suitability_score:
            self.logger.info(
                f"Skipping paper {paper['paper_id']}: score {score} below threshold {self.suitability_score}"
            )
            return None
        self.logger.info(f"Transforming paper {paper['paper_id']}")
        try:
            text = self.utils.get_pdf_text(paper)
            refined_data = (
                self.utils.extract_question_chain_of_reasoning_answer_from_artifact(
                    paper, constants.COT_REFINEMENT_ARTIFACT_PATTERN
                )
            )
            if not refined_data:
                raise ValueError("Could not retrieve refinement data for paper")

            question, chain_of_reasoning, answer = refined_data
            transformed_c, transformed_a, raw_response = self.process_voicing(
                text, question, chain_of_reasoning, answer
            )

            self.write_voicing_artifact(
                paper, question, transformed_c, transformed_a, raw_response
            )
            self.write_training_artifact(paper, question, transformed_c, transformed_a)

            self.utils.update_paper_status(paper["id"], constants.STATUS_COT_VOICED)
            self.logger.info(
                f"Successfully transformed paper {paper['paper_id']} - Status: {constants.STATUS_COT_VOICED}"
            )

        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_VOICING
            )

    def run(self) -> None:
        """
        Execute the main Chain of Thought voice transformation workflow.

        Orchestrates the complete transformation process:
        1. Fetches papers with STATUS_COT_QUALITY_SCORED status
        2. Processes each paper through voice transformation
        3. Updates paper status and stores transformation results
        4. Generates transformation artifacts

        :raises SystemExit: With code 1 if process fails critically
        """
        try:
            select_columns = constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + [
                "cot_quality_assessment_suitability_score"
            ]
            papers = self.utils.fetch_papers_by_processing_status(
                status=constants.STATUS_COT_QUALITY_SCORED,
                select_columns=select_columns,
                limit=self.limit,
            )
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("CoT voice transformation process completed")
        except Exception as e:
            self.logger.error(
                f"An error occurred during the CoT voice transformation process: {e}"
            )
            sys.exit(1)


def main() -> None:
    """
    Main entry point for the CoT voice transformation CLI.

    Parses command line arguments and initializes the transformation process.
    Handles the complete workflow from paper loading through transformation.
    """
    args = parse_arguments()
    voicer = CoTVoicing(
        limit=args.limit,
        voicing_preset=args.voicing_preset,
        database=args.database,
        suitability_score=args.suitability_score,
        inference_artifacts_directory=args.inference_artifacts_directory,
        template=args.template,
        debug=args.debug,
    )
    voicer.run()


if __name__ == "__main__":
    main()
