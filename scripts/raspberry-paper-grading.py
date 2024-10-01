#!/usr/bin/env python3

import argparse
import re
import xml.etree.ElementTree as ET
import sqlite3
import os
from urllib.parse import urlparse

# Define the rubrics as a constant list
RUBRICS = [
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
    parser = argparse.ArgumentParser(description="Grade papers based on the rubric.")
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    parser.add_argument("paper_content", type=str, help="Content to be graded")
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
    for rubric in RUBRICS:
        element = root.find(f'.//{rubric}')
        if element is not None:
            value = element.text.strip()
            criteria[f'criteria_{rubric}'] = 1 if value == 'Yes' else 0
        else:
            raise ValueError(f"{rubric} not found in XML")
    return criteria

def get_pretty_printed_rubrics(criteria):
    output = []
    for rubric in RUBRICS:
        grade = "Yes" if criteria[f'criteria_{rubric}'] == 1 else "No"
        output.append(f"  {rubric}: {grade}")
    return "\n".join(output)

def update_database(database_path, paper_id, paper_url, criteria):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Dynamically create the UPDATE query
        update_fields = ', '.join([f'criteria_{rubric} = ?' for rubric in RUBRICS])
        update_query = f"""
        UPDATE papers SET
            processing_status = 'graded',
            {update_fields}
        WHERE id = ?
        """

        # Create a tuple of values to update
        update_values = tuple(criteria[f'criteria_{rubric}'] for rubric in RUBRICS)

        cursor.execute(update_query, (*update_values, paper_id))
        conn.commit()

        # Pretty print the rubrics and grades
        print(f"Updated grading results for paper {paper_url}")
        print("Rubrics and grades:")
        print(get_pretty_printed_rubrics(criteria))
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def write_inference_artifact(results_directory, paper_url, criteria, xml_content):
    # Extract the basename from the paper URL
    parsed_url = urlparse(paper_url)
    basename = os.path.basename(parsed_url.path)

    # Remove file extension if present
    basename = os.path.splitext(basename)[0]

    inference_file_path = os.path.join(results_directory, f"{basename}_paper_grading.txt")
    with open(inference_file_path, 'w') as file:
        file.write(f"Paper URL: {paper_url}\n\n")
        file.write("Grading Results:\n\n")
        file.write(get_pretty_printed_rubrics(criteria))
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
    write_inference_artifact(args.inference_results_directory, args.paper_url, criteria, xml_content)
    update_database(args.database, args.paper_id, args.paper_url, criteria)

if __name__ == "__main__":
    main()
