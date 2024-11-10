import os
from pathlib import Path

CWD = Path(os.getcwd())

# LWE
DEFAULT_LWE_PRESET = "claude-sonnet"
DEFAULT_PAPER_PROFILER_PRESET = "claude-sonnet"
DEFAULT_COT_EXTRACTION_PRESET = "claude-sonnet"
DEFAULT_COT_CRITIQUE_PRESET = "claude-sonnet"
DEFAULT_COT_REFINEMENT_PRESET = "claude-sonnet"
DEFAULT_COT_QUALITY_ASSESSOR_PRESET = "claude-sonnet"
DEFAULT_PAPER_PROFILER_TEMPLATE = "raspberry-paper-profiler.md"
DEFAULT_COT_EXTRACTION_TEMPLATE = "raspberry-cot-extraction.md"
DEFAULT_COT_CRITIQUE_TEMPLATE = "raspberry-cot-critique.md"
DEFAULT_COT_REFINEMENT_TEMPLATE = "raspberry-cot-refine.md"
DEFAULT_COT_QUALITY_ASSESSOR_TEMPLATE = "raspberry-cot-quality-assessor.md"

# Artifact naming patterns
COT_INITIAL_EXTRACTION_ARTIFACT_PATTERN = "{paper_id}-cot-initial-extraction.txt"
COT_CRITIQUE_ARTIFACT_PATTERN = "{paper_id}-cot-critique.txt"
COT_REFINEMENT_ARTIFACT_PATTERN = "{paper_id}-cot-refinement.txt"
COT_QUALITY_ASSESSMENT_ARTIFACT_PATTERN = "{paper_id}-cot-quality-assessment.txt"
TRAINING_ARTIFACT_PATTERN = "{paper_id}-training-data.jsonl"
# TODO: This should use the package root, not CWD.
LWE_CONFIG_DIR = CWD / "lwe" / "config"
LWE_DATA_DIR = CWD / "lwe" / "storage"

# Categories.
ARXIV_DEFAULT_CATEGORIES = [
    "astro-ph.EP",
    "astro-ph.GA",
    "astro-ph.HE",
    "cond-mat.dis-nn",
    "cond-mat.mtrl-sci",
    "cond-mat.stat-mech",
    "cs.AI",
    "cs.CL",
    "cs.CV",
    "cs.CY",
    "cs.DS",
    "cs.GT",
    "cs.HC",
    "cs.LG",
    "cs.LO",
    "cs.RO",
    "cs.SE",
    "cs.SI",
    "econ.EM",
    "econ.GN",
    "econ.TH",
    "eess.SP",
    "eess.SY",
    "gr-qc",
    "hep-ex",
    "hep-th",
    "math.CA",
    "math.CO",
    "math.CT",
    "math.HO",
    "math.IT",
    "math.LO",
    "math.MP",
    "math.NA",
    "math.NT",
    "math.OC",
    "nlin.AO",
    "nlin.CD",
    "nlin.PS",
    "nlin.SI",
    "nucl-th",
    "physics.app-ph",
    "physics.atom-ph",
    "physics.bio-ph",
    "physics.chem-ph",
    "physics.class-ph",
    "physics.data-an",
    "physics.flu-dyn",
    "physics.gen-ph",
    "physics.geo-ph",
    "physics.pop-ph",
    "physics.soc-ph",
    "physics.space-ph",
    "q-bio.CB",
    "q-bio.GN",
    "q-bio.NC",
    "q-bio.PE",
    "q-bio.QM",
    "q-fin.PM",
    "q-fin.RM",
    "quant-ph",
    "stat.AP",
    "stat.ME",
    "stat.TH",
]

# Paths.
DEFAULT_INFERENCE_ARTIFACTS_DIR = CWD / "results" / "inference"
DEFAULT_TRAINING_ARTIFACTS_DIR = CWD / "results" / "training"
DEFAULT_PDF_CACHE_DIR = CWD / "pdf_cache"

# Paper profiling.
PAPER_PROFILING_CRITERIA = [
    "clear_question",
    "definitive_answer",
    "complex_reasoning",
    "coherent_structure",
    "layperson_comprehensible",
    "minimal_jargon",
    "illustrative_examples",
    "significant_insights",
    "verifiable_steps",
    "overall_suitability",
]
REQUIRED_PAPER_PROFILING_CRITERIA = [
    "clear_question",
    "definitive_answer",
    "complex_reasoning",
]

# CoT quality assessment
COT_QUALITY_ASSESSMENT_CRITERIA = [
    # source_fidelity criteria
    "contains_only_paper_content",
    "includes_all_critical_info",
    "accurate_representation",
    "technical_accuracy",
    # reasoning_integrity criteria
    "steps_supported_by_paper",
    "no_logical_leaps",
    "correct_sequence",
    "conclusion_follows",
    # training_utility criteria
    "question_answerable",
    "multi_step_progression",
    "answer_addresses_question",
    "appropriate_complexity",
    # structural_quality criteria
    "consistent_voice",
    "terms_explained",
    "no_contradictions",
    "complete_flow"
]

