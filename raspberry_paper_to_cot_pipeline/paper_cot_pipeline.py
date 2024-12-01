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
from contextlib import contextmanager
from datetime import datetime

from raspberry_paper_to_cot_pipeline.paper_profiler import PaperProfiler
from raspberry_paper_to_cot_pipeline.paper_profile_scorer import PaperProfileScorer
from raspberry_paper_to_cot_pipeline.paper_cot_extractor import CoTExtractor
from raspberry_paper_to_cot_pipeline.cot_quality_assessor import CoTQualityAssessor
from raspberry_paper_to_cot_pipeline.cot_quality_scorer import CoTQualityScorer
from raspberry_paper_to_cot_pipeline.cot_voicing import CoTVoicing
from raspberry_paper_to_cot_pipeline.cot_voicing_assessor import CoTVoicingAssessor
from raspberry_paper_to_cot_pipeline.cot_voicing_scorer import CoTVoicingScorer
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
        self.utils = Utils()
        self.stage_timings = {}

    @contextmanager
    def _time_stage(self, stage_name: str):
        """Context manager to time pipeline stages.
        
        :param stage_name: Name of the pipeline stage
        :type stage_name: str
        """
        start_time = datetime.now()
        try:
            yield
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            self.stage_timings[stage_name] = duration

    def run(self) -> None:
        """
        Execute the complete pipeline sequence.

        Runs all pipeline stages in sequence: paper profiling, profile scoring,
        CoT extraction, quality assessment, quality scoring, and training data
        generation. Handles errors and logging for each stage.

        :return: None
        :rtype: None
        """
        pipeline_start = datetime.now()
        try:
            # Stage 1: Profile papers
            with self._time_stage("Paper Profiling"):
                self.logger.info("Starting paper profiling stage...")
                profiler = PaperProfiler(
                    limit=self.limit,
                    selection_strategy=self.selection_strategy,
                    debug=self.debug,
                )
                profiler.run()

            # Stage 2: Score papers
            with self._time_stage("Paper Scoring"):
                self.logger.info("Starting paper scoring stage...")
                profiler_scorer = PaperProfileScorer(
                    limit=None,
                    debug=self.debug,
                )
                profiler_scorer.run()

            # Stage 3: Extract CoT
            with self._time_stage("CoT Extraction"):
                self.logger.info("Starting CoT extraction stage...")
                extractor = CoTExtractor(
                    limit=None,
                    debug=self.debug,
                )
                extractor.run()

            # Stage 4: CoT quality assessment
            with self._time_stage("CoT Quality Assessment"):
                self.logger.info("Starting CoT quality assessment stage...")
                cot_quality_assessor = CoTQualityAssessor(
                    limit=None,
                    debug=self.debug,
                )
                cot_quality_assessor.run()

            # Stage 5: CoT quality scoring
            with self._time_stage("CoT Quality Scoring"):
                self.logger.info("Starting CoT quality scoring stage...")
                cot_quality_scorer = CoTQualityScorer(
                    limit=None,
                    debug=self.debug,
                )
                cot_quality_scorer.run()

            # Stage 6: Transform CoT into correct voice
            with self._time_stage("CoT Voice Transformation"):
                voicer = CoTVoicing(
                    limit=None,
                    debug=self.debug,
                )
                voicer.run()

            # Stage 7: CoT voicing assessment
            with self._time_stage("CoT Voice Assessment"):
                self.logger.info("Starting CoT voicing assessment stage...")
                cot_voicing_assessor = CoTVoicingAssessor(
                    limit=None,
                    debug=self.debug,
                )
                cot_voicing_assessor.run()

            # Stage 8: CoT voicing scoring
            with self._time_stage("CoT Voice Scoring"):
                self.logger.info("Starting CoT voicing scoring stage...")
                cot_voicing_scorer = CoTVoicingScorer(
                    limit=None,
                    debug=self.debug,
                )
                cot_voicing_scorer.run()

            # Stage 9: Generate training data
            with self._time_stage("Training Data Generation"):
                self.logger.info("Starting training data generation stage...")
                generator = TrainingDataGenerator(
                    limit=None,
                    debug=self.debug,
                )
                generator.run()

            pipeline_duration = (datetime.now() - pipeline_start).total_seconds()
            
            # Log timing summary
            self.logger.info("\nPipeline Timing Summary:")
            for stage, duration in self.stage_timings.items():
                self.logger.info(f"{stage}: {self.utils.format_duration(duration)}")
            self.logger.info(f"\nTotal Pipeline Duration: {self.utils.format_duration(pipeline_duration)}")
            
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
    """
    args = parse_arguments()
    pipeline = PaperCoTPipeline(
        selection_strategy=args.selection_strategy, limit=args.limit, debug=args.debug
    )
    pipeline.run()


if __name__ == "__main__":
    main()
