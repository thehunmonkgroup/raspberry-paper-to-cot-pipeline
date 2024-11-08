#!/usr/bin/env python3

"""
Pipeline script that orchestrates the full paper processing workflow:
profiling → scoring → CoT extraction.
"""

import argparse
import sys
from typing import Optional

from raspberry_paper_to_cot_pipeline.paper_profiler import PaperProfiler
from raspberry_paper_to_cot_pipeline.paper_scorer import PaperScorer
from raspberry_paper_to_cot_pipeline.paper_extract_cot import CoTExtractor
from raspberry_paper_to_cot_pipeline.utils import Utils


class PaperCoTPipeline:
    """Orchestrates the full paper processing pipeline."""

    def __init__(self, limit: Optional[int], debug: bool = False):
        """
        Initialize the pipeline.

        :param limit: Number of papers to process in each stage
        :param debug: Enable debug logging
        """
        self.limit = limit
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, debug)

    def run(self) -> None:
        """Execute the full pipeline sequence."""
        try:
            # Stage 1: Profile papers
            self.logger.info("Starting paper profiling stage...")
            profiler = PaperProfiler(
                limit=self.limit,
                debug=self.debug,
            )
            profiler.run()

            # Stage 2: Score papers
            self.logger.info("Starting paper scoring stage...")
            scorer = PaperScorer(
                limit=self.limit,
                debug=self.debug,
            )
            scorer.run()

            # Stage 3: Extract CoT
            self.logger.info("Starting CoT extraction stage...")
            extractor = CoTExtractor(
                limit=self.limit,
                debug=self.debug,
            )
            extractor.run()

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
        "--limit",
        type=int,
        default=1,
        help="Number of papers to process in each stage, default: %(default)s"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    pipeline = PaperCoTPipeline(limit=args.limit, debug=args.debug)
    pipeline.run()


if __name__ == "__main__":
    main()
