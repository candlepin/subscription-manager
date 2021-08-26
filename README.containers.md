Subscription Manager & Containers
=================================

This directory contains scripts and configuration files that are necessary for running
subscription-manager in a containerized environment. This environment could be created
using podman. Why do we care about running subscription-manager in a containerized
environment? We believe that it could be useful for testing of subscription-manager.
Running subscription-manager using podman could be more flexible for developers too.

Requirements
------------

To create and use a containerized environment it is necessary to have following packages
installed in the system:

 * podman

   $ sudo dnf install -y podman

Create a containerized environment
----------------------------------

To create a containerized environment you can simply run following script:

    $ podman build -f ./Containerfile --build-arg UID="$(id -u)" -t subman
    $ podman run -it --rm -v /run/user/$UID/bus:/tmp/bus subman /bin/bash

The above will create a clean sandbox in which to run tests reliably and
test out subscription-manager.

To do development locally and have the changes reflected locally (inside the con
tainer) do the following run command from the base subscription-manager source
directory:

    $ podman run -t --rm -v /run/user/$UID/bus:/tmp/bus -v $PWD:/home/jenkins/subman:Z -w /home/jenkins/subman subman /bin/bash

Reviewing PRs
-------------

Jenkins will build, tag, and push the PR test environment to
quay.io/candlepin/subscription-manager:PR-XXXX where XXXX is the PR number.
This is done as a regular part of the jenkins tests as each test is run in
one of these containers.

This means that for any PR which has had the jenkins tests complete
(regardless of success or failure), you can run the following to reproduce
the jenkins test results (for example if the unit tests failed):

    $ git checkout origin pr/XXXX
    $ podman run -it quay.io/candlepin/subscription-manager:PR-XXXX sh ./jenkins/unit.sh

One can also run the following (for the unit tests or for any tests that jenkins
runs) (the CHANGE_ID should be the PR number that you are reproducing):

    $ CHANGE_ID=XXXX ./jenkins/run.sh ./jenkins/unit.sh
