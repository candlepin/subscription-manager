#!/bin/bash -x
set -e
if [ -z "$GIT_HASH" ]; then
    TAG="$(git rev-parse HEAD)"
else
    TAG="$GIT_HASH"
fi

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

pushd "$PROJECT_ROOT"
podman build -f ./Containerfile --build-arg UID="$(id -u)" --build-arg GIT_HASH="pr/$CHANGE_ID" -t "quay.io/candlepin/subscription-manager:$TAG"
podman push --creds "$QUAY_CREDS" "quay.io/candlepin/subscription-manager:$TAG"
podman tag "quay.io/candlepin/subscription-manager:$TAG" "quay.io/candlepin/subscription-manager:PR-$CHANGE_ID"
podman push --creds "$QUAY_CREDS" "quay.io/candlepin/subscription-manager:PR-$CHANGE_ID"
popd
