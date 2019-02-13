cd $WORKSPACE

# Do nothing if syspurpose directory is absent
if [ ! -d syspurpose ]; then
    exit 0;
fi

echo "sha1:" "${sha1}"

sudo dnf clean expire-cache
sudo dnf builddep subscription-manager.spec  # ensure we install any missing rpm deps

pushd $WORKSPACE/syspurpose

pip install --user pipenv
# Make pipenv available on the path
PATH=$PATH:"$(python -m site --user-base)/bin"

pipenv install --dev
pipenv run ./setup.py nosetests
