subscription-manager
====================

The Subscription Manager package provides programs and libraries
to allow users to manage subscriptions and DNF repositories
from the Candlepin.

 - https://candlepinproject.org/
 - https://github.com/candlepin/subscription-manager

Local Installation
------------------

In order to build, develop, and test locally, please follow
[INSTALL.md](INSTALL.md).

For instructions on building the debian-packages of this project, see instructions in [contrib/debian/README.source](contrib/debian/README.source).

To ignore bulk commits that only change the format of the code, not the code
itself (e.g. `black`ing whole codebase), add `.git-blame-ignore-revs` to your
git configuration:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Development of the Subscription-Manager Deployment Ansible role
---------------------------------------------------------------
The Ansible role that is used for deploying subscription-manager can be found at 
https://github.com/candlepin/ansible-role-subman-devel. In order to test 
changes for this Ansible role you will need to check it out locally. 
This will pull the latest commit from this path and use it for deployment. 

Testing
-------
We run tests using pytest. [See TESTING.md for more details.](./TESTING.md)
