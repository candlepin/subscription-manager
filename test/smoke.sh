#!/bin/bash

# if we should run subman under any tool
# like 'time' or 'strace' or profilers, etc
#wrapper="/usr/bin/time"
WRAPPER=""

# if you run out of source, otherwise
# point this to /usr/bin or "PYTHONPATH=/wherever bin/subscription-manager"
# or "SUBMAN_DEBUG=1 bin/subscription-manager"
#SM="SUBMAN_DEBUG=1 bin/subscription-manager"
#SM="subscription-manager"
# To unset the default path and use the installed version (or system paths, etc)
# pass in PYPATH=, aka 'PYPATH= test/smoke.sh'
PYPATH=${PYPATH-PYTHONPATH=../python-rhsm/src:src/}
SM="${PYPATH} bin/subscription-manager"
WORKER="${PYPATH} python src/daemons/rhsmcertd-worker.py"
RHSMD="${PYPATH} src/daemons/rhsm_d.py"
RHSMCERTD="bin/rhsmcertd"
RCT="${PYPATH} bin/rct"
RHSM_DEBUG="${PYPATH} bin/rhsm-debug"

# assume we are testing installed version
VIRT_WHO="${PYPATH} /usr/bin/virt-who"

# where to store backup copies of rhsm related files
# NOTE: we currently dont restore them
BACKUP_DIR="/tmp/sm-smoke/backup"
TIMESTAMP=$(date +%s)

CONF_BACKUP="${BACKUP_DIR}/${TIMESTAMP}/"

# running yum requires installing the pluings
# Note: have to set CONF_BACKUP first
YUM="${PYPATH} yum -c ${CONF_BACKUP}/yum-smoke.conf"


# this script assumes it's running from top level of src checkout
YUM_PLUGINS_DIR="${PWD}/src/plugins/"
YUM_PLUGINS_CONF_DIR="${PWD}/etc-conf/plugin/"

# user/pass/org from the cli, or the default
# the defaults are based on candlepin test_data
USERNAME="${1:-duey}"
PASSWORD="${2:-password}"
ORG="${3:-donaldduck}"
ACTIVATION_KEY="${4:-default_key}"

REDEEM_EMAIL="${5:-noreply@notreal.redhat.com}"

#global_args="--help"
GLOBAL_ARGS=""

# Track failed tests
declare -a FAILED_TEST_ARRAY

# break on ctrl-c
trap 'exit' INT

C_RED='\033[1;31m'
C_GREEN='\033[1;32m'

C_FAIL="${C_RED}"
C_PASS="${C_GREEN}"

C_RST='\033[m'

# what to run before running the smoke tests, ie, setting up config
# note, script doesn't restore configs yet
backup_conf () {
    # back up configs
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${CONF_BACKUP}"
    mkdir -p "${CONF_BACKUP}/pki"
    mkdir -p "${CONF_BACKUP}/yum.repos.d"
    sudo cp --archive --recursive  /etc/rhsm/ "${CONF_BACKUP}/"
    # so we don't want to unregister/delete it
    sudo mv -v /etc/pki/consumer/ "${CONF_BACKUP}/pki/consumer"
    sudo cp --archive --recursive  /etc/pki/entitlement/ "${CONF_BACKUP}/pki/entitlement"
    sudo cp --archive --recursive  /etc/pki/product/ "${CONF_BACKUP}/pki/product"
    sudo cp --archive --recursive  /etc/pki/product-default/ "${CONF_BACKUP}/pki/product-default"
    sudo cp --archive  /etc/yum.repos.d/redhat.repo "${CONF_BACKUP}/yum.repos.d/"
    # others? /var/lib/rhsm? productid.js? docker certs? ostree config?
}

restore_conf() {
    echo "Restoring config from ${CONF_BACKUP}"
    sudo cp --archive --recursive "${CONF_BACKUP}/rhsm/" /etc/
    # NOTE: since we have since deleted
    sudo cp --archive --recursive "${CONF_BACKUP}/pki/consumer/" /etc/pki/
    sudo cp --archive --recursive "${CONF_BACKUP}/pki/entitlement/" /etc/pki/
    sudo cp --archive --recursive "${CONF_BACKUP}/pki/product/" /etc/pki/
    sudo cp --archive --recursive "${CONF_BACKUP}/pki/product-default/" /etc/pki/
    sudo cp --archive "${CONF_BACKUP}/yum.repos.d/redhat.repo" /etc/yum.repos.d/redhat.repo
}

