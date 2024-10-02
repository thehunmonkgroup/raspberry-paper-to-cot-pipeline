#!/usr/bin/env python3

"""
This script profiles papers based on a set of rubric questions.
It extracts XML content, parses it, and writes the results to inference files and updates the database.
"""

import argparse
import re
import xml.etree.ElementTree as ET
import sqlite3
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Optional

# Define the rubric questions as a constant list
QUESTIONS = [
    "clear_question",
    "definitive_answer",
    "complex_reasoning",
    "coherent_structure",
    "layperson_comprehensible",
    "minimal_jargon",
    "illustrative_examples",
    "significant_insights",
    "verifiable_steps",
    "overall_suitability",
]


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Profile papers based on a set of rubric questions."
    )
    parser.add_argument(
        "profiling_preset",
        type=str,
        help="Model configuration used to perform the profiling",
    )
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument("paper_content", type=str, help="Content to be profiled")
    parser.add_argument(
        "inference_results_directory", type=str, help="Directory for inference results"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


class PaperProfiler:
    """
    A class to handle paper profiling based on rubric questions.
    """

    def __init__(
        self,
        profiling_preset: str,
        database: str,
        paper_id: str,
        paper_url: str,
        paper_content: str,
        inference_results_directory: str,
        debug: bool,
    ):
        """
        Initialize the PaperProfiler with individual arguments.

        :param profiling_preset: Model configuration used to perform the profiling
        :param database: Path to the SQLite database
        :param paper_id: ID of the paper in the database
        :param paper_url: URL of the paper
        :param paper_content: Content to be profiled
        :param inference_results_directory: Directory for inference results
        :param debug: Enable debug logging
        """
        self.profiling_preset = profiling_preset
        self.database = database
        self.paper_id = paper_id
        self.paper_url = paper_url
        self.paper_content = paper_content
        self.inference_results_directory = inference_results_directory
        self.debug = debug
        self.setup_logging()

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def extract_xml(self) -> Optional[str]:
        """
        Extract XML content from the paper content.

        :return: Extracted XML content or None if not found
        """
        match = re.search(
            r"<results>(?:(?!</results>).)*</results>", self.paper_content, re.DOTALL
        )
        return match.group(0) if match else None

    def parse_xml(self, xml_string: str) -> Dict[str, int]:
        """
        Parse the XML string to extract criteria values.

        :param xml_string: XML string to parse
        :return: Dictionary of criteria and their values
        """
        root = ET.fromstring(xml_string)
        criteria = {}
        for question in QUESTIONS:
            element = root.find(f".//{question}")
            if element is not None:
                value = element.text.strip()
                criteria[f"criteria_{question}"] = (
                    1 if value.lower() in ["yes", "y"] else 0
                )
            else:
                raise ValueError(f"{question} not found in XML")
        return criteria

    def get_pretty_printed_rubric_questions(self, criteria: Dict[str, int]) -> str:
        """
        Get a pretty-printed string of rubric questions and answers.

        :param criteria: Dictionary of criteria and their values
        :return: Pretty-printed string of questions and answers
        """
        output = []
        for question in QUESTIONS:
            answer = "Yes" if criteria[f"criteria_{question}"] == 1 else "No"
            output.append(f"  {question}: {answer}")
        return "\n".join(output)

    def update_database(self, criteria: Dict[str, int]) -> None:
        """
        Update the processing status and criteria of the paper in the database.

        :param criteria: Dictionary of criteria and their values
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()

            update_fields = ", ".join(
                [f"criteria_{question} = ?" for question in QUESTIONS]
            )
            update_query = f"""
            UPDATE papers SET
                processing_status = 'profiled',
                {update_fields}
            WHERE id = ?
            """

            update_values = tuple(
                criteria[f"criteria_{question}"] for question in QUESTIONS
            )

            cursor.execute(update_query, (*update_values, self.paper_id))
            conn.commit()

            print(f"Updated profiling results for paper {self.paper_url}")
            print("Questions and answers:")
            print(self.get_pretty_printed_rubric_questions(criteria))
            self.logger.debug(f"Updated database for paper {self.paper_id}")
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def write_inference_artifact(
        self, criteria: Dict[str, int], xml_content: str
    ) -> None:
        """
        Write inference artifact to a file.

        :param criteria: Dictionary of criteria and their values
        :param xml_content: Raw XML content
        """
        parsed_url = urlparse(self.paper_url)
        basename = Path(parsed_url.path).stem
        inference_file_path = (
            Path(self.inference_results_directory) / f"{basename}-paper-profiling.txt"
        )

        with open(inference_file_path, "w") as file:
            file.write(f"Paper URL: {self.paper_url}\n")
            file.write(f"Profiling preset: {self.profiling_preset}\n\n")
            file.write("Profiling results:\n\n")
            file.write(self.get_pretty_printed_rubric_questions(criteria))
            file.write("\n\n----------------------\n\n")
            file.write("Raw Inference Output:\n\n")
            file.write(xml_content)

        print(f"Saved inference results to {inference_file_path}")
        self.logger.debug(f"Wrote inference results to {inference_file_path}")

    def run(self) -> None:
        """Execute the main logic of the paper profiling process."""
        xml_content = self.extract_xml()
        if not xml_content:
            message = "Could not extract XML content from paper_content"
            self.logger.error(message)
            raise ValueError(message)
        criteria = self.parse_xml(xml_content)
        self.write_inference_artifact(criteria, xml_content)
        self.update_database(criteria)
        self.logger.info("Paper profiling process completed successfully")


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    profiler = PaperProfiler(
        profiling_preset=args.profiling_preset,
        database=args.database,
        paper_id=args.paper_id,
        paper_url=args.paper_url,
        paper_content=args.paper_content,
        inference_results_directory=args.inference_results_directory,
        debug=args.debug,
    )
    profiler.run()


if __name__ == "__main__":
    main()
