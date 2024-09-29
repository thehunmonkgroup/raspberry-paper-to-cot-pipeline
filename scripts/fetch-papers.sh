#!/usr/bin/env bash

set -euo pipefail

# Default date filters
DEFAULT_BEGIN_DATE="1970-01-01"
DEFAULT_END_DATE="2020-01-01"

# Default categories
CATEGORIES=(
    astro-ph.EP
    cond-mat.stat-mech
    cs.AI
    cs.CL
    cs.CV
    cs.CY
    cs.DS
    cs.GT
    cs.HC
    cs.LG
    cs.LO
    cs.RO
    cs.SE
    cs.SI
    econ.EM
    econ.GN
    econ.TH
    eess.SP
    math.HO
    math.LO
    math.OC
    physics.ed-ph
    physics.hist-ph
    physics.soc-ph
    q-bio.PE
    q-bio.QM
    q-fin.PM
    q-fin.RM
    stat.AP
    stat.ME
)

# arXiv Taxonomy Map
declare -A ARXIV_TAXONOMY_MAP
ARXIV_TAXONOMY_MAP=(
    ["astro-ph.EP"]="Earth and Planetary Astrophysics"
    ["cond-mat.stat-mech"]="Statistical Mechanics"
    ["cs.AI"]="Artificial Intelligence"
    ["cs.CL"]="Computation and Language"
    ["cs.CV"]="Computer Vision and Pattern Recognition"
    ["cs.CY"]="Computers and Society"
    ["cs.DS"]="Data Structures and Algorithms"
    ["cs.GT"]="Computer Science and Game Theory"
    ["cs.HC"]="Human-Computer Interaction"
    ["cs.LG"]="Machine Learning"
    ["cs.LO"]="Logic in Computer Science"
    ["cs.RO"]="Robotics"
    ["cs.SE"]="Software Engineering"
    ["cs.SI"]="Social and Information Networks"
    ["econ.EM"]="Econometrics"
    ["econ.GN"]="General Economics"
    ["econ.TH"]="Theoretical Economics"
    ["eess.SP"]="Signal Processing"
    ["math.HO"]="History and Overview"
    ["math.LO"]="Logic"
    ["math.OC"]="Optimization and Control"
    ["physics.ed-ph"]="Physics Education"
    ["physics.hist-ph"]="History and Philosophy of Physics"
    ["physics.soc-ph"]="Physics and Society"
    ["q-bio.PE"]="Populations and Evolution"
    ["q-bio.QM"]="Quantitative Methods"
    ["q-fin.PM"]="Portfolio Management"
    ["q-fin.RM"]="Risk Management"
    ["stat.AP"]="Applications"
    ["stat.ME"]="Methodology"
    ["astro-ph.CO"]="Cosmology and Nongalactic Astrophysics"
    ["astro-ph.GA"]="Astrophysics of Galaxies"
    ["astro-ph.HE"]="High Energy Astrophysical Phenomena"
    ["astro-ph.IM"]="Instrumentation and Methods for Astrophysics"
    ["astro-ph.SR"]="Solar and Stellar Astrophysics"
    ["cond-mat.dis-nn"]="Disordered Systems and Neural Networks"
    ["cond-mat.mes-hall"]="Mesoscale and Nanoscale Physics"
    ["cond-mat.mtrl-sci"]="Materials Science"
    ["cond-mat.other"]="Other Condensed Matter"
    ["cond-mat.quant-gas"]="Quantum Gases"
    ["cond-mat.soft"]="Soft Condensed Matter"
    ["cond-mat.str-el"]="Strongly Correlated Electrons"
    ["cond-mat.supr-con"]="Superconductivity"
    ["cs.AR"]="Hardware Architecture"
    ["cs.CC"]="Computational Complexity"
    ["cs.CE"]="Computational Engineering, Finance, and Science"
    ["cs.CR"]="Cryptography and Security"
    ["cs.DB"]="Databases"
    ["cs.DC"]="Distributed, Parallel, and Cluster Computing"
    ["cs.DL"]="Digital Libraries"
    ["cs.DM"]="Discrete Mathematics"
    ["cs.ET"]="Emerging Technologies"
    ["cs.FL"]="Formal Languages and Automata Theory"
    ["cs.GL"]="General Literature"
    ["cs.GR"]="Graphics"
    ["cs.IR"]="Information Retrieval"
    ["cs.IT"]="Information Theory"
    ["cs.MA"]="Multiagent Systems"
    ["cs.MM"]="Multimedia"
    ["cs.MS"]="Mathematical Software"
    ["cs.NA"]="Numerical Analysis"
    ["cs.NE"]="Neural and Evolutionary Computing"
    ["cs.NI"]="Networking and Internet Architecture"
    ["cs.OH"]="Other Computer Science"
    ["cs.OS"]="Operating Systems"
    ["cs.PF"]="Performance"
    ["cs.PL"]="Programming Languages"
    ["cs.SC"]="Symbolic Computation"
    ["cs.SD"]="Sound"
    ["cs.SY"]="Systems and Control"
    ["econ.EC"]="Econometrics"
    ["eess.AS"]="Audio and Speech Processing"
    ["eess.IV"]="Image and Video Processing"
    ["eess.SY"]="Systems and Control"
    ["gr-qc"]="General Relativity and Quantum Cosmology"
    ["hep-ex"]="High Energy Physics - Experiment"
    ["hep-lat"]="High Energy Physics - Lattice"
    ["hep-ph"]="High Energy Physics - Phenomenology"
    ["hep-th"]="High Energy Physics - Theory"
    ["math.AC"]="Commutative Algebra"
    ["math.AG"]="Algebraic Geometry"
    ["math.AP"]="Analysis of PDEs"
    ["math.AT"]="Algebraic Topology"
    ["math.CA"]="Classical Analysis and ODEs"
    ["math.CO"]="Combinatorics"
    ["math.CT"]="Category Theory"
    ["math.CV"]="Complex Variables"
    ["math.DG"]="Differential Geometry"
    ["math.DS"]="Dynamical Systems"
    ["math.FA"]="Functional Analysis"
    ["math.GM"]="General Mathematics"
    ["math.GN"]="General Topology"
    ["math.GR"]="Group Theory"
    ["math.GT"]="Geometric Topology"
    ["math.KT"]="K-Theory and Homology"
    ["math.MG"]="Metric Geometry"
    ["math.MP"]="Mathematical Physics"
    ["math.NA"]="Numerical Analysis"
    ["math.NT"]="Number Theory"
    ["math.OA"]="Operator Algebras"
    ["math.PR"]="Probability"
    ["math.QA"]="Quantum Algebra"
    ["math.RA"]="Rings and Algebras"
    ["math.RT"]="Representation Theory"
    ["math.SG"]="Symplectic Geometry"
    ["math.SP"]="Spectral Theory"
    ["math.ST"]="Statistics Theory"
    ["math-ph"]="Mathematical Physics"
    ["nlin.AO"]="Adaptation and Self-Organizing Systems"
    ["nlin.CD"]="Chaotic Dynamics"
    ["nlin.CG"]="Cellular Automata and Lattice Gases"
    ["nlin.PS"]="Pattern Formation and Solitons"
    ["nlin.SI"]="Exactly Solvable and Integrable Systems"
    ["nucl-ex"]="Nuclear Experiment"
    ["nucl-th"]="Nuclear Theory"
    ["physics.acc-ph"]="Accelerator Physics"
    ["physics.ao-ph"]="Atmospheric and Oceanic Physics"
    ["physics.app-ph"]="Applied Physics"
    ["physics.atm-clus"]="Atomic and Molecular Clusters"
    ["physics.atom-ph"]="Atomic Physics"
    ["physics.bio-ph"]="Biological Physics"
    ["physics.chem-ph"]="Chemical Physics"
    ["physics.class-ph"]="Classical Physics"
    ["physics.comp-ph"]="Computational Physics"
    ["physics.data-an"]="Data Analysis, Statistics and Probability"
    ["physics.flu-dyn"]="Fluid Dynamics"
    ["physics.gen-ph"]="General Physics"
    ["physics.geo-ph"]="Geophysics"
    ["physics.ins-det"]="Instrumentation and Detectors"
    ["physics.med-ph"]="Medical Physics"
    ["physics.optics"]="Optics"
    ["physics.plasm-ph"]="Plasma Physics"
    ["physics.pop-ph"]="Popular Physics"
    ["physics.space-ph"]="Space Physics"
    ["q-bio.BM"]="Biomolecules"
    ["q-bio.CB"]="Cell Behavior"
    ["q-bio.GN"]="Genomics"
    ["q-bio.MN"]="Molecular Networks"
    ["q-bio.NC"]="Neurons and Cognition"
    ["q-bio.OT"]="Other Quantitative Biology"
    ["q-bio.SC"]="Subcellular Processes"
    ["q-bio.TO"]="Tissues and Organs"
    ["q-fin.CP"]="Computational Finance"
    ["q-fin.EC"]="Economics"
    ["q-fin.GN"]="General Finance"
    ["q-fin.MF"]="Mathematical Finance"
    ["q-fin.PR"]="Pricing of Securities"
    ["q-fin.ST"]="Statistical Finance"
    ["q-fin.TR"]="Trading and Market Microstructure"
    ["quant-ph"]="Quantum Physics"
    ["stat.CO"]="Computation"
    ["stat.ML"]="Machine Learning"
    ["stat.OT"]="Other Statistics"
    ["stat.TH"]="Statistics Theory"
)

