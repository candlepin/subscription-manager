#!/bin/bash

if (( $# != 2 )); then
    >&2 cat << EOF
    This script requires two arguments.

    Usage: $0 [NAME_OF_TEST_RESULTS] [PATH_TO_SCRIPT_TO_RUN_AND_CAPTURE_RESULTS_FROM]
    This script will run the script provided as the second argument, and capture the output/retval.
EOF
    exit
fi

cd $(git rev-parse --show-toplevel)
mkdir test_results
( set -o pipefail; sh $2 | tee test_results/$1.txt )
RETVAL="$?"
echo "RETVAL: $RETVAL" >> test_results/$1.txt

