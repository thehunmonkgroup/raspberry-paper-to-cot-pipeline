#!/usr/bin/env python3

import os
import argparse
import random
import string
import json


def parse_args():
    parser = argparse.ArgumentParser(description="Process training and inference files.")
    parser.add_argument("training_file", type=str, help="Path to the training file")
    parser.add_argument("inference_results_directory", type=str, help="Directory for inference results")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument("paper_content", type=str, help="Content to be written and logged")
    args = parser.parse_args()
    return args


def make_inference_results_directory(args):
    if not os.path.exists(args.inference_results_directory):
        os.makedirs(args.inference_results_directory)


def write_to_inference_file(args):
    random_identifier = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    inference_file_path = os.path.join(args.inference_results_directory, f"inference_result_{random_identifier}.txt")
    with open(inference_file_path, 'w') as file:
        file.write(args.paper_url + "\n\n" + args.paper_content)


def write_to_training_file(args):
    training_data = {"url": args.paper_url, "data": args.paper_content}
    with open(args.training_file, 'a') as file:
        file.write(json.dumps(training_data) + "\n")

def main():
    args = parse_args()
    make_inference_results_directory(args)
    write_to_inference_file(args)
    write_to_training_file(args)


if __name__ == "__main__":
    main()