# Script name
SCRIPT_NAME=$(basename "${0}")

usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Pull arXiv papers based on date range and categories.

Options:
  --begin DATE       Start date for paper filtering (YYYY-MM-DD) (default: ${DEFAULT_BEGIN_DATE})
  --end DATE         End date for paper filtering (YYYY-MM-DD) (default: ${DEFAULT_END_DATE})
  --category LIST    Comma or space-separated list of categories (optional)
  --config           Display current configuration and exit
  --list             Display all available categories with descriptions and exit
  --debug            Enable debug mode
  -h, --help         Display this help message and exit

If no category is specified, all default categories will be used.
EOF
}

# Function to display configuration
display_config() {
    echo "Current configuration:"
    echo "Begin date: ${begin_date}"
    echo "End date: ${end_date}"
    echo "Categories:"
    for category in "${CATEGORIES[@]}"; do
        description="${ARXIV_TAXONOMY_MAP[${category}]:-Unknown}"
        printf "  %-15s %s\n" "${category}" "${description}"
    done
    exit 0
}

# Function to display all categories with descriptions
display_categories() {
    echo "Available arXiv categories:"
    for category in "${!ARXIV_TAXONOMY_MAP[@]}"; do
        printf "%-15s %s\n" "${category}" "${ARXIV_TAXONOMY_MAP[${category}]}"
    done
    exit 0
}

