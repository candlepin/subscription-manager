#!/bin/bash
#
# A local candlepin is used for most of integration tests.
# It is fast to run the tests and the candlepin comes with testing data.
# So the environment is mostly prepared in the candlepin after we run a contianer.
#
# For most information see https://github.com/ptoscano/candlepin-container-unofficial
#
podman run -d --name candlepin -p 8080:8080 -p 8443:8443 --hostname candlepin.local ghcr.io/ptoscano/candlepin-unofficial:latest
