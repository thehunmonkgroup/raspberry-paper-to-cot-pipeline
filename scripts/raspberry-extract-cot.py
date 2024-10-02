#!/usr/bin/env python3

import os
import argparse
import json
import re
import xml.etree.ElementTree as ET
import textwrap
from urllib.parse import urlparse
import sqlite3


def parse_args():
    parser = argparse.ArgumentParser(description="Process training and inference files.")
    parser.add_argument("extraction_preset", type=str, help="Model configuration used to perform the extraction")
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument("paper_content", type=str, help="Content to be written and logged")
    parser.add_argument("training_file", type=str, help="Path to the training file")
    parser.add_argument("inference_results_directory", type=str, help="Directory for inference results")
    args = parser.parse_args()
    return args


def make_inference_results_directory(args):
    if not os.path.exists(args.inference_results_directory):
        os.makedirs(args.inference_results_directory)


def extract_xml(content):
    match = re.search(r'<results>(?:(?!</results>).)*</results>', content, re.DOTALL)
    if match:
        return match.group(0)
    return None


def parse_xml(xml_string):
    root = ET.fromstring(xml_string)
    question = root.find('.//question').text.strip()
    chain_of_reasoning = textwrap.dedent(root.find('.//chain_of_reasoning').text).strip()
    answer = root.find('.//answer').text.strip()
    return question, chain_of_reasoning, answer


def write_to_inference_file(args, question, chain_of_reasoning, answer):
    # Extract the basename from the paper URL
    parsed_url = urlparse(args.paper_url)
    basename = os.path.basename(parsed_url.path)

    # Remove file extension if present
    basename = os.path.splitext(basename)[0]

    inference_file_path = os.path.join(args.inference_results_directory, f"{basename}_cot_extraction.txt")
    with open(inference_file_path, 'w') as file:
        file.write(f"Paper URL: {args.paper_url}\n")
        file.write(f"Extraction preset: {args.extraction_preset}\n\n")
        file.write("Extracted Information:\n\n")
        file.write("----------------------\n\n")
        file.write(f"Question:\n\n{question}\n\n")
        file.write(f"Chain of Reasoning:\n\n{chain_of_reasoning}\n\n")
        file.write(f"Answer:\n\n{answer}\n\n")
        file.write("------------\n\n")
        file.write("Raw Content:\n\n")
        file.write(args.paper_content)
    print(f"Saved inference results to {inference_file_path}")


def write_to_training_file(args, question, chain_of_reasoning, answer):
    training_data = {
        "prompt": question,
        "response": f"{chain_of_reasoning}\n\nAnswer: {answer}"
    }
    with open(args.training_file, 'a') as file:
        file.write(json.dumps(training_data) + "\n")
    print(f"Saved training data to {args.training_file}")


def update_database_status(database_path, paper_id, paper_url, status):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE papers SET processing_status = ? WHERE id = ?", (status, paper_id))
        conn.commit()
        print(f"Updated paper {paper_url} status to {status}")
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def main():
    args = parse_args()
    make_inference_results_directory(args)

    xml_content = extract_xml(args.paper_content)
    if not xml_content:
        raise ValueError("Could not extract XML content from paper_content")

    question, chain_of_reasoning, answer = parse_xml(xml_content)
    write_to_inference_file(args, question, chain_of_reasoning, answer)
    write_to_training_file(args, question, chain_of_reasoning, answer)
    update_database_status(args.database, args.paper_id, args.paper_url, 'cot_extracted')


if __name__ == "__main__":
    main()
