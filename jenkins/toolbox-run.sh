#!/bin/bash -x
PROJECT_ROOT=$(git rev-parse --show-toplevel)

# Run one of our tests inside a newly created toolbox container

if (( $# != 2)); then
    >&2 cat << EOF
    This script requires two arguments.

    Usage: $0 [END_OF_TAG] [PATH_TO_SCRIPT_TO_RUN_IN_CONTAINER]
    This script will create a toolbox container, run the script provided in it, and forcefully destroy the toolbox container.
EOF
    exit
fi

pushd $PROJECT_ROOT
toolbox create -i quay.io/candlepin/subscription-manager:PR-$CHANGE_ID -c PR-$CHANGE_ID-$1
toolbox run -c PR-$CHANGE_ID-$1 sh $2
RETVAL=$?
toolbox rm --force PR-$CHANGE_ID-$1
popd
exit $RETVAL
