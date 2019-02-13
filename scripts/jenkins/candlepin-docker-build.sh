#!/bin/bash -xe

echo $USER
groups $USER
env

echo "Using workspace: $WORKSPACE"
docker --version

docker login -u unused -p "$DOCKER_API_TOKEN" docker-registry.engineering.redhat.com
./docker/build-images -p
