import os
from pathlib import Path

CWD = Path(os.getcwd())

# LWE
DEFAULT_LWE_PRESET = "claude-sonnet"
DEFAULT_PAPER_PROFILER_TEMPLATE = "raspberry-paper-profiler.md"
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

# Profiling.
PROFILING_CRITERIA = [
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
REQUIRED_PROFILING_CRITERIA = [
    "clear_question",
    "definitive_answer",
    "complex_reasoning",
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

# Database.
DEFAULT_DB_NAME = CWD / "papers.db"
CREATE_TABLES_QUERY = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT UNIQUE,
    paper_url TEXT,
    processing_status TEXT,
    criteria_clear_question INT DEFAULT 0,
    criteria_definitive_answer INT DEFAULT 0,
    criteria_complex_reasoning INT DEFAULT 0,
    criteria_coherent_structure INT DEFAULT 0,
    criteria_layperson_comprehensible INT DEFAULT 0,
    criteria_minimal_jargon INT DEFAULT 0,
    criteria_illustrative_examples INT DEFAULT 0,
    criteria_significant_insights INT DEFAULT 0,
    criteria_verifiable_steps INT DEFAULT 0,
    criteria_overall_suitability INT DEFAULT 0,
    suitability_score INT DEFAULT 0
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
STATUS_READY_TO_CLEAN = 'ready_to_clean'
STATUS_VERIFIED = "verified"
STATUS_MISSING = "missing"
STATUS_PROFILED = "profiled"
STATUS_SCORED = "scored"
