subscription-manager
====================
[![Docker Repository on Quay](https://quay.io/repository/candlepin/subscription-manager/status "Docker Repository on Quay")](https://quay.io/repository/candlepin/subscription-manager)
The Subscription Manager package provides programs and libraries
to allow users to manage subscriptions and yum repositories
from the  Candlepin.

 - http://candlepinproject.org/
 - https://fedorahosted.org/subscription-manager/
 - https://github.com/candlepin/subscription-Manager


Container Development Environment
---------------------------------
The current preferred and supported method for development and testing of
subscription-manager is through the use of toolbox containers.

To get started:
```bash
sudo dnf install -y toolbox
# Here we are pulling main but check the quay.io repo for other branches that
# are prebuilt
toolbox create -i quay.io/candlepin/subscription-manager:main rhsm_main
```

Then everytime you'd like to begin development you can run:
```bash

toolbox enter rhsm_main
```

These containers are used both for development, testing, and for builds.
From inside the toolbox container you should be able to run the following to
get subscription-manager installed from source:
```bash
sudo make install
```

This can be run over and over again if there are any changes you make to the
source to try out the new version.

The source can be edited from inside or outside the toolbox container and
changes will be reflected bidirectionally. This way you can use whatever IDE
you'd like on your host system to make your changes and test / play around with
it inside the container after a simple: `sudo make install`.

You can also run all the unit/stylish/tito tests (all the tests run by our
jenkins automation) within this toolbox container to help get consistent
results whether run via automation or locally.

To run the tests you can run the scripts directly from the ./jenkins folder.
An example (from inside the container):
```bash
sh jenkins/python3-tests.sh
sh jenkins/stylish-tests.sh
sh jenkins/tito-tests.sh

```



Local Installation
------------------
Consider using Vagrant instead (see below) for development as it can be a much
more consistent and easy experience.

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
PYTHONPATH=./src python -m subscription_manager.scripts.rhn_migrate_classic_to_rhsm
# ... etc.
```

(You can also just export `PYTHONPATH` instead of setting it in each command).

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

### Python 3

```bash
dnf install -y pipenv gcc make python3-devel \
    openssl-devel intltool libnl3-devel
```

You can create virtual environment using following steps:

1. Create virtual environment using Python 3 and it is necessary to
   use `--site-packages` argument, because virtual environment has to
   use `rpm` Python package installed in your system. It is not possible
   to install `rpm` Python package to virtual environment using pip/pipenv.
   ```

   Python 3:

   ```bash
   pipenv --site-packages --three
   ```

2. Install required Python packages defined in `Pipfile` into virtual environment:

   ```bash
   pipenv install
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
Edit the `vagrant/requirements.yml` file and change the src property to 
`- src: git+file:///your/development/path/to/ansible-role-subman-devel`. 
This will pull the latest commit from this path and use it for deployment. 

D-Bus Development
-----------------
In a vagrant VM, the `com.redhat.RHSM1` service along with related files 
(scripts, policy files, etc.) are linked to those from the source. However, it
is necessary to restart the D-Bus service if edits are made while it is running
with, for example, `sudo systemctl restart rhsm`.

Cockpit
-------

The easiest way to get started with cockpit plugin development is Vagrant.
Inside the VM, from the directory `/vagrant/cockpit`, the following commands
can be used:

 - `yarn install` - fetch dependencies, and update the lockfile if necessary.
 - `npm run build` - do a build of the JavaScript source.
 - `npm run watch` - monitor the source for changes and rebuild the cockpit
  plugin when necessary.

See `cockpit/README.md` for more detailed information on cockpit development.

syspurpose
---------
The syspurpose utility manages certain user-definable values tracked in
the /etc/rhsm/syspurpose/syspurpose.json file (in json format).

See ./packages/syspurpose/README.md for details on getting started


Testing
-------
We run tests using nose (see candlepinproject.org for details).  Some tests
are not run by default. For example, since we are not maintaining the GTK GUI
for all platforms, they are not run by default. They can be included via
`-a gui` option for the nose command. It is recommended if you run the GUI
tests to also use `--with-xvfb` in order to use Xvfb instead of spawning
GTK windows in your desktop session (ex. `nosetests -a gui --with-xvfb`).

[More details about testing](./TESTING.md)

Troubleshooting
---------------

If you are working inside one of the vagrant boxes and you find subscription-manager and/or
subscription-manager-gui will not work with output that looks like the following:
"Unable to find Subscription Manager module.
Error: libssl.so.10: cannot open shared object file: No such file or directory"

You should be able to run `vagrant provision [vm-name]` from the host machine to fix the issue.

This issue can happen if the python-rhsm/build or python-rhsm/build_ext directories are copied to
the virtual machine and the virtual machine provides different libraries than those available on
the build host.
