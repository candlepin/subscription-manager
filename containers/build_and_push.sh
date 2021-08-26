#!/bin/bash -x
CURRENT_GIT_HASH="$(git rev-parse HEAD)"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

pushd "$PROJECT_ROOT" || exit 1
podman build -f ./containers/Containerfile -t "quay.io/candlepin/subscription-manager:$CURRENT_GIT_HASH"
podman push --creds "$QUAY_CREDS" "quay.io/candlepin/subscription-manager:$CURRENT_GIT_HASH"
podman tag "quay.io/candlepin/subscription-manager:$CURRENT_GIT_HASH" "quay.io/candlepin/subscription-manager:PR-$CHANGE_ID"
podman push --creds "$QUAY_CREDS" "quay.io/candlepin/subscription-manager:PR-$CHANGE_ID"
popd || exit 1
