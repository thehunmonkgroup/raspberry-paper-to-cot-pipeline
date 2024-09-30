#!/usr/bin/env python3

import os
import argparse
import random
import string
import json
import re
import xml.etree.ElementTree as ET
import textwrap

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
    random_identifier = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    inference_file_path = os.path.join(args.inference_results_directory, f"inference_result_{random_identifier}.txt")
    with open(inference_file_path, 'w') as file:
        file.write(f"Paper URL: {args.paper_url}\n\n")
        file.write("Extracted Information:\n\n")
        file.write("----------------------\n\n")
        file.write(f"Question:\n\n{question}\n\n")
        file.write(f"Chain of Reasoning:\n\n{chain_of_reasoning}\n\n")
        file.write(f"Answer:\n\n{answer}\n\n")
        file.write("------------\n\n")
        file.write("Raw Content:\n\n")
        file.write(args.paper_content)

def write_to_training_file(args, question, chain_of_reasoning, answer):
    training_data = {
        "question": question,
        "response": f"{chain_of_reasoning}\n\nAnswer: {answer}"
    }
    with open(args.training_file, 'a') as file:
        file.write(json.dumps(training_data) + "\n")

def main():
    args = parse_args()
    make_inference_results_directory(args)
    
    xml_content = extract_xml(args.paper_content)
    if xml_content:
        question, chain_of_reasoning, answer = parse_xml(xml_content)
        write_to_inference_file(args, question, chain_of_reasoning, answer)
        write_to_training_file(args, question, chain_of_reasoning, answer)
    else:
        print("Error: Could not extract XML content from paper_content")

if __name__ == "__main__":
    main()
