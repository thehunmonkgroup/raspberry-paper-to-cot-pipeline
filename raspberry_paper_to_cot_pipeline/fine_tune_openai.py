#!/usr/bin/env python3
"""
This script handles fine-tuning of an OpenAI model using specified training and validation files.
It uploads the provided training and validation files to the OpenAI API and starts a fine-tuning job.
"""

import sys
import argparse
from pathlib import Path
from openai import OpenAI
from openai.types.fine_tuning import job_create_params
from typing import Any, Tuple

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils

DEFAULT_HYPERPARAMETERS: job_create_params.Hyperparameters = {
    "batch_size": constants.DEFAULT_OPENAI_FINE_TUNING_BATCH_SIZE,
    "learning_rate_multiplier": constants.DEFAULT_OPENAI_FINE_TUNING_LEARNING_RATE_MULTIPLIER,
    "n_epochs": constants.DEFAULT_OPENAI_FINE_TUNING_N_EPOCHS,
}


class OpenAIFineTuner:
    """
    Handles uploading training files and initiating an OpenAI fine-tuning job.

    :param training_file: Path to the training file.
    :type training_file: Path
    :param validation_file: Path to the validation file.
    :type validation_file: Path
    :param model: Model identifier for fine-tuning.
    :type model: str
    :param hyperparameters: Dictionary of hyperparameters for fine-tuning.
    :type hyperparameters: job_create_params.Hyperparameters
    :param debug: Enable debug logging.
    :type debug: bool
    """

    def __init__(
        self,
        training_file: Path,
        validation_file: Path,
        model: str = constants.DEFAULT_OPENAI_FINE_TUNING_MODEL,
        hyperparameters: job_create_params.Hyperparameters = DEFAULT_HYPERPARAMETERS,
        debug: bool = False,
    ) -> None:
        self.training_file = training_file
        self.validation_file = validation_file
        self.model = model
        self.hyperparameters = hyperparameters
        self.debug = debug
        self.client = OpenAI()
        self.logger = Utils.setup_logging(__name__, self.debug)

    def upload_training_files(self) -> Tuple[Any, Any]:
        """
        Uploads the training and validation files to OpenAI.

        :return: Tuple containing the training and validation file objects.
        """
        self.logger.info(f"Uploading training file from {self.training_file}")
        training_file_obj = self.client.files.create(
            file=open(self.training_file, "rb"), purpose="fine-tune"
        )
        self.logger.info(f"Uploading validation file from {self.validation_file}")
        validation_file_obj = self.client.files.create(
            file=open(self.validation_file, "rb"), purpose="fine-tune"
        )
        self.logger.info(f"Training file Info: {training_file_obj}")
        self.logger.info(f"Validation file Info: {validation_file_obj}")
        return training_file_obj, validation_file_obj

    def fine_tune_model(self, training_file_obj: Any, validation_file_obj: Any) -> Any:
        """
        Initiates a fine-tuning job with the uploaded training and validation files.
        :param training_file_obj: Training file object.
        :param validation_file_obj: Validation file object.
        :return: Fine-tuning job object.
        """
        self.logger.info("Starting fine-tuning job")
        job = self.client.fine_tuning.jobs.create(
            training_file=training_file_obj.id,
            validation_file=validation_file_obj.id,
            model=self.model,
            hyperparameters=self.hyperparameters,
        )
        self.logger.info(
            f"Fine-tuning model {self.model}, hyperparameters: {self.hyperparameters}"
        )
        self.logger.info(f"Training Job ID: {job.id}")
        self.logger.info(f"Training Response: {job}")
        self.logger.info(f"Training Status: {job.status}")
        self.logger.info(
            f"Job link: {constants.DEFAULT_OPENAI_PLATFORM_BASE_URL}/finetune/{job.id}"
        )
        return job

    def run(self) -> Any:
        """
        Runs the fine-tuning process: upload files and start fine-tuning.
        :return: Fine-tuning job object.
        """
        training_file_obj, validation_file_obj = self.upload_training_files()
        job = self.fine_tune_model(training_file_obj, validation_file_obj)
        return job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune an OpenAI model using training and validation files."
    )
    parser.add_argument("training_file", type=Path, help="Path to the training file.")
    parser.add_argument(
        "validation_file", type=Path, help="Path to the validation file."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=constants.DEFAULT_OPENAI_FINE_TUNING_MODEL,
        help="Model identifier for fine-tuning. Default: %(default)s",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=constants.DEFAULT_OPENAI_FINE_TUNING_BATCH_SIZE,
        help="Batch size. Default: %(default)s",
    )
    parser.add_argument(
        "--learning-rate-multiplier",
        type=float,
        default=constants.DEFAULT_OPENAI_FINE_TUNING_LEARNING_RATE_MULTIPLIER,
        help="Learning rate multiplier. Default: %(default)s",
    )
    parser.add_argument(
        "--n-epochs",
        type=int,
        default=constants.DEFAULT_OPENAI_FINE_TUNING_N_EPOCHS,
        help="Number of epochs. Default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    args.hyperparameters = {
        "batch_size": args.batch_size,
        "learning_rate_multiplier": args.learning_rate_multiplier,
        "n_epochs": args.n_epochs,
    }
    return args


def main() -> None:
    args = parse_args()
    tuner = OpenAIFineTuner(
        training_file=args.training_file,
        validation_file=args.validation_file,
        model=args.model,
        hyperparameters=args.hyperparameters,
        debug=args.debug,
    )
    try:
        tuner.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
