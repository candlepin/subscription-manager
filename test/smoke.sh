#!/bin/bash

# if we should run subman under any tool
# like 'time' or 'strace'
#wrapper="/usr/bin/time"
WRAPPER=""

# if you run out of source, otherwise
# point this to /usr/bin or "PYTHONPATH=/wherever bin/subscription-manager"
# or "SUBMAN_DEBUG=1 bin/subscription-manager"
#SM="SUBMAN_DEBUG=1 bin/subscription-manager"
#SM="subscription-manager"
SM="PYTHONPATH=../python-rhsm/src/:src/ bin/subscription-manager"


# where to store backup copies of rhsm related files
# NOTE: we currently dont restore them
BACKUP_DIR="/tmp/sm-smoke/backup"

# user/pass/org from the cli, or the default
USERNAME="${1:-admin}"
PASSWORD="${2:-admin}"
ORG="${3:-admin}"
ACTIVATION_KEY="${4:-default_key}"

#global_args="--help"
GLOBAL_ARGS=""

# break on ctrl-c
trap 'exit' INT

# what to run before running the smoke tests, ie, setting up config
# note, script doesn't restore configs yet
backup_conf () {
    # back up configs
    mkdir -p "${BACKUP_DIR}"
    TIMESTAMP=$(date +%s)
    CONF_BACKUP="${BACKUP_DIR}/${TIMESTAMP}/"
    mkdir -p "${CONF_BACKUP}"
    sudo cp --archive --recursive  /etc/rhsm/ "${CONF_BACKUP}/"
    sudo cp --archive --recursive  /etc/pki/ "${CONF_BACKUP}/"

}

pre () {

    backup_conf
}

pre


run_sm () {
    echo "===================="
    echo "running: ${SM} ${GLOBAL_ARGS} $*"
    echo
    sudo ${WRAPPER} ${SM} ${GLOBAL_ARGS} $*
    RETURN_CODE=$?
    echo "return code: ${RETURN_CODE}"
    echo "===================="
}

# basics
run_sm unregister
run_sm register --username "${USERNAME}" --password "${PASSWORD}" --org "${ORG}" --force
run_sm list --installed
run_sm list --available
run_sm service-level
run_sm repos
run_sm subscribe --auto
run_sm list --consumed
run_sm repos

# others...
run_sm config --list
run_sm version
run_sm status
run_sm facts
run_sm identity
run_sm orgs --username "${USERNAME}" --password "${PASSWORD}"
run_sm release --list
run_sm remove --all
run_sm plugins --list
run_sm unregister

# activation keys
run_sm unregister
run_sm register --activationkey "${ACTIVATION_KEY}" --org "${ORG}" --force
run_sm unregister
run_sm register --activationkey "${ACTIVATION_KEY}" --org "${ORG}" --force --auto-attach
run_sm unregister

# what to run after the tests, ie, restore configs, etc
#post () {
#    
#}

#post
