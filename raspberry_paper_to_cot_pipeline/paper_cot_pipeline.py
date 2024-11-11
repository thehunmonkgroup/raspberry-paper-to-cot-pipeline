#!/usr/bin/env python3

"""
Pipeline script that orchestrates the full paper processing workflow:
profiling → scoring → CoT extraction.
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
    """Orchestrates the full paper processing pipeline."""

    def __init__(
        self,
        selection_strategy: Literal["random", "category_balanced"] = "random",
        limit: int = 1,
        debug: bool = False,
    ) -> None:
        """
        Initialize the pipeline.

        :param selection_strategy: Strategy for paper selection in profiling stage
        :param limit: Number of papers to process in each stage
        :param debug: Enable debug logging
        """
        self.limit = limit
        self.selection_strategy = selection_strategy
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, debug)

    def run(self) -> None:
        """Execute the full pipeline sequence."""
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
    """Parse command line arguments."""
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
    """Main entry point."""
    args = parse_arguments()
    pipeline = PaperCoTPipeline(
        selection_strategy=args.selection_strategy, limit=args.limit, debug=args.debug
    )
    pipeline.run()


if __name__ == "__main__":
    main()