build_local_yum_config () {

    # cp system yum.conf local, append config for pluginpath and pluginconfpath.
    # Need to do this because 'pluginpath' is read and set before any '--setopts' are
    # used.
    # backup copy of original
    cp /etc/yum.conf "${CONF_BACKUP}/yum.conf"
    # new copy for us to modify
    cp "${CONF_BACKUP}/yum.conf" "${CONF_BACKUP}/yum-smoke.conf"
    echo "pluginpath=${YUM_PLUGINS_DIR}" >> "${CONF_BACKUP}/yum-smoke.conf"
    echo "pluginconfpath=${YUM_PLUGINS_CONF_DIR}" >> "${CONF_BACKUP}/yum-smoke.conf"

}


pre () {
    backup_conf
    build_local_yum_config
}

post () {
    restore_conf
}

# run pre setup, backup confs etc
pre

echo_fail() {
    echo -e "${C_FAIL}""$*""${C_RST}"
}

echo_pass() {
    echo -e "${C_PASS}""$*""${C_RST}"
}

show_failures() {
    ret_code=0
    for i in "${FAILED_TEST_ARRAY[@]}" ;
    do
        echo_fail "*** FAILED ***: $i"
        ret_code=1
    done

    if [[ ${ret_code} == "1" ]] ; then
        return 1
    fi
    return 0
}

check_return_code () {
    EXPECTED_CODES=$1
    shift
    ACTUAL_CODE=$1
    shift
    TEST_CMD=$1
    echo "actual return code: ${ACTUAL_CODE}"

    for i in ${EXPECTED_CODES[*]} ;
    do
        if [[ "${ACTUAL_CODE}" = "${i}" ]] ; then
            echo_pass "TEST PASSED"
            return
        fi
    done

    # no expected codes matched, test failed
    echo_fail "!!!!!! TEST FAILED  !!!!!!!!!"
    echo_fail "${TEST_CMD}"
    echo_fail "actual return code: ${ACTUAL_CODE}"
    echo_fail "expect return code: ${EXPECTED_CODES}"
    FAILED_TEST_ARRAY+=("expected=${EXPECTED_CODES} actual=${ACTUAL_CODE} cmd: ${TEST_CMD}")
}

# arg1 is the tool to invoke
# arg2 is a string of space seperated expected exist codes 
#   ie "0" for a 0 success or "128" for a faulure
#   or "37 38 39" if those are all acceptable
run_tool () {
    TOOL=$1
    shift
    EXPECTED_RETURN_CODES=$1
    shift
    ARGS=$*
    echo "======================================================================="
    echo "running: ${TOOL} ${GLOBAL_ARGS} ${ARGS}"
    echo
    CMD_STRING="${WRAPPER} ${TOOL} ${GLOBAL_ARGS} ${ARGS}"
    sudo ${WRAPPER} ${TOOL} ${GLOBAL_ARGS} ${ARGS}
    #sudo ${WRAPPER} ${TOOL} ${GLOBAL_ARGS} ${ARGS}
    RETURN_CODE=$?
    echo
    check_return_code "${EXPECTED_RETURN_CODES}" "${RETURN_CODE}" "${CMD_STRING}"
    echo "======================================================================"
    echo
}

run_sm () {
    run_tool "${SM}" "$@"
}

run_rhsmcertd_worker () {
    run_tool "${WORKER}" "$@"
}

run_rct () {
    run_tool "${RCT}" "$@"
}

run_rhsmd () {
    run_tool "${RHSMD}" "$@"
}

run_rhsm_debug () {
    run_tool "${RHSM_DEBUG}" "$@"
}

#run_sat5to6 () { run_tool "${SAT5TO6}" "$@" }

run_rhsmcertd () {
    run_tool "${RHSMCERTD}" "$@"
}

run_yum () {
    run_tool "${YUM}" "$@"
}

run_virtwho () {
    run_tool "${VIRT_WHO}" "$@"
}

# basics
# first arg is valid exit codes
run_sm "0" register --username "${USERNAME}" --password "${PASSWORD}" --org "${ORG}" --force
run_sm "0" list --installed
run_sm "0" list --available
run_sm "0" service-level
run_sm "0" service-level --list
run_sm "0" repos
run_sm "0" attach

