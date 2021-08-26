# needs tito installed
# needs subscription-manager build deps installed

echo "GIT_COMMIT:" "${GIT_COMMIT}"

pushd "${WORKSPACE}"
mkdir tito/


# Use nexus mirror if available
NPM_REGISTRY="$(ping -c1 -W1 repository.engineering.redhat.com > /dev/null 2>&1 &&\
       	echo 'https://repository.engineering.redhat.com/nexus/repository/registry.npmjs.org' ||\
       	echo 'https://registry.npmjs.org')"
npm config set registry $NPM_REGISTRY

if [[ "$NPM_REGISTRY" =~ "redhat" ]]; then
    export NODE_TLS_REJECT_UNAUTHORIZED=0
    npm config set strict-ssl false
fi

sudo yum-builddep subscription-manager.spec -y || true

tito build --output=tito/ --test --rpm