REQUIRED_COT_QUALITY_ASSESSMENT_CRITERIA = [
    "contains_only_paper_content",
    "includes_all_critical_info",
    "accurate_representation",
    "steps_supported_by_paper",
    "no_logical_leaps",
    "answer_addresses_question"
]

# ArXiv.
ARXIV_TAXONOMY_URL = "https://arxiv.org/category_taxonomy"
ARXIV_EXPORT_BASE = "https://export.arxiv.org"

# Fetch.
FETCH_DEFAULT_BEGIN_DATE = "1970-01-01"
FETCH_DEFAULT_END_DATE = "2021-01-01"
FETCH_MAX_RESULTS_DEFAULT = 1000
FETCH_MAX_RESULTS_FALLBACK = 100
FETCH_MAX_EMPTY_RESULTS_ATTEMPTS = 10

# CoT extraction.
COT_EXTRACTION_DEFAULT_SUITABILITY_SCORE = 8

# Database.
DEFAULT_DB_NAME = CWD / "papers.db"
CREATE_TABLES_QUERY = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT UNIQUE,
    paper_url TEXT,
    processing_status TEXT,
    profiler_criteria_clear_question INT DEFAULT 0,
    profiler_criteria_definitive_answer INT DEFAULT 0,
    profiler_criteria_complex_reasoning INT DEFAULT 0,
    profiler_criteria_coherent_structure INT DEFAULT 0,
    profiler_criteria_layperson_comprehensible INT DEFAULT 0,
    profiler_criteria_minimal_jargon INT DEFAULT 0,
    profiler_criteria_illustrative_examples INT DEFAULT 0,
    profiler_criteria_significant_insights INT DEFAULT 0,
    profiler_criteria_verifiable_steps INT DEFAULT 0,
    profiler_criteria_overall_suitability INT DEFAULT 0,
    profiler_suitability_score INT DEFAULT 0,
    cot_quality_assessment_criteria_contains_only_paper_content INT DEFAULT 0,
    cot_quality_assessment_criteria_includes_all_critical_info INT DEFAULT 0,
    cot_quality_assessment_criteria_accurate_representation INT DEFAULT 0,
    cot_quality_assessment_criteria_technical_accuracy INT DEFAULT 0,
    cot_quality_assessment_criteria_steps_supported_by_paper INT DEFAULT 0,
    cot_quality_assessment_criteria_no_logical_leaps INT DEFAULT 0,
    cot_quality_assessment_criteria_correct_sequence INT DEFAULT 0,
    cot_quality_assessment_criteria_conclusion_follows INT DEFAULT 0,
    cot_quality_assessment_criteria_question_answerable INT DEFAULT 0,
    cot_quality_assessment_criteria_multi_step_progression INT DEFAULT 0,
    cot_quality_assessment_criteria_answer_addresses_question INT DEFAULT 0,
    cot_quality_assessment_criteria_appropriate_complexity INT DEFAULT 0,
    cot_quality_assessment_criteria_consistent_voice INT DEFAULT 0,
    cot_quality_assessment_criteria_terms_explained INT DEFAULT 0,
    cot_quality_assessment_criteria_no_contradictions INT DEFAULT 0,
    cot_quality_assessment_criteria_complete_flow INT DEFAULT 0,
    cot_quality_assessment_suitability_score INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS paper_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER,
    category TEXT,
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    UNIQUE(paper_id, category)
);
"""
DEFAULT_FETCH_BY_STATUS_COLUMNS = ["id", "paper_id", "paper_url"]
STATUS_PAPER_LINK_DOWNLOADED = "paper_link_downloaded"
STATUS_PAPER_LINK_VERIFIED = "paper_link_verified"
STATUS_PAPER_MISSING = "paper_missing"
STATUS_PAPER_PROFILED = "paper_profiled"
STATUS_PAPER_PROFILE_SCORED = "paper_profile_scored"
STATUS_COT_EXTRACTED = "cot_extracted"
STATUS_COT_QUALITY_ASSESSED = "cot_quality_assessed"
STATUS_COT_QUALITY_SCORED = "cot_quality_scored"
STATUS_FAILED_COT_EXTRACTION = "failed_cot_extraction"
STATUS_FAILED_COT_QUALITY_ASSESSMENT = "failed_cot_quality_assessment"

# URL cleaning
PAPER_URL_REQUEST_TIMEOUT_SECONDS = 15
PAPER_URL_PROGRESS_LOG_BATCH_SIZE = 1000

# Training
TRAINING_SYSTEM_MESSAGE = "You are a thinking agent responsible for developing a detailed, step-by-step thought process in response to a request, problem, or conversation. Your task is to break down the situation into a structured reasoning process. If feedback is provided, integrate it into your thought process for refinement."