# Note: with current test data, the awesome-os repos will never be enabled
run_yum "0" repolist
run_yum "0" --disablerepo="*" repolist
run_yum "1" --disablerepo="*" --enablerepo="this-repo-doesnt-exist" repolist

run_sm "0" list --consumed

# NOTE: rct doesn't return particular usefule return codes, so these
#       could still be wrong
run_rct "0" cat-cert /etc/pki/entitlement/*[0-9].pem   # just the certs, not keys
run_rct "0" cat-cert /etc/pki/consumer/cert.pem
run_rct "0" cat-cert /etc/pki/product/*.pem

run_rct "0" stat-cert /etc/pki/entitlement/*[0-9].pem
run_rct "0" stat-cert /etc/pki/consumer/cert.pem
run_rct "0" stat-cert /etc/pki/product/*.pem
# TODO: test -manifest commands


run_sm "0" repos

# others...
run_sm "0" config --list
run_sm "0" version
# test status as is
run_sm "0" status
# TODO: test status with an unentitled product id installed


# If running against standalone cp or prod, return code is 69. If
# running against katello/sat6 it should be 0
run_sm "69" environments --username "${USERNAME}" --password "${PASSWORD}"

run_sm "0" refresh

run_sm "0" redeem --email "${REDEEM_EMAIL}"

run_sm "0" facts
run_sm "0" facts --list
run_sm "0" facts --update

run_sm "0" identity
run_sm "0" orgs --username "${USERNAME}" --password "${PASSWORD}"

# should be 0 for real cdn, but test_data will be 128
run_sm "0 78" release --list
run_sm "0" remove --all
run_sm "0" plugins --list

# pretty much always 0
run_rhsmcertd "0"
run_rhsmcertd "0" -n

run_rhsmcertd_worker "0"
run_rhsmcertd_worker "0" --autoheal

run_rhsmd "0" -s

# too slow
# run_rhsm_debug "0" system
run_rhsm_debug "0" system --sos

# this fails at the moment
# run_rhsm_debug "1" system --no-archive

# TODO: add some "fake" configs for virt-who
# virt-who
run_virtwho "0" -d -o


# TODO:
# test yum plugins with actual content
# check productid.js after next tests
# test yum plugins installing something, and installing productid
# test yum plugins triggering a product id delete
# test yum search-enabled-repos plugin
# test yum with 'manage_repos=0' in rhsm
# test yum --installroot
# test yum clean
# test yum 'disconnected'

run_sm "0" unregister
# exit 1 if already unregistered
run_sm "1" unregister

run_sm "0" import --certificate test/ent_cert_to_import.pem
run_sm "0" repos --list
# activation keys

# register, but activationkey didnt provide enough subs to cover, so not
# fully entitled, hence the '1'
run_sm "1" register --activationkey "${ACTIVATION_KEY}" --org "${ORG}" --force
run_sm "0" unregister
run_sm "64" register --activationkey "${ACTIVATION_KEY}" --org "${ORG}" --force --auto-attach
run_sm "1" unregister

run_sm "0" clean

# check proxy good and bad
run_sm "0" repos --list --proxy auto-services.usersys.redhat.com:3129
run_sm "0" repos --list --proxy auto-services.usersys.redhat.com:3128 --proxyuser redhat --proxypassword redhat
# this is not a proxy for CP
run_sm "69" repos --list --proxy www.redhat.com
# this requires auth. proxy is there but auth fails
run_sm "70" repos --list --proxy auto-services.usersys.redhat.com:3128
# same tests with config settings
run_sm "0" config --server.proxy_hostname=auto-services.usersys.redhat.com --server.proxy_port=3129
run_sm "0" repos --list
run_sm "0" config --server.proxy_hostname=auto-services.usersys.redhat.com --server.proxy_port=3128 --server.proxy_user=redhat --server.proxy_password=redhat
run_sm "0" repos --list
# reset config
restore_conf
run_sm "0" config --server.proxy_hostname=www.redhat.com
# it will run the config settings with no test. returns cached results
run_sm "0" repos --list
restore_conf
run_sm "0" config --server.proxy_hostname=auto-services.usersys.redhat.com --server.proxy_port=3128
run_sm "70" repos --list


# restore configs, etc
post

show_failures
