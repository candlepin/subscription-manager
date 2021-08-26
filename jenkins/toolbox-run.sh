#!/bin/bash -x
PROJECT_ROOT=$(git rev-parse --show-toplevel)

# Run one of our tests inside a newly created toolbox container

pushd $PROJECT_ROOT
toolbox create -i quay.io/candlepin/subscription-manager:PR-$CHANGE_ID -c PR-$CHANGE_ID-$1
toolbox run -c PR-$CHANGE_ID-$1 sh $2
RETVAL=$?
toolbox rm --force PR-$CHANGE_ID-$1
popd
exit $RETVAL
