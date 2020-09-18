# needs tito installed
# needs subscription-manager build deps installed

echo "GIT_COMMIT:" "${GIT_COMMIT}"

pushd "${WORKSPACE}"

mkdir tito/

sudo yum-builddep subscription-manager.spec -y || true

# Get exit status from 'tito' not 'tee'
( set -o pipefail; tito build --output=tito/ --test --rpm | tee tito_results.txt )