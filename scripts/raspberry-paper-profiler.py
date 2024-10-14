#!/usr/bin/env python3

"""
This script profiles papers based on a set of rubric questions.
It fetches papers from a database, downloads PDFs, extracts text,
profiles the papers, and updates the results in the database.
"""

import argparse
import re
import xml.etree.ElementTree as ET
import sqlite3
import logging
import os
import requests
import pymupdf4llm
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Optional, List, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from lwe.core.config import Config
from lwe import ApiBackend

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
    parser.add_argument(
        "inference_results_directory", type=str, help="Directory for inference results"
    )
    parser.add_argument(
        "--limit", type=int, default=1, help="Number of papers to process"
    )
    parser.add_argument(
        "--order_by", type=str, default="RANDOM()", help="Order of paper selection"
    )
    parser.add_argument(
        "--tmp_pdf_path", type=str, default="/tmp/raspberry-tmp-pdf.pdf", help="Temporary PDF storage path"
    )
    parser.add_argument(
        "--template", type=str, default="raspberry-paper-profiler.md", help="LWE template name"
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
        inference_results_directory: str,
        limit: int,
        order_by: str,
        tmp_pdf_path: str,
        template: str,
        debug: bool,
    ):
        """
        Initialize the PaperProfiler with individual arguments.

        :param profiling_preset: Model configuration used to perform the profiling
        :param database: Path to the SQLite database
        :param inference_results_directory: Directory for inference results
        :param limit: Number of papers to process
        :param order_by: Order of paper selection
        :param tmp_pdf_path: Temporary PDF storage path
        :param template: LWE template name
        :param debug: Enable debug logging
        """
        self.profiling_preset = profiling_preset
        self.database = database
        self.inference_results_directory = inference_results_directory
        self.limit = limit
        self.order_by = order_by
        self.tmp_pdf_path = tmp_pdf_path
        self.template = template
        self.debug = debug
        self.setup_logging()
        self.setup_lwe()

    def setup_lwe(self) -> None:
        """Set up LWE configuration and API backend."""
        config = Config()
        config.load_from_file()
        config.set("debug.log.enabled", True)
        config.set("model.default_preset", self.profiling_preset)
        self.lwe_backend = ApiBackend(config)
        self.lwe_backend.set_return_only(True)

    def run_lwe_template(self, paper_content: str) -> Tuple[bool, str, str]:
        """
        Run the LWE template with the paper content.

        :param paper_content: Extracted text content of the paper
        :return: Response on success
        """
        template_vars = {"paper": paper_content}

        success, response, user_message = self.lwe_backend.run_template(self.template, template_vars)
        if not success:
            message = f"Error running LWE template: {user_message}"
            self.logger.error(message)
            raise RuntimeError(message)
        return response


    def setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def fetch_papers(self) -> List[Dict[str, str]]:
        """
        Fetch papers from the database.

        :return: List of dictionaries containing paper information
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            query = f"""
            SELECT id, paper_url
            FROM papers
            WHERE processing_status = 'verified'
            ORDER BY {self.order_by}
            LIMIT ?
            """
            cursor.execute(query, (self.limit,))
            papers = [{"id": row[0], "url": row[1]} for row in cursor.fetchall()]
            self.logger.debug(f"Fetched {len(papers)} papers from the database")
            return papers
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def download_pdf(self, url: str) -> None:
        """
        Download PDF from the given URL.

        :param url: URL of the PDF to download
        """
        response = requests.get(url)
        response.raise_for_status()
        with open(self.tmp_pdf_path, 'wb') as f:
            f.write(response.content)
        self.logger.debug(f"Downloaded PDF from {url} to {self.tmp_pdf_path}")

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from the PDF file.

        :param pdf_path: Path to the PDF file
        :return: Extracted text
        """
        self.logger.debug(f"Extracting text from {pdf_path}")
        try:
            return pymupdf4llm.to_markdown(pdf_path)
        except Exception as e:
            message = f"Error extracting {pdf_path} content with pymupdf4llm: {str(e)}"
            self.logger.error(message)

    def extract_xml(self, content: str) -> Optional[str]:
        """
        Extract XML content from the paper content.

        :param content: Paper content
        :return: Extracted XML content or None if not found
        """
        match = re.search(
            r"<results>(?:(?!</results>).)*</results>", content, re.DOTALL
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

    def update_paper_status(self, paper_id: str, status: str, criteria: Optional[Dict[str, int]] = None) -> None:
        """
        Update the processing status and criteria of the paper in the database.

        :param paper_id: ID of the paper
        :param status: New processing status
        :param criteria: Dictionary of criteria and their values (optional)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()

            if criteria:
                update_fields = ", ".join(
                    [f"criteria_{question} = ?" for question in QUESTIONS]
                )
                update_query = f"""
                UPDATE papers SET
                    processing_status = ?,
                    {update_fields}
                WHERE id = ?
                """
                update_values = (status,) + tuple(
                    criteria[f"criteria_{question}"] for question in QUESTIONS
                ) + (paper_id,)
            else:
                update_query = "UPDATE papers SET processing_status = ? WHERE id = ?"
                update_values = (status, paper_id)

            cursor.execute(update_query, update_values)
            conn.commit()

            self.logger.debug(f"Updated status for paper {paper_id} to {status}")
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def write_inference_artifact(
        self, paper_url: str, criteria: Dict[str, int], xml_content: str
    ) -> None:
        """
        Write inference artifact to a file.

        :param paper_url: URL of the paper
        :param criteria: Dictionary of criteria and their values
        :param xml_content: Raw XML content
        """
        parsed_url = urlparse(paper_url)
        basename = Path(parsed_url.path).stem
        inference_file_path = (
            Path(self.inference_results_directory) / f"{basename}-paper-profiling.txt"
        )

        with open(inference_file_path, "w") as file:
            file.write(f"Paper URL: {paper_url}\n")
            file.write(f"Profiling preset: {self.profiling_preset}\n\n")
            file.write("Profiling results:\n\n")
            file.write(self.get_pretty_printed_rubric_questions(criteria))
            file.write("\n\n----------------------\n\n")
            file.write("Raw Inference Output:\n\n")
            file.write(xml_content)

        self.logger.debug(f"Wrote inference results to {inference_file_path}")

    def run(self) -> None:
        """Execute the main logic of the paper profiling process."""
        papers = self.fetch_papers()
        for paper in papers:
            try:
                self.download_pdf(paper['url'])
                text = self.extract_text(self.tmp_pdf_path)
                lwe_response = self.run_lwe_template(text)
                xml_content = self.extract_xml(lwe_response)
                if not xml_content:
                    raise ValueError("Could not extract XML content from LWE response")
                criteria = self.parse_xml(xml_content)
                self.write_inference_artifact(paper['url'], criteria, xml_content)
                self.update_paper_status(paper['id'], 'profiled', criteria)
                self.logger.info(f"Successfully profiled paper {paper['id']}")
            except Exception as e:
                self.logger.error(f"Error processing paper {paper['id']}: {str(e)}")
                self.update_paper_status(paper['id'], 'failed_profiling')
            finally:
                if os.path.exists(self.tmp_pdf_path):
                    os.remove(self.tmp_pdf_path)
        self.logger.info("Paper profiling process completed")


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    profiler = PaperProfiler(
        profiling_preset=args.profiling_preset,
        database=args.database,
        inference_results_directory=args.inference_results_directory,
        limit=args.limit,
        order_by=args.order_by,
        tmp_pdf_path=args.tmp_pdf_path,
        template=args.template,
        debug=args.debug,
    )
    profiler.run()


if __name__ == "__main__":
    main()
