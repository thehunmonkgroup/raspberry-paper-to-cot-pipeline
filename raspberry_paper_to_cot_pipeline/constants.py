# System messages.
SYSTEM_MESSAGE_COT_EXTRACTION = "You are a thinking agent responsible for developing a detailed, step-by-step thought process in response to a request, problem, or conversation. Your task is to break down the situation into a structured reasoning process. If feedback is provided, integrate it into your thought process for refinement."

# Categories.
DEFAULT_CATEGORIES = [
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
DEFAULT_DB_NAME = "papers.db"
CREATE_TABLES_QUERY = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_url TEXT UNIQUE,
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
STATUS_READY_TO_CLEAN = 'ready_to_clean'
STATUS_DEFAULT_PROCESSING = "ready_to_clean"
