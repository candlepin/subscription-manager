#!/usr/bin/env bash

project_root=$(git rev-parse --show-toplevel)
ctr1=$(buildah from "${1:-fedora}")
echo $ctr1
## Get all updates and install our minimal httpd server
#buildah run "$ctr1" -- dnf update -y
buildah run "$ctr1" -- dnf install git -y
#buildah run "$ctr1" -- # todo: find a way to install all subman build requirements
#buildah rename "$ctr1" "subman_dev_fedora"
buildah tag "$ctr1" $($project_root/containers/dependency_fingerprint.sh)
