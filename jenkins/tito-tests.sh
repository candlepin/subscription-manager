# needs tito installed
# needs subscription-manager build deps installed

echo "GIT_COMMIT:" "${GIT_COMMIT}"

PROJECTROOT=$(git rev-parse --show-toplevel)
WORKSPACE=${WORKSPACE:-$PROJECTROOT}

pushd "${WORKSPACE}"
mkdir tito/

# Use nexus mirror if available
NPM_REGISTRY='https://registry.npmjs.org'
if ping -c1 -W1 repository.engineering.redhat.com > /dev/null 2>&1; then
	NPM_REGISTRY='https://repository.engineering.redhat.com/nexus/repository/registry.npmjs.org'
	if [ -f /run/secrets/rh-it.crt ]; then
		sudo cp /run/secrets/rh-it.crt /etc/pki/ca-trust/source/anchors/
		sudo /usr/bin/update-ca-trust
	else
		npm config set strict-ssl false
	fi
fi
npm config set registry $NPM_REGISTRY
sudo yum-builddep subscription-manager.spec -y || true

# Get exit status from 'tito' not 'tee'
( set -o pipefail; tito build --output=tito/ --test --rpm | tee tito_results.txt )