# Function to join array elements
join_by() {
    local IFS="$1"
    shift
    echo "$*"
}

# Parse command line arguments
begin_date="${DEFAULT_BEGIN_DATE}"
end_date="${DEFAULT_END_DATE}"
debug=false
custom_categories=""

while [[ ${#} -gt 0 ]]; do
    case ${1} in
        --begin)
            begin_date=${2}
            shift 2
            ;;
        --end)
            end_date=${2}
            shift 2
            ;;
        --category)
            custom_categories=${2}
            shift 2
            ;;
        --config)
            display_config
            ;;
        --list)
            display_categories
            ;;
        --debug)
            debug=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option ${1}" >&2
            usage >&2
            exit 1
            ;;
    esac
done

# Validate date format
validate_date() {
    if ! date -d "$1" >/dev/null 2>&1; then
        echo "Error: Invalid date format for $2. Use YYYY-MM-DD." >&2
        exit 1
    fi
}

validate_date "${begin_date}" "--begin"
validate_date "${end_date}" "--end"

# Process categories
if [[ -n ${custom_categories} ]]; then
    IFS=',' read -ra CATEGORIES <<< "${custom_categories//,/ }"
fi

# Main execution
for category in "${CATEGORIES[@]}"; do
    cmd="./pull-arxiv-papers.py"
    cmd+=" --date-filter-begin ${begin_date}"
    cmd+=" --date-filter-end ${end_date}"
    cmd+=" --category ${category}"

    if ${debug}; then
        cmd+=" --debug"
    fi

    echo "Executing: ${cmd}"
    eval "${cmd}"
done
