#!/usr/bin/env python3

"""
This script processes training and inference files for Chain of Thought (CoT) extraction from research papers.
It extracts XML content, parses it, and writes the results to inference and training files.
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
import textwrap
from urllib.parse import urlparse
import sqlite3
import logging
from pathlib import Path
from typing import Tuple, Optional

SYSTEM_MESSAGE = "You are a thinking agent responsible for developing a detailed, step-by-step thought process in response to a request, problem, or conversation. Your task is to break down the situation into a structured reasoning process. If feedback is provided, integrate it into your thought process for refinement."


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Process training and inference files."
    )
    parser.add_argument(
        "extraction_preset",
        type=str,
        help="Model configuration used to perform the extraction",
    )
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument(
        "paper_content", type=str, help="Content to be written and logged"
    )
    parser.add_argument("training_file", type=str, help="Path to the training file")
    parser.add_argument(
        "inference_results_directory", type=str, help="Directory for inference results"
    )
    parser.add_argument(
        "training_results_directory", type=str, help="Directory for training results"
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
        paper_id: str,
        paper_url: str,
        paper_content: str,
        training_file: str,
        inference_results_directory: str,
        training_results_directory: str,
        debug: bool,
    ):
        """
        Initialize the CoTExtractor with individual arguments.

        :param extraction_preset: Model configuration used to perform the extraction
        :param database: Path to the SQLite database
        :param paper_id: ID of the paper in the database
        :param paper_url: URL of the paper
        :param paper_content: Content to be written and logged
        :param training_file: Path to the training file
        :param inference_results_directory: Directory for inference results
        :param training_results_directory: Directory for training results
        :param debug: Enable debug logging
        """
        self.extraction_preset = extraction_preset
        self.database = database
        self.paper_id = paper_id
        self.paper_url = paper_url
        self.paper_content = paper_content
        self.training_file = training_file
        self.inference_results_directory = inference_results_directory
        self.training_results_directory = training_results_directory
        self.debug = debug
        self.setup_logging()

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def make_results_directories(self) -> None:
        """Create the inference and training results directories if they don't exist."""
        Path(self.inference_results_directory).mkdir(parents=True, exist_ok=True)
        Path(self.training_results_directory).mkdir(parents=True, exist_ok=True)
        self.logger.debug(
            f"Ensured inference results directory exists: {self.inference_results_directory}"
        )
        self.logger.debug(
            f"Ensured training results directory exists: {self.training_results_directory}"
        )

    def extract_xml(self) -> Optional[str]:
        """
        Extract XML content from the paper content.

        :return: Extracted XML content or None if not found
        """
        match = re.search(
            r"<results>(?:(?!</results>).)*</results>", self.paper_content, re.DOTALL
        )
        return match.group(0) if match else None

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

    def get_file_basename(self) -> str:
        """
        Get the basename for the output files.

        :return: Basename derived from the paper URL
        """
        parsed_url = urlparse(self.paper_url)
        return Path(parsed_url.path).stem

    def write_to_inference_file(
        self, question: str, chain_of_reasoning: str, answer: str
    ) -> None:
        """
        Write extracted information to the inference file.

        :param question: Extracted question
        :param chain_of_reasoning: Extracted chain of reasoning
        :param answer: Extracted answer
        """
        basename = self.get_file_basename()
        inference_file_path = (
            Path(self.inference_results_directory) / f"{basename}-cot-extraction.txt"
        )

        with open(inference_file_path, "w") as file:
            file.write(f"Paper URL: {self.paper_url}\n")
            file.write(f"Extraction preset: {self.extraction_preset}\n\n")
            file.write("Extracted Information:\n\n")
            file.write("----------------------\n\n")
            file.write(f"Question:\n\n{question}\n\n")
            file.write(f"Chain of Reasoning:\n\n{chain_of_reasoning}\n\n")
            file.write(f"Answer:\n\n{answer}\n\n")
            file.write("------------\n\n")
            file.write("Raw Content:\n\n")
            file.write(self.paper_content)

        self.log_file_operation("inference", inference_file_path)

    def write_to_training_file(
        self, question: str, chain_of_reasoning: str, answer: str
    ) -> None:
        """
        Write extracted information to a separate training file for each paper.

        :param question: Extracted question
        :param chain_of_reasoning: Extracted chain of reasoning
        :param answer: Extracted answer
        """
        basename = self.get_file_basename()
        training_file_path = (
            Path(self.training_results_directory) / f"{basename}-training-data.jsonl"
        )

        training_data = {
            "system": SYSTEM_MESSAGE,
            "user": question,
            "assistant": f"{chain_of_reasoning}\n\nAnswer: {answer}",
        }
        with open(training_file_path, "w") as file:
            file.write(json.dumps(training_data) + "\n")

        self.log_file_operation("training", training_file_path)

    def log_file_operation(self, operation_type: str, file_path: Path) -> None:
        """
        Log file operations.

        :param operation_type: Type of operation (e.g., "inference", "training")
        :param file_path: Path to the file
        """
        print(f"Saved {operation_type} data to {file_path}")
        self.logger.debug(f"Wrote {operation_type} data to {file_path}")

    def update_database_status(self, status: str) -> None:
        """
        Update the processing status of the paper in the database.

        :param status: New status to set
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE papers SET processing_status = ? WHERE id = ?",
                (status, self.paper_id),
            )
            conn.commit()
            print(f"Updated paper {self.paper_url} status to {status}")
            self.logger.debug(
                f"Updated database status for paper {self.paper_id} to '{status}'"
            )
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def run(self) -> None:
        """Execute the main logic of the CoT extraction process."""
        self.make_results_directories()
        xml_content = self.extract_xml()
        if not xml_content:
            message = "Could not extract XML content from paper_content"
            self.logger.error(message)
            raise ValueError(message)
        question, chain_of_reasoning, answer = self.parse_xml(xml_content)
        self.write_to_inference_file(question, chain_of_reasoning, answer)
        self.write_to_training_file(question, chain_of_reasoning, answer)
        self.update_database_status("cot_extracted")
        self.logger.info("CoT extraction process completed successfully")


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    extractor = CoTExtractor(
        extraction_preset=args.extraction_preset,
        database=args.database,
        paper_id=args.paper_id,
        paper_url=args.paper_url,
        paper_content=args.paper_content,
        training_file=args.training_file,
        inference_results_directory=args.inference_results_directory,
        training_results_directory=args.training_results_directory,
        debug=args.debug,
    )
    extractor.run()


if __name__ == "__main__":
    main()
