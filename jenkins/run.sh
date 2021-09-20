cd $(git rev-parse --show-toplevel)
mkdir test_results
( set -o pipefail; sh $2 | tee test_results/$1.txt )
RETVAL="$?"
echo "RETVAL: $RETVAL" >> test_results/$1.txt

