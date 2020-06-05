Subscription Manager & Podman
=============================

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
 * buildah

Create a containerized environment
----------------------------------

To create a containerized environment you can simply run following script:

    $ ./build.sh

Or you can build an image using:

    $ podman build -f ./Containerfile -t test-subman

This script will download base images. Then all required rpm images defined in the Containerfile
will be installed into the container. To run the test image use following command:

    $ podman run -it localhost/testenv