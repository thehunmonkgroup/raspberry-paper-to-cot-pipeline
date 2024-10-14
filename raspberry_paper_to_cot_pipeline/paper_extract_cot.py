#!/usr/bin/env python3

"""
This script extracts Chain of Thought (CoT) from research papers.
It downloads PDFs, extracts text, runs LWE templates, and processes the results.
"""

import argparse
import xml.etree.ElementTree as ET
import textwrap
from typing import Dict, Any, Tuple
import sys
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
        help="Model configuration used to perform the extraction, default: %(default)s",
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
        "--template",
        type=str,
        default=constants.DEFAULT_COT_EXTRACTION_TEMPLATE,
        help="LWE paper profiler template name, default: %(default)s",
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
        database: str,
        inference_artifacts_directory: str,
        training_artifacts_directory: str,
        limit: int,
        suitability_score: int,
        pdf_cache_dir: str,
        template: str,
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
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.training_artifacts_directory = training_artifacts_directory
        self.limit = limit
        self.suitability_score = suitability_score
        self.pdf_cache_dir = pdf_cache_dir
        self.template = template
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
        Process a single paper for CoT extraction.

        :param paper: Paper data
        """
        try:
            pdf_text = self.utils.get_pdf_text(paper)
            lwe_response = self.utils.run_lwe_template(
                self.template, {"paper": pdf_text}
            )
            xml_content = self.utils.extract_xml(lwe_response)
            if not xml_content:
                raise ValueError("Could not extract XML content from LWE response")
            question, chain_of_reasoning, answer = self.parse_xml(xml_content)
            self.write_inference_artifact(
                paper, question, chain_of_reasoning, answer, lwe_response
            )
            self.write_training_artifact(paper, question, chain_of_reasoning, answer)
            self.utils.update_paper_status(paper["id"], constants.STATUS_COT_EXTRACTED)
            self.logger.info(
                f"Successfully extracted CoT from paper {paper['paper_id']}"
            )
        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )

    @staticmethod
    def parse_xml(xml_string: str) -> Tuple[str, str, str]:
        """
        Parse the XML string to extract question, chain of reasoning, and answer.

        :param xml_string: XML string to parse
        :return: Tuple of (question, chain_of_reasoning, answer)
        """
        root = ET.fromstring(xml_string)
        question = root.find(".//question").text.strip()
        chain_of_reasoning = textwrap.dedent(
            root.find(".//chain_of_reasoning").text
        ).strip()
        answer = root.find(".//answer").text.strip()
        return question, chain_of_reasoning, answer

    def write_inference_artifact(
        self,
        paper: Dict[str, Any],
        question: str,
        chain_of_reasoning: str,
        answer: str,
        raw_content: str,
    ) -> None:
        """
        Write inference artifact to a file.

        :param paper: Paper data
        :param question: Extracted question
        :param chain_of_reasoning: Extracted chain of reasoning
        :param answer: Extracted answer
        :param raw_content: Raw LWE response content
        """
        artifact_name = f"{paper['paper_id']}-cot-extraction.txt"
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
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        training_artifacts_directory=args.training_artifacts_directory,
        limit=args.limit,
        suitability_score=args.suitability_score,
        pdf_cache_dir=args.pdf_cache_dir,
        template=args.template,
        debug=args.debug,
    )
    extractor.run()


if __name__ == "__main__":
    main()
