# needs tito installed
# needs subscription-manager build deps installed

echo "sha1:" "${sha1}"

pushd "${WORKSPACE}"

mkdir tito/

# Get exit status from 'tito' not 'tee'
( set -o pipefail; tito build --output=tito/ --test --rpm | tee tito_results.txt )