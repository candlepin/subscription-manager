#!/bin/bash -x
PROJECT_ROOT="$(git rev-parse --show-toplevel)"


# The CHANGE_ID environment variable is set by Jenkins for multibranch jobs.
# It's value is generally the PR number. This is not set anywhere by our
# bits (yet).
if [ -z "$CHANGE_ID" ]; then
    TAG="latest"
else
    TAG="PR-$CHANGE_ID"
fi
# Run one of our tests inside a newly created toolbox container
echo "Using container image tag: $TAG"

if (( $# != 2 )); then
    >&2 cat << EOF
    This script requires two arguments.

    Usage: $0 [END_OF_TAG] [PATH_TO_SCRIPT_TO_RUN_IN_CONTAINER]
    This script will create a toolbox container, run the script provided in it, and forcefully destroy the toolbox container.
EOF
    exit
fi

pushd "$PROJECT_ROOT" || exit 1
toolbox create -y -i "quay.io/candlepin/subscription-manager:$TAG" -c "$TAG-$1"
toolbox run -c "$TAG-$1" sh jenkins/run.sh "$1" "$2"

if test -f "test_results/$1.txt"; then
    RETVAL="$(tail -1 test_results/$1.txt | awk '{ print $2 }')"
else
    RETVAL=1
fi

toolbox rm --force "$TAG-$1"
popd
exit "$RETVAL"