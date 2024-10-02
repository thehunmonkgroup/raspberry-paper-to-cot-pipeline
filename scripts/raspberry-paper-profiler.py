#!/usr/bin/env python3

import argparse
import re
import xml.etree.ElementTree as ET
import sqlite3
import os
from urllib.parse import urlparse

# Define the rubric questions as a constant list
QUESTIONS = [
    'clear_question',
    'definitive_answer',
    'complex_reasoning',
    'coherent_structure',
    'layperson_comprehensible',
    'minimal_jargon',
    'illustrative_examples',
    'significant_insights',
    'verifiable_steps',
    'overall_suitability'
]

def parse_args():
    parser = argparse.ArgumentParser(description="Profile papers based on a set of rubric questions.")
    parser.add_argument("profiling_preset", type=str, help="Model configuration used to perform the profiling")
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument("paper_content", type=str, help="Content to be profiled")
    parser.add_argument("inference_results_directory", type=str, help="Directory for inference results")
    return parser.parse_args()

def extract_xml(content):
    match = re.search(r'<results>(?:(?!</results>).)*</results>', content, re.DOTALL)
    if match:
        return match.group(0)
    return None

def parse_xml(xml_string):
    root = ET.fromstring(xml_string)
    criteria = {}
    for question in QUESTIONS:
        element = root.find(f'.//{question}')
        if element is not None:
            value = element.text.strip()
            criteria[f'criteria_{question}'] = 1 if value == 'Yes' else 0
        else:
            raise ValueError(f"{question} not found in XML")
    return criteria

def get_pretty_printed_rubric_questions(criteria):
    output = []
    for question in QUESTIONS:
        answer = "Yes" if criteria[f'criteria_{question}'] == 1 else "No"
        output.append(f"  {question}: {answer}")
    return "\n".join(output)

def update_database(database_path, paper_id, paper_url, criteria):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Dynamically create the UPDATE query
        update_fields = ', '.join([f'criteria_{question} = ?' for question in QUESTIONS])
        update_query = f"""
        UPDATE papers SET
            processing_status = 'profiled',
            {update_fields}
        WHERE id = ?
        """

        # Create a tuple of values to update
        update_values = tuple(criteria[f'criteria_{question}'] for question in QUESTIONS)

        cursor.execute(update_query, (*update_values, paper_id))
        conn.commit()

        # Pretty print the rubric questions and answers
        print(f"Updated profiling results for paper {paper_url}")
        print("Questions and answers:")
        print(get_pretty_printed_rubric_questions(criteria))
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def write_inference_artifact(args, criteria, xml_content):
    # Extract the basename from the paper URL
    parsed_url = urlparse(args.paper_url)
    basename = os.path.basename(parsed_url.path)

    # Remove file extension if present
    basename = os.path.splitext(basename)[0]

    inference_file_path = os.path.join(args.inference_results_directory, f"{basename}_paper_profiling.txt")
    with open(inference_file_path, 'w') as file:
        file.write(f"Paper URL: {args.paper_url}\n")
        file.write(f"Profiling preset: {args.profiling_preset}\n\n")
        file.write("Profiling results:\n\n")
        file.write(get_pretty_printed_rubric_questions(criteria))
        file.write("\n\n----------------------\n\n")
        file.write("Raw Inference Output:\n\n")
        file.write(xml_content)
    print(f"Saved inference results to {inference_file_path}")

def main():
    args = parse_args()

    xml_content = extract_xml(args.paper_content)
    if not xml_content:
        raise ValueError("Could not extract XML content from paper_content")

    criteria = parse_xml(xml_content)
    write_inference_artifact(args, criteria, xml_content)
    update_database(args.database, args.paper_id, args.paper_url, criteria)

if __name__ == "__main__":
    main()
