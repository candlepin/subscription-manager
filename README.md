subscription-manager
====================

The Subscription Manager package provides programs and libraries
to allow users to manage subscriptions and yum repositories
from the  Candlepin.

 - http://candlepinproject.org/
 - https://fedorahosted.org/subscription-manager/
 - https://github.com/candlepin/subscription-Manager

Local Installation
------------------

In order to build, develop, and test locally, please follow
[instructions at candlepinproject.org](http://www.candlepinproject.org/docs/subscription-manager/installation.html#installation-of-upstream-from-source-code).

For instructions on building the debian-packages of this project, see instructions in contrib/debian/README.source.

Due to unintuitive behavior with `sys.path`
(see https://github.com/asottile/scratch/wiki/PythonPathSadness),
`python src/subscription_manager/scripts/subscription_manager.py` does not work
as expected. One can run the script like this instead:

```bash
PYTHONPATH=./src python -m subscription_manager.scripts.subscription_manager
```

Similar for other bin scripts:

```bash
PYTHONPATH=./src python -m subscription_manager.scripts.rct
# ... etc.
```

(You can also just export `PYTHONPATH` instead of setting it in each command).

To ignore bulk commits that only change the format of the code, not the code
itself (e.g. `black`ing whole codebase), add `.git-blame-ignore-revs` to your
git configuration:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Pipenv
------

There is experimental support for installation of subscription-manager using
Pipenv. We tested installing subscription-manager using Pipenv only on following
operating systems:

* Fedora 30
* RHEL/CentOS 7
* RHEL/CentOS 8

We tested pipenv with Python 2 and Python 3. It is necessary to install following
packages to your system, because binary module have to be compiled in virtual
environment:

### Python 2

```bash
dnf install -y pipenv gcc make python2-devel \
    openssl-devel libnl3-devel
```

### Python 3

```bash
dnf install -y pipenv gcc make python3-devel \
    openssl-devel libnl3-devel
```

You can create virtual environment using following steps:

1. Create virtual environment using Python 2 or Python 3 and it is necessary to
   use `--site-packages` argument, because virtual environment has to
   use `rpm` Python package installed in your system. It is not possible
   to install `rpm` Python package to virtual environment using pip/pipenv.

   Python 2:

   ```bash
   pipenv --site-packages --two
   ```

   Python 3:

   ```bash
   pipenv --site-packages --three
   ```

2. Install required Python packages defined in `Pipfile` into virtual environment:

   ```bash
   pipevn install
   ```

3. Start virtual environment:

   ```bash
   pipenv shell
   ```

4. Build binary modules in virtual environment:

   ```bash
   python ./setup.py build
   ```

5. Install subscription-manager into virtual environment:

   ```bash
   python ./setup.py install
   ```

6. It should be possible to run subscription-manager in virtual environment

   ```bash
   sudo subscription-manager version
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
