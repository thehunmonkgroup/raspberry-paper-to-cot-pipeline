#!/usr/bin/env python3

"""
This script profiles papers based on a set of rubric questions.
It fetches papers from a database, downloads PDFs, extracts text,
profiles the papers, and updates the results in the database.
"""

import argparse
import copy
import xml.etree.ElementTree as ET
from typing import Dict, Any
import sys
from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Profile papers based on a set of rubric questions."
    )
    parser.add_argument(
        "--profiling-preset",
        type=str,
        default=constants.DEFAULT_LWE_PRESET,
        help="Model configuration used to perform the profiling, default: %(default)s",
    )
    parser.add_argument("--database", type=str, default=constants.DEFAULT_DB_NAME, help="Path to the SQLite database, default: %(default)s")
    parser.add_argument(
        "--inference-artifacts-directory", type=str, default=constants.DEFAULT_INFERENCE_ARTIFACTS_DIR, help="Directory for inference artifacts, default: %(default)s"
    )
    parser.add_argument(
        "--limit", type=int, default=1, help="Number of papers to process, default: %(default)s"
    )
    parser.add_argument(
        "--order_by", type=str, default="RANDOM()", help="Order of paper selection, default: %(default)s"
    )
    parser.add_argument(
        "--pdf-cache-dir", type=str, default=constants.DEFAULT_PDF_CACHE_DIR, help="PDF cache directory, default: %(default)s"
    )
    parser.add_argument(
        "--template", type=str, default=constants.DEFAULT_PAPER_PROFILER_TEMPLATE, help="LWE paper profiler template name, default: %(default)s"
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
        inference_artifacts_directory: str,
        limit: int,
        order_by: str,
        pdf_cache_dir: str,
        template: str,
        debug: bool,
    ):
        """
        Initialize the PaperProfiler with individual arguments.

        :param profiling_preset: Model configuration used to perform the profiling
        :param database: Path to the SQLite database
        :param inference_artifacts_directory: Directory for inference artifacts
        :param limit: Number of papers to process
        :param order_by: Order of paper selection
        :param pdf_cache_dir: PDF cache directory
        :param template: LWE paper profiler template name
        :param debug: Enable debug logging
        """
        self.profiling_preset = profiling_preset
        self.database = database
        self.inference_artifacts_directory = inference_artifacts_directory
        self.limit = limit
        self.order_by = order_by
        self.pdf_cache_dir = pdf_cache_dir
        self.template = template
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)
        self.utils = Utils(database=self.database,
                           inference_artifacts_directory=self.inference_artifacts_directory,
                           pdf_cache_dir=self.pdf_cache_dir,
                           lwe_default_preset=self.profiling_preset,
                           logger=self.logger,
                           )
        self.utils.setup_lwe()

    def run_lwe_template(self, paper_content: str) -> str:
        """
        Run the LWE template with the paper content.

        :param paper_content: Extracted text content of the paper
        :return: Response on success
        :raises RuntimeError: If LWE template execution fails
        """
        template_vars = {"paper": paper_content}
        return self.utils.run_lwe_template(self.template, template_vars)

    def parse_xml(self, xml_string: str) -> Dict[str, int]:
        """
        Parse the XML string to extract criteria values.

        :param xml_string: XML string to parse
        :return: Dictionary of criteria and their values
        :raises ValueError: If a required question is not found in the XML
        """
        root = ET.fromstring(xml_string)
        criteria = {}
        for question in constants.PROFILING_CRITERIA:
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
        for question in constants.PROFILING_CRITERIA:
            answer = "Yes" if criteria[f"criteria_{question}"] == 1 else "No"
            output.append(f"  {question}: {answer}")
        return "\n".join(output)

    def write_inference_artifact(
        self, paper: Dict[str, Any], criteria: Dict[str, int], xml_content: str
    ) -> None:
        """
        Write inference artifact to a file.

        :param paper: Paper data
        :param criteria: Dictionary of criteria and their values
        :param xml_content: Raw XML content
        """
        artifact_name = f"{paper['paper_id']}-paper-profiling.txt"
        content = f"""Paper URL: {paper['paper_url']}
Profiling preset: {self.profiling_preset}

Profiling results:

{self.get_pretty_printed_rubric_questions(criteria)}

----------------------

Raw Inference Output:

{xml_content}
"""
        self.utils.write_inference_artifact(artifact_name, content)

    def process_paper(self, paper: Dict[str, Any]) -> None:
        """
        Process a single paper.

        :param paper: Paper data
        """
        try:
            text = self.utils.get_pdf_text(paper)
            lwe_response = self.run_lwe_template(text)
            xml_content = self.utils.extract_xml(lwe_response)
            if not xml_content:
                raise ValueError("Could not extract XML content from LWE response")
            criteria = self.parse_xml(xml_content)
            self.write_inference_artifact(paper, criteria, xml_content)
            data = copy.deepcopy(criteria)
            data['processing_status'] = constants.STATUS_PROFILED
            self.utils.update_paper(paper['id'], data)
            self.logger.info(f"Successfully profiled paper {paper['paper_id']}")
        except Exception as e:
            self.logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
            self.utils.update_paper_status(paper['id'], 'failed_profiling')

    def run(self) -> None:
        """Execute the main logic of the paper profiling process."""
        try:
            papers = self.utils.fetch_papers_by_processing_status(status=constants.STATUS_VERIFIED, order_by=self.order_by, limit=self.limit)
            for paper in papers:
                self.process_paper(paper)
            self.logger.info("Paper profiling process completed")
        except Exception as e:
            self.logger.error(f"An error occurred during the paper profiling process: {e}")
            sys.exit(1)


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    profiler = PaperProfiler(
        profiling_preset=args.profiling_preset,
        database=args.database,
        inference_artifacts_directory=args.inference_artifacts_directory,
        limit=args.limit,
        order_by=args.order_by,
        pdf_cache_dir=args.pdf_cache_dir,
        template=args.template,
        debug=args.debug,
    )
    profiler.run()


if __name__ == "__main__":
    main()
