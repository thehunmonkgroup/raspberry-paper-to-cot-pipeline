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
    printf '  %s\n' "${CATEGORIES[@]}"
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
