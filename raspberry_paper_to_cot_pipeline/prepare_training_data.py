#!/usr/bin/env python3
"""
This script prepares training data from a JSONL file by converting samples into
the OpenAI chat messages format and splitting them into training and test sets.
:raises Exception: If processing fails.
"""
import sys
import argparse
from pathlib import Path
import pandas as pd
from datasets import Dataset

from raspberry_paper_to_cot_pipeline import constants
from raspberry_paper_to_cot_pipeline.utils import Utils


class TrainingDataPreparer:
    """
    Handles the preparation of training data from a JSONL file by converting raw samples
    to OpenAI chat message format and splitting them into training and test sets.
    :param input_file: Path to the input JSONL file.
    :type input_file: Path
    :param output_dir: Directory where output files will be saved.
    :type output_dir: Path
    :param training_file: Name of the output training file.
    :type training_file: str
    :param validation_file: Name of the output validation file.
    :type validation_file: str
    :param debug: Enable debug logging, defaults to False.
    :type debug: bool
    """

    def __init__(
        self,
        input_file: Path,
        output_dir: Path,
        training_file: str,
        validation_file: str,
        debug: bool = False,
    ) -> None:
        self.input_file = input_file
        self.output_dir = output_dir
        self.training_file = training_file
        self.validation_file = validation_file
        self.debug = debug
        self.logger = Utils.setup_logging(__name__, self.debug)

    def load_data(self) -> pd.DataFrame:
        """Loads the JSONL data from the input file.
        :return: DataFrame containing the input data.
        :rtype: pd.DataFrame
        :raises: Exception if file reading fails.
        """
        try:
            self.logger.info(f"Loading data from {self.input_file}")
            return pd.read_json(self.input_file, lines=True)
        except Exception as e:
            self.logger.error(f"Failed to read input file {self.input_file}: {e}")
            raise

    def convert_sample_to_openai_format(self, row: pd.Series) -> dict:
        """Converts a row of data to OpenAI chat message format.
        :param row: A row from the DataFrame.
        :type row: pd.Series
        :return: Dictionary with OpenAI formatted messages.
        :rtype: dict
        """
        messages = []
        if row.get("system"):
            messages.append({"role": "system", "content": row["system"]})
        if row.get("user"):
            messages.append({"role": "user", "content": row["user"]})
        if row.get("assistant"):
            messages.append({"role": "assistant", "content": row["assistant"]})
        return {"messages": messages}

    def convert_data_to_openai_format(self, df: pd.DataFrame) -> list:
        """Applies conversion to all rows in the DataFrame.
        :param df: Input DataFrame.
        :type df: pd.DataFrame
        :return: List of dictionaries formatted for OpenAI.
        :rtype: list
        """
        self.logger.info("Converting data to OpenAI format")
        return df.apply(self.convert_sample_to_openai_format, axis=1).tolist()

    def create_train_test_split(self, data: list) -> dict:
        """Splits the data into training and test sets.
        :param data: List of data samples.
        :type data: list
        :return: Dictionary with 'train' and 'test' keys containing the split datasets.
        :rtype: dict
        """
        self.logger.info("Splitting data into train and test sets")
        dataset = Dataset.from_list(data)
        return dataset.train_test_split(test_size=0.2, seed=42)

    def write_files(self, split_dataset: dict) -> None:
        """Writes the training and test datasets to JSONL files.
        :param split_dataset: Dictionary containing dataset splits.
        :type split_dataset: dict
        :raises: Exception if file writing fails.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(
                f"Writing files {self.training_file}/{self.validation_file} to {self.output_dir}"
            )
            split_dataset["train"].to_json(
                str(self.output_dir / self.training_file), orient="records", lines=True
            )
            split_dataset["test"].to_json(
                str(self.output_dir / self.validation_file),
                orient="records",
                lines=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to write output files: {e}")
            raise

    def run(self) -> None:
        """Executes the training data preparation pipeline."""
        df = self.load_data()
        converted = self.convert_data_to_openai_format(df)
        split_dataset = self.create_train_test_split(converted)
        self.write_files(split_dataset)
        self.logger.info("Conversion complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare training data from a JSONL file."
    )
    parser.add_argument("input_file", type=Path, help="Path to the input JSONL file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=constants.DEFAULT_TRAINING_ARTIFACTS_DIR,
        help="Directory to save the training/validation JSONL files default: %(default)s",
    )
    parser.add_argument(
        "--training-file",
        type=Path,
        default=constants.DEFAULT_TRAINING_FILE,
        help="Name of the training JSONL file default: %(default)s",
    )
    parser.add_argument(
        "--validation-file",
        type=Path,
        default=constants.DEFAULT_VALIDATION_FILE,
        help="Name of the validation JSONL file default: %(default)s",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    preparer = TrainingDataPreparer(
        args.input_file,
        args.output_dir,
        args.training_file,
        args.validation_file,
        args.debug,
    )
    try:
        preparer.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
