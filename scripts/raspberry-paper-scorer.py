#!/usr/bin/env python3

import argparse
import sqlite3
import logging

REQUIRED_CRITERIA = [
    'criteria_clear_question',
    'criteria_definitive_answer',
    'criteria_complex_reasoning',
]

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Score papers based on profiling criteria.")
    parser.add_argument("database", type=str, help="Path to the SQLite database")
    parser.add_argument("paper_id", type=str, help="ID of the paper in the database")
    parser.add_argument("paper_url", type=str, help="URL of the paper")
    return parser.parse_args()

def missing_required_criteria(criteria):
    return any(criteria[c] == 0 for c in REQUIRED_CRITERIA)

def calculate_suitability_score(criteria):
    return 0 if missing_required_criteria(criteria) else sum(criteria.values())

def update_database(database_path, paper_id, paper_url, suitability_score):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE papers
            SET processing_status = 'scored', suitability_score = ?
            WHERE id = ?
        """, (suitability_score, paper_id))
        conn.commit()
        print(f"Updated suitability score for paper {paper_url} to {suitability_score}")
        print(f"Set processing status for paper {paper_url} to 'scored'")
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def get_criteria_from_database(database_path, paper_id):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT criteria_clear_question, criteria_definitive_answer, criteria_complex_reasoning,
                   criteria_coherent_structure, criteria_layperson_comprehensible, criteria_minimal_jargon,
                   criteria_illustrative_examples, criteria_significant_insights, criteria_verifiable_steps,
                   criteria_overall_suitability
            FROM papers
            WHERE id = ?
        """, (paper_id,))
        result = cursor.fetchone()
        if result:
            return {
                'criteria_clear_question': result[0],
                'criteria_definitive_answer': result[1],
                'criteria_complex_reasoning': result[2],
                'criteria_coherent_structure': result[3],
                'criteria_layperson_comprehensible': result[4],
                'criteria_minimal_jargon': result[5],
                'criteria_illustrative_examples': result[6],
                'criteria_significant_insights': result[7],
                'criteria_verifiable_steps': result[8],
                'criteria_overall_suitability': result[9]
            }
        else:
            raise ValueError(f"No criteria found for paper ID {paper_id}")
    finally:
        if conn:
            conn.close()

def main():
    args = parse_args()
    criteria = get_criteria_from_database(args.database, args.paper_id)
    suitability_score = calculate_suitability_score(criteria)
    update_database(args.database, args.paper_id, args.paper_url, suitability_score)

if __name__ == "__main__":
    logger = setup_logging()
    main()
