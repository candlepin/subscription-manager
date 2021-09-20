#!/bin/bash -x
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

if [ -z "$CHANGE_ID"]; then
    TAG="latest"
else
    TAG="PR-$CHANGE_ID"
fi
# Run one of our tests inside a newly created toolbox container
echo "Using container image tag: $TAG"

if (( $# != 2)); then
    >&2 cat << EOF
    This script requires two arguments.

    Usage: $0 [END_OF_TAG] [PATH_TO_SCRIPT_TO_RUN_IN_CONTAINER]
    This script will create a toolbox container, run the script provided in it, and forcefully destroy the toolbox container.
EOF
    exit
fi

pushd "$PROJECT_ROOT" || exit 1
toolbox create -i "quay.io/candlepin/subscription-manager:$TAG" -c "$TAG-$1"
toolbox run -c "$TAG-$1" sh "$2"
RETVAL=$?
toolbox rm --force "$TAG-$1"
popd
exit "$RETVAL"
