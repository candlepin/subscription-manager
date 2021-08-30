Subscription Manager & Containers
=================================

This directory contains scripts and configuration files that are necessary for running
subscription-manager in a containerized environment. This environment could be created
using podman. Why do we care about running subscription-manager in a containerized
environment? We believe that it could be useful for testing of subscription-manager.
We also support running and testing of subscription-manager using vagrant, but running
subscription-manager in VM could be a bit cumbersome. Running subscription-manager
using podman could be more flexible for developers too.

Requirements
------------

To create and use a containerized environment it is necessary to have following packages
installed in the system:

 * podman
 * toolbox

   $ sudo dnf install -y podman toolbox

Create a containerized environment
----------------------------------

To create a containerized environment you can simply run following script:

    $ toolbox create -i quay.io/candlepin/subscription-manager:main -c rhsm-dev
    $ toolbox enter rhsm-dev

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
    $ toolbox create -i quay.io/candlepin/subscription-manager:PR-XXXX -c PR-XXXX
    $ toolbox run -c PR-XXXX ./jenkins/unit.sh

Running the following will let you work like normal from within the environment
    $ toolbox enter PR-XXXX
