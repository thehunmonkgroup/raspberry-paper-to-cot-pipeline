#!/usr/bin/env python3

"""
This script extracts Chain of Thought (CoT) from research papers.
It downloads PDFs, extracts text, runs LWE templates, and processes the results.
"""

import argparse
from typing import Dict, Any, Tuple
import sys
import xml.etree.ElementTree as ET
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Extract Chain of Thought (CoT) from research papers."
    )
    parser.add_argument(
        "--extraction-preset",
        type=str,
        default=constants.DEFAULT_LWE_PRESET,
        help="Model configuration used to perform the initial extraction, default: %(default)s",
    )
    parser.add_argument(
        "--critique-preset",
        type=str,
        default=constants.DEFAULT_CRITIQUE_PRESET,
        help="Model configuration used to perform the critique, default: %(default)s",
    )
    parser.add_argument(
        "--refinement-preset",
        type=str,
        default=constants.DEFAULT_REFINEMENT_PRESET,
        help="Model configuration used to perform the refinement, default: %(default)s",
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
        "--training-artifacts-directory",
        type=str,
        default=constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        help="Directory for training artifacts, default: %(default)s",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of papers to process, default: %(default)s",
    )
    parser.add_argument(
        "--suitability-score",
        type=int,
        default=constants.COT_EXTRACTION_DEFAULT_SUITABILITY_SCORE,
        help="Minimum suitability score for papers to process, default: %(default)s",
    )
    parser.add_argument(
        "--pdf-cache-dir",
        type=str,
        default=constants.DEFAULT_PDF_CACHE_DIR,
        help="PDF cache directory, default: %(default)s",
    )
    parser.add_argument(
        "--initial-cot-extraction-template",
        type=str,
        default=constants.DEFAULT_COT_EXTRACTION_TEMPLATE,
        help="LWE template for initial CoT extraction, default: %(default)s",
    )
    parser.add_argument(
        "--critique-template",
        type=str,
        default=constants.DEFAULT_COT_CRITIQUE_TEMPLATE,
        help="LWE template for CoT critique, default: %(default)s",
    )
    parser.add_argument(
        "--refinement-template",
        type=str,
        default=constants.DEFAULT_COT_REFINEMENT_TEMPLATE,
        help="LWE template for CoT refinement, default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class CoTExtractor:
    """
    A class to handle Chain of Thought (CoT) extraction from research papers.
    """

    def __init__(
        self,
        extraction_preset: str,
        critique_preset: str,
        refinement_preset: str,
        database: str,
        inference_artifacts_directory: str,
        training_artifacts_directory: str,
        limit: int,
        suitability_score: int,
        pdf_cache_dir: str,
        initial_cot_extraction_template: str,
        critique_template: str,
        refinement_template: str,
        debug: bool,
    ):
        """
        Initialize the CoTExtractor with individual arguments.

        :param extraction_preset: Model configuration used to perform the extraction
        :param database: Path to the SQLite database
        :param inference_artifacts_directory: Directory for inference artifacts
        :param training_artifacts_directory: Directory for training artifacts
        :param limit: Number of papers to process
        :param suitability_score: Minimum suitability score for papers to process
        :param pdf_cache_dir: PDF cache directory
        :param template: LWE paper profiler template name
        :param debug: Enable debug logging
        """
        self.extraction_preset = extraction_preset
        self.critique_preset = critique_preset
        self.refinement_preset = refinement_preset
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.training_artifacts_directory = training_artifacts_directory
        self.limit = limit
        self.suitability_score = suitability_score
        self.pdf_cache_dir = pdf_cache_dir
        self.initial_cot_extraction_template = initial_cot_extraction_template
        self.critique_template = critique_template
        self.refinement_template = refinement_template
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(
            database=self.database,
            inference_artifacts_directory=self.inference_artifacts_directory,
            training_artifacts_directory=self.training_artifacts_directory,
            pdf_cache_dir=self.pdf_cache_dir,
            lwe_default_preset=self.extraction_preset,
            logger=self.logger,
        )
        self.utils.setup_lwe()

    def fetch_papers(self) -> Any:
        """
        Fetch papers from the database based on suitability score.

        :return: Generator of paper data
        """
        query = f"""
        SELECT id, paper_id, paper_url
        FROM papers
        WHERE processing_status = '{constants.STATUS_SCORED}' AND suitability_score >= ?
        ORDER BY RANDOM()
        LIMIT ?
        """
        return self.utils.fetch_papers_by_custom_query(
            query, (self.suitability_score, self.limit)
        )

    def process_paper(self, paper: Dict[str, Any]) -> None:
        """
        Process a single paper for CoT extraction, critique, and refinement.

        :param paper: Paper data
        """
        try:
            pdf_text = self.utils.get_pdf_text(paper)
            question, chain_of_reasoning, answer, initial_response = self.process_initial_cot_extraction(
                pdf_text
            )
            self.write_initial_cot_extraction_artifact(
                paper, question, chain_of_reasoning, answer, initial_response
            )
            self.logger.info(
                f"Completed initial extraction for paper {paper['paper_id']}"
            )
            critique, critique_response = self.process_critique(
                question, chain_of_reasoning, answer, pdf_text
            )
            self.write_critique_artifact(paper, critique, critique_response)
            self.logger.info(
                f"Completed critique for paper {paper['paper_id']}"
            )
            refined_q, refined_c, refined_a, refinement_response = self.process_refinement(
                question, chain_of_reasoning, answer, critique, pdf_text
            )
            self.write_refinement_artifact(
                paper, refined_q, refined_c, refined_a, refinement_response
            )
            self.logger.info(
                f"Completed refinement for paper {paper['paper_id']}"
            )
            self.write_training_artifact(paper, refined_q, refined_c, refined_a)
            self.utils.update_paper_status(paper["id"], constants.STATUS_COT_EXTRACTED)
            self.logger.info(
                f"Successfully completed all stages for paper {paper['paper_id']}"
            )

        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )

    def write_initial_cot_extraction_artifact(
        self,
        paper: Dict[str, Any],
        question: str,
        chain_of_reasoning: str,
        answer: str,
        raw_content: str,
    ) -> None:
        """
        Write initial extraction artifact to a file.

        :param paper: Paper data
        :param question: Extracted question
        :param chain_of_reasoning: Extracted chain of reasoning
        :param answer: Extracted answer
        :param raw_content: Raw LWE response content
        """
        artifact_name = constants.INITIAL_EXTRACTION_ARTIFACT_PATTERN.format(
            paper_id=paper['paper_id']
        )
        content = f"""Paper URL: {paper['paper_url']}
Extraction preset: {self.extraction_preset}

Extracted Information:

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
        self.utils.write_inference_artifact(artifact_name, content)

    def write_critique_artifact(
        self,
        paper: Dict[str, Any],
        critique: str,
        raw_content: str,
    ) -> None:
        """
        Write critique artifact to a file.

        :param paper: Paper data
        :param critique: Critique
        :param critique_response: Raw critique response
        """
        artifact_name = constants.CRITIQUE_ARTIFACT_PATTERN.format(
            paper_id=paper['paper_id']
        )
        content = f"""Paper URL: {paper['paper_url']}
