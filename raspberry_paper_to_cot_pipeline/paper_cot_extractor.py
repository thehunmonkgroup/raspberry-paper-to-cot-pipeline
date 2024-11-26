#!/usr/bin/env python3

"""Extract Chain of Thought (CoT) reasoning from research papers.

This script handles the automated extraction of Chain of Thought reasoning from academic papers.
It manages the full extraction pipeline including:
- PDF download and text extraction
- Initial CoT extraction using LLM templates
- Critique generation and analysis
- Refinement based on critique
- Generation of training artifacts

The process is configurable through command-line arguments and uses a SQLite database
to track paper processing status.
"""

import argparse
import requests
from typing import Tuple, Generator, Optional
import sqlite3
import xml
import xml.etree.ElementTree as ET
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments for the CoT extraction process.

    Configures and processes all command-line arguments needed for the Chain of Thought
    extraction pipeline.

    :return: Parsed command-line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Extract Chain of Thought (CoT) from research papers."
    )
    parser.add_argument(
        "--extraction-preset",
        type=str,
        default=constants.DEFAULT_COT_EXTRACTION_PRESET,
        help="Model configuration used to perform the initial extraction, default: %(default)s",
    )
    parser.add_argument(
        "--critique-preset",
        type=str,
        default=constants.DEFAULT_COT_CRITIQUE_PRESET,
        help="Model configuration used to perform the critique, default: %(default)s",
    )
    parser.add_argument(
        "--refinement-preset",
        type=str,
        default=constants.DEFAULT_COT_REFINEMENT_PRESET,
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
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of papers to process, default: %(default)s",
    )
    group.add_argument(
        "--paper-id",
        type=str,
        help="Process a specific paper by its ID",
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
    """Handle Chain of Thought (CoT) extraction from research papers.

    This class manages the complete pipeline for extracting, critiquing, and refining
    Chain of Thought reasoning from academic papers. It coordinates:
    - Paper selection based on suitability scores
    - PDF processing and text extraction
    - Initial CoT extraction using LLM templates
    - Critique generation and analysis
    - Refinement of extracted reasoning
    - Generation of training artifacts

    The class uses configurable LLM presets and templates for each stage of processing.
    Results and artifacts are stored in specified directories for both inference and training.
    """

    def __init__(
        self,
        limit: Optional[int] = 1,
        debug: bool = False,
        extraction_preset: str = constants.DEFAULT_COT_EXTRACTION_PRESET,
        critique_preset: str = constants.DEFAULT_COT_CRITIQUE_PRESET,
        refinement_preset: str = constants.DEFAULT_COT_REFINEMENT_PRESET,
        database: str = constants.DEFAULT_DB_NAME,
        inference_artifacts_directory: str = constants.DEFAULT_INFERENCE_ARTIFACTS_DIR,
        training_artifacts_directory: str = constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        paper_id: Optional[str] = None,
        suitability_score: int = constants.COT_EXTRACTION_DEFAULT_SUITABILITY_SCORE,
        pdf_cache_dir: str = constants.DEFAULT_PDF_CACHE_DIR,
        initial_cot_extraction_template: str = constants.DEFAULT_COT_EXTRACTION_TEMPLATE,
        critique_template: str = constants.DEFAULT_COT_CRITIQUE_TEMPLATE,
        refinement_template: str = constants.DEFAULT_COT_REFINEMENT_TEMPLATE,
    ):
        """Initialize the CoTExtractor with processing configuration.

        Sets up all necessary attributes and configurations for the Chain of Thought
        extraction pipeline, including model presets, file paths, and processing options.
        Initializes logging and utility components.

        :param extraction_preset: Model configuration for initial extraction
        :type extraction_preset: str
        :param critique_preset: Model configuration for critique generation
        :type critique_preset: str
        :param refinement_preset: Model configuration for refinement
        :type refinement_preset: str
        :param database: Path to the SQLite database
        :type database: str
        :param inference_artifacts_directory: Directory for inference artifacts
        :type inference_artifacts_directory: str
        :param training_artifacts_directory: Directory for training artifacts
        :type training_artifacts_directory: str
        :param limit: Number of papers to process, defaults to None
        :type limit: Optional[int]
        :param paper_id: Specific paper ID to process, defaults to None
        :type paper_id: Optional[str]
        :param suitability_score: Minimum required suitability score
        :type suitability_score: int
        :param pdf_cache_dir: Directory for caching PDFs
        :type pdf_cache_dir: str
        :param initial_cot_extraction_template: Template for initial extraction
        :type initial_cot_extraction_template: str
        :param critique_template: Template for critique generation
        :type critique_template: str
        :param refinement_template: Template for refinement
        :type refinement_template: str
        :param debug: Enable debug logging
        :type debug: bool
        """
        self.extraction_preset = extraction_preset
        self.critique_preset = critique_preset
        self.refinement_preset = refinement_preset
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.training_artifacts_directory = training_artifacts_directory
        self.limit = limit
        self.paper_id = paper_id
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

    def fetch_specific_paper(self, paper_id: str) -> Generator[sqlite3.Row, None, None]:
        """Fetch a specific paper from the database by its ID.

        Queries the database for a paper with the given ID and yields its data.
        Used when processing a single specific paper rather than batch processing.

        :param paper_id: ID of the paper to fetch from database
        :type paper_id: str
        :return: Generator yielding the paper data as dictionary or database row
        :rtype: Generator[Union[Dict[str, Any], sqlite3.Row], None, None]
        :raises RuntimeError: If paper with given ID is not found in database
        """
        query = """
        SELECT id, paper_id, paper_url
        FROM papers
        WHERE paper_id = ?
        """
        self.logger.debug("Fetching specific paper with ID: %s", paper_id)
        papers = self.utils.fetch_papers_by_custom_query(query, (paper_id,))
        if not papers:
            raise RuntimeError(f"Paper with ID {paper_id} not found in database")
        yield from papers

    def fetch_papers(self) -> Generator[sqlite3.Row, None, None]:
        """Fetch papers from the database for processing.

        Retrieves papers based on either a specific paper ID if provided, or based on
        suitability score and processing status. Handles both single-paper and batch
        processing modes.

        :return: Generator of paper data rows containing id, paper_id, and paper_url
        :rtype: Generator[sqlite3.Row, None, None]
        """
        if hasattr(self, "paper_id") and self.paper_id:
            return self.fetch_specific_paper(self.paper_id)
        select_columns = constants.DEFAULT_FETCH_BY_STATUS_COLUMNS + [
            "profiler_suitability_score"
        ]
        return self.utils.fetch_papers_by_processing_status(
            constants.STATUS_PAPER_PROFILE_SCORED,
            select_columns=select_columns,
            limit=self.limit,
        )

    def _check_suitability(self, paper: sqlite3.Row) -> bool:
        """Check if paper meets minimum suitability requirements for processing.

        Evaluates the paper's profiler suitability score against the minimum threshold
        to determine if it should be processed.

        :param paper: Paper data containing profiler_suitability_score
        :type paper: sqlite3.Row
        :return: True if paper meets suitability requirements, False otherwise
        :rtype: bool
        """
        if (
            "profiler_suitability_score" in paper.keys()
            and paper["profiler_suitability_score"] < self.suitability_score
        ):
            self.logger.debug(
                f"Skipping paper {paper['paper_id']} due to low suitability score"
            )
            return False
        return True

    def _handle_extraction_stage(
        self, paper: sqlite3.Row, pdf_text: str
    ) -> Tuple[str, str, str]:
        """Handle the initial Chain of Thought extraction stage.

        Processes the paper text to extract the initial question, chain of reasoning,
        and answer. Writes the extraction results to an artifact file.

        :param paper: Paper data containing paper_id and metadata
        :type paper: sqlite3.Row
        :param pdf_text: Extracted text content of the paper
        :type pdf_text: str
        :return: Tuple of (question, chain_of_reasoning, answer)
        :rtype: Tuple[str, str, str]
        """
        question, chain_of_reasoning, answer, initial_response = (
            self.process_initial_cot_extraction(pdf_text)
        )
        self.write_initial_cot_extraction_artifact(
            paper, question, chain_of_reasoning, answer, initial_response
        )
        self.logger.info(f"Completed initial extraction for paper {paper['paper_id']}")
        return question, chain_of_reasoning, answer

    def _handle_critique_stage(
        self,
        paper: sqlite3.Row,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        pdf_text: str,
    ) -> str:
        """Handle the critique stage of the CoT extraction pipeline.

        Processes the initial extraction results to generate a critique of the reasoning
        and conclusions. Writes critique results to an artifact file.

        :param paper: Paper data containing paper_id and metadata
        :type paper: sqlite3.Row
        :param question: Initially extracted question
        :type question: str
        :param chain_of_reasoning: Initially extracted reasoning chain
        :type chain_of_reasoning: str
        :param answer: Initially extracted answer
        :type answer: str
        :param pdf_text: Full text content of the paper
        :type pdf_text: str
        :return: Generated critique of the extraction
        :rtype: str
        """
        critique, critique_response = self.process_critique(
            question, chain_of_reasoning, answer, pdf_text
        )
        self.write_critique_artifact(paper, critique, critique_response)
        self.logger.info(f"Completed critique for paper {paper['paper_id']}")
        return critique

    def _handle_refinement_stage(
        self,
        paper: sqlite3.Row,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        critique: str,
        pdf_text: str,
    ) -> None:
        """Handle the refinement stage of the CoT extraction pipeline.

        Processes the critique to generate refined versions of the question, reasoning
        chain and answer. Writes both refinement and training artifacts.

        :param paper: Paper data containing paper_id and metadata
        :type paper: sqlite3.Row
        :param question: Original extracted question
        :type question: str
        :param chain_of_reasoning: Original reasoning chain
        :type chain_of_reasoning: str
        :param answer: Original extracted answer
        :type answer: str
        :param critique: Generated critique of initial extraction
        :type critique: str
        :param pdf_text: Full text content of the paper
        :type pdf_text: str
        """
        refined_q, refined_c, refined_a, refinement_response = self.process_refinement(
            question, chain_of_reasoning, answer, critique, pdf_text
        )
        self.write_refinement_artifact(
            paper, refined_q, refined_c, refined_a, refinement_response
        )
        self.logger.info(f"Completed refinement for paper {paper['paper_id']}")
        self.write_training_artifact(paper, refined_q, refined_c, refined_a)

    def process_paper(self, paper: sqlite3.Row) -> None:
        """
        Process a single paper for CoT extraction, critique, and refinement.

        :param paper: Paper data
        """
        if not self._check_suitability(paper):
            return

        self.logger.info(f"Starting processing of paper {paper['paper_id']}")
        self.logger.debug(f"Paper details: {dict(paper)}")

        try:
            self.logger.debug(f"Fetching PDF text for paper {paper['paper_id']}")
            pdf_text = self.utils.get_pdf_text(paper)
            self.logger.debug(f"PDF text length: {len(pdf_text)} characters")

            self.logger.info(f"Processing paper {paper['paper_id']}: Extraction stage")
            question, chain_of_reasoning, answer = self._handle_extraction_stage(
                paper, pdf_text
            )
            self.logger.info(
                f"Completed extraction stage for paper {paper['paper_id']}"
            )
            self.logger.debug(
                f"Extraction details - Question length: {len(question)}, "
                f"Reasoning length: {len(chain_of_reasoning)}, "
                f"Answer length: {len(answer)}"
            )

            self.logger.info(f"Processing paper {paper['paper_id']}: Critique stage")
            critique = self._handle_critique_stage(
                paper, question, chain_of_reasoning, answer, pdf_text
            )
            self.logger.info(f"Completed critique stage for paper {paper['paper_id']}")
            self.logger.debug(f"Critique completed - Length: {len(critique)}")

            self.logger.info(f"Processing paper {paper['paper_id']}: Refinement stage")
            self._handle_refinement_stage(
                paper, question, chain_of_reasoning, answer, critique, pdf_text
            )
            self.logger.info(
                f"Completed refinement stage for paper {paper['paper_id']}"
            )
            self.logger.debug(f"Refinement completed for paper {paper['paper_id']}")

            self.utils.update_paper_status(paper["id"], constants.STATUS_COT_EXTRACTED)
            self.logger.info(
                f"Successfully completed all stages for paper {paper['paper_id']}"
            )

        except requests.RequestException as e:
            self.logger.error(
                f"PDF download error for paper {paper['paper_id']}: {str(e)}"
            )
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )
        except sqlite3.Error as e:
            self.logger.error(
                f"Database error processing paper {paper['paper_id']}: {str(e)}"
            )
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )
            raise
        except xml.etree.ElementTree.ParseError as e:
            self.logger.error(
                f"XML parsing error for paper {paper['paper_id']}: {str(e)}"
            )
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )
        except ValueError as e:
            self.logger.error(
                f"Value error processing paper {paper['paper_id']}: {str(e)}"
            )
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error processing paper {paper['paper_id']}: {str(e)}"
            )
            self.utils.update_paper_status(
                paper["id"], constants.STATUS_FAILED_COT_EXTRACTION
            )
            raise

    def write_initial_cot_extraction_artifact(
        self,
        paper: sqlite3.Row,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        raw_content: str,
    ) -> None:
        """Write the initial CoT extraction results to an artifact file.

        Creates a formatted artifact file containing the extracted question, reasoning
        chain, and answer, along with metadata and raw LLM response.

        :param paper: Paper data containing paper_id and paper_url
        :type paper: sqlite3.Row
        :param question: Extracted research question
        :type question: str
        :param chain_of_reasoning: Extracted reasoning chain
        :type chain_of_reasoning: str
        :param answer: Extracted answer
        :type answer: str
        :param raw_content: Raw LLM response content
        :type raw_content: str
        """
        artifact_name = constants.COT_INITIAL_EXTRACTION_ARTIFACT_PATTERN.format(
            paper_id=paper["paper_id"]
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
        paper: sqlite3.Row,
        critique: str,
        raw_content: str,
    ) -> None:
        """Write the critique results to an artifact file.

        Creates a formatted artifact file containing the generated critique along
        with metadata and raw LLM response.

        :param paper: Paper data containing paper_id and paper_url
        :type paper: sqlite3.Row
        :param critique: Generated critique of the extraction
        :type critique: str
        :param raw_content: Raw LLM response content
        :type raw_content: str
        """
        artifact_name = constants.COT_CRITIQUE_ARTIFACT_PATTERN.format(
            paper_id=paper["paper_id"]
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
        paper: sqlite3.Row,
        question: str,
        chain_of_reasoning: str,
        answer: str,
        raw_content: str,
    ) -> None:
        """Write the refinement results to an artifact file.

        Creates a formatted artifact file containing the refined question, reasoning
        chain, and answer, along with metadata and raw LLM response.

        :param paper: Paper data containing paper_id and paper_url
        :type paper: sqlite3.Row
        :param question: Refined research question
        :type question: str
        :param chain_of_reasoning: Refined reasoning chain
        :type chain_of_reasoning: str
        :param answer: Refined answer
        :type answer: str
        :param raw_content: Raw LLM response content
        :type raw_content: str
        """
        artifact_name = constants.COT_REFINEMENT_ARTIFACT_PATTERN.format(
            paper_id=paper["paper_id"]
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
        self, pdf_text: str
    ) -> Tuple[str, str, str, str]:
        """
        Process the initial CoT extraction for a paper.

        :param pdf_text: Text content of the paper
        :return: Tuple of (question, chain_of_reasoning, answer, initial_response)
        :raises RuntimeError: If extraction processing fails
        """
        self.logger.debug("Starting initial CoT extraction")
        try:
            self.logger.debug(
                f"Running LWE template with preset: {self.extraction_preset}"
            )
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
            self.logger.debug(f"LWE template response length: {len(initial_response)}")

            self.logger.debug("Extracting components from response")
            question, chain_of_reasoning, answer = (
                self.utils.extract_question_chain_of_reasoning_answer(initial_response)
            )
            self.logger.debug("Successfully extracted all components")
            return question, chain_of_reasoning, answer, initial_response

        except requests.RequestException as e:
            self.logger.error(f"LWE API request failed: {str(e)}")
            raise RuntimeError(f"LWE API request failed: {str(e)}") from e
        except ValueError as e:
            self.logger.error(f"Failed to parse LWE response: {str(e)}")
            raise RuntimeError(f"Failed to parse LWE response: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error in initial extraction: {str(e)}")
            raise RuntimeError(f"Initial extraction processing failed: {str(e)}") from e

    def extract_critique(self, xml_string: str) -> str:
        """Extract analysis and critique content from XML response.

        Parses the XML response from the LLM to extract the structured critique
        content from the designated XML tags.

        :param xml_string: XML formatted string containing critique response
        :type xml_string: str
        :return: Extracted critique content
        :rtype: Tuple[str, str]
        :raises ValueError: If XML string is empty or missing required elements
        """
        if not xml_string:
            raise ValueError("Empty XML string")
        root = ET.fromstring(xml_string)
        critique = root.find(".//critique")
        if critique is None:
            raise ValueError("Missing required XML element critique")
        return self.utils.clean_extracted_text(critique.text)

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
        self.logger.debug("Starting critique processing")
        try:
            self.logger.debug(
                f"Running critique template with preset: {self.critique_preset}"
            )
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
            self.logger.debug(f"Critique response length: {len(critique_response)}")

            self.logger.debug("Extracting XML content from critique response")
            xml_content = self.utils.extract_xml(critique_response)
            if not xml_content:
                raise ValueError("Could not extract XML content from critique")
            self.logger.debug(f"Extracted XML content length: {len(xml_content)}")

            self.logger.debug("Parsing critique from XML")
            critique = self.extract_critique(xml_content)
            self.logger.debug(
                f"Successfully extracted critique of length: {len(critique)}"
            )
            return critique, critique_response

        except requests.RequestException as e:
            self.logger.error(f"LWE API request failed during critique: {str(e)}")
            raise RuntimeError(f"Critique LWE API request failed: {str(e)}") from e
        except xml.etree.ElementTree.ParseError as e:
            self.logger.error(f"Failed to parse critique XML: {str(e)}")
            raise RuntimeError(f"Failed to parse critique XML: {str(e)}") from e
        except ValueError as e:
            self.logger.error(f"Invalid critique response format: {str(e)}")
            raise RuntimeError(f"Invalid critique format: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error in critique processing: {str(e)}")
            raise RuntimeError(f"Critique processing failed: {str(e)}") from e

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
        self.logger.debug("Starting refinement processing")
        try:
            self.logger.debug(
                f"Running refinement template with preset: {self.refinement_preset}"
            )
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
            self.logger.debug(f"Refinement response length: {len(refinement_response)}")

            self.logger.debug("Extracting refined components")
            refined_q, refined_c, refined_a = (
                self.utils.extract_question_chain_of_reasoning_answer(
                    refinement_response
                )
            )
            self.logger.debug(
                f"Refinement complete - Question length: {len(refined_q)}, "
                f"Chain length: {len(refined_c)}, Answer length: {len(refined_a)}"
            )
            return refined_q, refined_c, refined_a, refinement_response

        except requests.RequestException as e:
            self.logger.error(f"LWE API request failed during refinement: {str(e)}")
            raise RuntimeError(f"Refinement LWE API request failed: {str(e)}") from e
        except ValueError as e:
            self.logger.error(f"Failed to parse refinement response: {str(e)}")
            raise RuntimeError(f"Failed to parse refinement response: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error in refinement processing: {str(e)}")
            raise RuntimeError(f"Refinement processing failed: {str(e)}") from e

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

    def run(self) -> None:
        """Execute the main logic of the CoT extraction process.

        Orchestrates the complete Chain of Thought extraction pipeline:
        1. Fetches papers from database based on criteria
        2. For each paper:
           - Downloads and processes PDF
           - Performs initial CoT extraction
           - Generates critique
           - Refines extraction based on critique
           - Creates training artifacts

        :raises: Exception: If a fatal error occurs during processing
        """
        try:
            papers = self.fetch_papers()
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("CoT extraction process completed")
        except Exception as e:
            self.logger.error(
                f"An error occurred during the CoT extraction process: {e}"
            )
            raise


def main():
    """Main entry point for CLI usage.

    Parses command line arguments and initializes the CoT extraction pipeline.
    Configures the extractor with provided options and executes the pipeline.

    """
    args = parse_arguments()
    if args.debug:
        print(f"Arguments: {vars(args)}")
    extractor = CoTExtractor(
        limit=args.limit,
        debug=args.debug,
        extraction_preset=args.extraction_preset,
        critique_preset=args.critique_preset,
        refinement_preset=args.refinement_preset,
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        training_artifacts_directory=args.training_artifacts_directory,
        paper_id=args.paper_id,
        suitability_score=args.suitability_score,
        pdf_cache_dir=args.pdf_cache_dir,
        initial_cot_extraction_template=args.initial_cot_extraction_template,
        critique_template=args.critique_template,
        refinement_template=args.refinement_template,
    )
    extractor.run()


if __name__ == "__main__":
    main()
