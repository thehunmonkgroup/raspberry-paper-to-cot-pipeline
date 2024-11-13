#!/usr/bin/env python3

"""
Pipeline script for orchestrating the complete paper processing workflow.

This module implements a multi-stage pipeline that processes research papers through
several stages: profiling, scoring, Chain of Thought (CoT) extraction, quality
assessment, and training data generation. Each stage builds upon the results of
the previous stage to create a comprehensive paper analysis pipeline.
"""

import argparse
import sys
from typing import Literal

from raspberry_paper_to_cot_pipeline.paper_profiler import PaperProfiler
from raspberry_paper_to_cot_pipeline.paper_profile_scorer import PaperProfileScorer
from raspberry_paper_to_cot_pipeline.paper_cot_extractor import CoTExtractor
from raspberry_paper_to_cot_pipeline.cot_quality_assessor import CoTQualityAssessor
from raspberry_paper_to_cot_pipeline.cot_quality_scorer import CoTQualityScorer
from raspberry_paper_to_cot_pipeline.generate_training_data import TrainingDataGenerator
from raspberry_paper_to_cot_pipeline.utils import Utils


class PaperCoTPipeline:
    """
    Orchestrates the complete paper processing pipeline.

    This class manages the execution of multiple processing stages for research papers,
    including profiling, scoring, CoT extraction, quality assessment, and training
    data generation. It handles the flow control and error management between stages.

    :param selection_strategy: Strategy for selecting papers in the profiling stage
    :type selection_strategy: Literal["random", "category_balanced"]
    :param limit: Maximum number of papers to process in each stage
    :type limit: int
    :param debug: Flag to enable debug logging
    :type debug: bool
    """

    def __init__(
        self,
        selection_strategy: Literal["random", "category_balanced"] = "random",
        limit: int = 1,
        debug: bool = False,
    ) -> None:
        """
        Initialize the pipeline with specified configuration.

        :param selection_strategy: Strategy for paper selection in profiling stage
        :type selection_strategy: Literal["random", "category_balanced"]
        :param limit: Number of papers to process in each stage
        :type limit: int
        :param debug: Enable debug logging
        :type debug: bool
        :return: None
        :rtype: None
        """
        self.limit = limit
        self.selection_strategy = selection_strategy
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, debug)

    def run(self) -> None:
        """
        Execute the complete pipeline sequence.

        Runs all pipeline stages in sequence: paper profiling, profile scoring,
        CoT extraction, quality assessment, quality scoring, and training data
        generation. Handles errors and logging for each stage.

        :return: None
        :rtype: None
        :raises Exception: If any pipeline stage fails
        """
        try:
            # Stage 1: Profile papers
            self.logger.info("Starting paper profiling stage...")
            profiler = PaperProfiler(
                limit=self.limit,
                selection_strategy=self.selection_strategy,
                debug=self.debug,
            )
            profiler.run()

            # Stage 2: Score papers
            self.logger.info("Starting paper scoring stage...")
            scorer = PaperProfileScorer(
                limit=None,
                debug=self.debug,
            )
            scorer.run()

            # Stage 3: Extract CoT
            self.logger.info("Starting CoT extraction stage...")
            extractor = CoTExtractor(
                limit=None,
                debug=self.debug,
            )
            extractor.run()

            # Stage 4: CoT quality assessment
            self.logger.info("Starting CoT quality assessment stage...")
            assessor = CoTQualityAssessor(
                limit=None,
                debug=self.debug,
            )
            assessor.run()

            # Stage 5: CoT quality scoring
            self.logger.info("Starting CoT quality scoring stage...")
            scorer = CoTQualityScorer(
                limit=None,
                debug=self.debug,
            )
            scorer.run()

            # Stage 6: Generate training data
            self.logger.info("Starting training data generation stage...")
            generator = TrainingDataGenerator(
                limit=None,
                debug=self.debug,
            )
            generator.run()

            self.logger.info("Pipeline completed successfully")

        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for pipeline configuration.

    Defines and processes command line arguments for configuring the pipeline,
    including selection strategy, processing limits, and debug options.

    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Run the complete paper processing pipeline."
    )
    parser.add_argument(
        "--selection-strategy",
        type=str,
        choices=["random", "category_balanced"],
        default="random",
        help="Strategy for paper selection in profiling stage: 'random' or 'category_balanced', default: %(default)s",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of papers to process in each stage, default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main():
    """
    Main entry point for the pipeline execution.

    Initializes and runs the paper processing pipeline with command line arguments.
    Handles command line argument parsing and pipeline initialization.

    :return: None
    :rtype: None
    :raises SystemExit: If the pipeline execution fails
    """
    args = parse_arguments()
    pipeline = PaperCoTPipeline(
        selection_strategy=args.selection_strategy, limit=args.limit, debug=args.debug
    )
    pipeline.run()


if __name__ == "__main__":
    main()