Critique preset: {self.critique_preset}

Critique:
----------------------
{critique}

Raw Response:
----------------------
{raw_content}
"""
        self.utils.write_inference_artifact(artifact_name, content)

    def write_refinement_artifact(
        self,
        paper: Dict[str, Any],
        question: str,
        chain_of_reasoning: str,
        answer: str,
        raw_content: str,
    ) -> None:
        """
        Write refinement artifact to a file.

        :param paper: Paper data
        :param question: Refined question
        :param chain_of_reasoning: Refined chain of reasoning
        :param answer: Refined answer
        :param raw_content: Raw refinement content
        """
        artifact_name = constants.REFINEMENT_ARTIFACT_PATTERN.format(
            paper_id=paper['paper_id']
        )
        content = f"""Paper URL: {paper['paper_url']}
Refinement preset: {self.refinement_preset}

Refined Information:

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
        self.utils.write_inference_artifact(artifact_name, content)

    def process_initial_cot_extraction(
        self,
        pdf_text: str
    ) -> Tuple[str, str, str, str]:
        """
        Process the initial CoT extraction for a paper.

        :param pdf_text: Text content of the paper
        :return: Tuple of (question, chain_of_reasoning, answer, initial_response)
        :raises RuntimeError: If extraction processing fails
        """
        try:
            initial_response = self.utils.run_lwe_template(
                self.initial_cot_extraction_template,
                {
                    "paper": pdf_text,
                },
                {
                    "request_overrides": {
                        "preset": self.extraction_preset,
                    },
                },
            )
            question, chain_of_reasoning, answer = self.utils.extract_question_chain_of_reasoning_answer(
                initial_response
            )
            return question, chain_of_reasoning, answer, initial_response
        except Exception as e:
            self.logger.error(f"Error processing initial extraction: {str(e)}")
            raise RuntimeError(f"Initial extraction processing failed: {str(e)}")

    def extract_critique(self, xml_string: str) -> Tuple[str, str]:
        """
        Extract analysis and critique content from XML response.

        :param xml_string: XML string containing critique response
        :return: Critique content
        :raises ValueError: If XML parsing fails
        """
        if not xml_string:
            raise ValueError("Empty XML string")
        root = ET.fromstring(xml_string)
        critique = root.find(".//critique")
        if critique is None:
            raise ValueError("Missing required XML element critique")
        return critique.text.strip()

    def process_critique(
        self,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        pdf_text: str,
    ) -> Tuple[str, str]:
        """
        Process critique for the initial extraction.

        :param question: Initial question
        :param chain_of_reasoning: Initial chain of reasoning
        :param answer: Initial answer
        :param pdf_text: Paper content
        :return: Tuple of (critique_content, raw_response)
        :raises RuntimeError: If critique processing fails
        """
        try:
            critique_response = self.utils.run_lwe_template(
                self.critique_template,
                {
                    "paper": pdf_text,
                    "question": question,
                    "chain_of_reasoning": chain_of_reasoning,
                    "answer": answer,
                },
                {
                    "request_overrides": {
                        "preset": self.critique_preset,
                    },
                },
            )
            xml_content = self.utils.extract_xml(critique_response)
            if not xml_content:
                raise ValueError("Could not extract XML content from critique")

            critique = self.extract_critique(xml_content)
            return critique, critique_response
        except Exception as e:
            self.logger.error(f"Error processing critique: {str(e)}")
            raise RuntimeError(f"Critique processing failed: {str(e)}")

    def process_refinement(
        self,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        critique: str,
        pdf_text: str,
    ) -> Tuple[str, str, str, str]:
        """
        Process refinement based on critique.

        :param question: Initial question
        :param chain_of_reasoning: Initial chain of reasoning
        :param answer: Initial answer
        :param critique: Critique content
        :param pdf_text: Paper content
        :return: Tuple of (refined_question, refined_chain, refined_answer, raw_response)
        :raises RuntimeError: If refinement processing fails
        """
        try:
            refinement_response = self.utils.run_lwe_template(
                self.refinement_template,
                {
                    "paper": pdf_text,
                    "question": question,
                    "chain_of_reasoning": chain_of_reasoning,
                    "answer": answer,
                    "critique": critique,
                },
                {
                    "request_overrides": {
                        "preset": self.refinement_preset,
                    },
                },
            )
            refined_q, refined_c, refined_a = self.utils.extract_question_chain_of_reasoning_answer(
                refinement_response
            )
            return refined_q, refined_c, refined_a, refinement_response
        except Exception as e:
            self.logger.error(f"Error processing refinement: {str(e)}")
            raise RuntimeError(f"Refinement processing failed: {str(e)}")

    def write_training_artifact(
        self,
        paper: Dict[str, Any],
        question: str,
        chain_of_reasoning: str,
        answer: str,
    ) -> None:
        """
        Write training artifact to a file.

        :param paper: Paper data
        :param question: Extracted question
        :param chain_of_reasoning: Extracted chain of reasoning
        :param answer: Extracted answer
        """
        artifact_name = f"{paper['paper_id']}-training-data.jsonl"
        training_data = {
            "system": constants.TRAINING_SYSTEM_MESSAGE,
            "user": question,
            "assistant": f"{chain_of_reasoning}\n\nAnswer: {answer}",
        }
        self.utils.write_training_artifact(artifact_name, training_data)

    def run(self) -> None:
        """Execute the main logic of the CoT extraction process."""
        try:
            papers = self.fetch_papers()
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("CoT extraction process completed")
        except Exception as e:
            self.logger.error(
                f"An error occurred during the CoT extraction process: {e}"
            )
            sys.exit(1)


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    extractor = CoTExtractor(
        extraction_preset=args.extraction_preset,
        critique_preset=args.critique_preset,
        refinement_preset=args.refinement_preset,
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        training_artifacts_directory=args.training_artifacts_directory,
        limit=args.limit,
        suitability_score=args.suitability_score,
        pdf_cache_dir=args.pdf_cache_dir,
        initial_cot_extraction_template=args.initial_cot_extraction_template,
        critique_template=args.critique_template,
        refinement_template=args.refinement_template,
        debug=args.debug,
    )
    extractor.run()


if __name__ == "__main__":
    main()
