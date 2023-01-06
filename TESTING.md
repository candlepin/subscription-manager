# TESTING

- [subscription-manager](#subscription-manager)

## subscription-manager

```bash
pytest
# or, for increased verbosity
pytest -v
```

Some tests are disabled by default, some can be disabled manually. Defaults are stored in the `pytest.ini` file. To overwrite them, use `-m` argument.

For example, to run just the Zypper tests, execute

```bash
pytest -m "functional and zypper"
```

or, to disable DBus tests, run

```bash
pytest -m "not dbus"
```

To test specific class or function, use `::` as separator:

```bash
pytest test/test_i18n.py::TestI18N::test_text_width
```

To only run tests containing some substring, run

```bash
pytest -k cache
# or, to omit the summary, run
pytest -k cache --no-summary
```

### Plugins

- To disable pytest-randomly plugin, run

```bash
pytest -p no:randomly test/
```

- If you install `pytest-xdist` the tests can be run in parallel. The following runs in 9.67s instead of 22.41s:

```bash
pytest -n 4 --no-summary -p no:randomly -v test/
```

After all the tests are run, a warnings summary is displayed with the list of deprecations. It can be disabled with `--disable-warnings`. Whole summary can be disabled with `--no-summary`.

To compute coverage, run

```bash
coverage run
# display ASCII report
coverage report
# generate interactive HTML report to htmlcov/
coverage html
# generate XML report readable by tools like IDEs
# - PyCharm: Run > Show Coverage Data (Ctrl+Alt+6)
coverage xml
```

## Containers

You can use Podman to run the test suite, ensuring your local setup does not differ from CI.

First, pick which container you'll want to use: CentOS Stream 9, Fedora latest, Fedora Rawhide, ...:

```bash
IMAGE="quay.io/centos/centos:stream9"
IMAGE="registry.fedoraproject.org/fedora:latest"
IMAGE="registry.fedoraproject.org/fedora:rawhide"
```

Enter the container (assuming you are in the project root) and run a pre-test script that will set install the dependencies and compile C extensions:

```bash
podman run -it --rm --name subscription-manager -v .:/subscription-manager --privileged $IMAGE bash
cd /subscription-manager/
bash scripts/container-pre-test.sh
```

Then you can run the test suite. You have to use `dbus-run-session` wrapper, because D-Bus is not running in containers:

```bash
SUBMAN_TEST_IN_CONTAINER=1 dbus-run-session python3 -m pytest
```

## Further reading


## System testing

If you want to test subscription-manager in real life
there is a few players in this game:

- [candlepin server](#candlepin-server)
- [tested machine](#tested-vm)
- [proxy server](#proxy-server)
- [RHSM services](#rhsm-services)

### Initialization
#### Candlepin server
It is necessary to clone `candlepin` repo.

```shell
cd ~/src
git clone https://github.com/candlepin/candlepin.git
cd candlepin
export CANDLEPIN_VAGRANT_NO_NFS=1 
export CANDLEPIN_DEPLOY_ARGS="-gTa"
vagrant up
```
See `README.md` in the repo for more details.
An URL of this server is `candlepin.example.com` by default.

#### tested VM
There is an env variable `SUBMAN_WITH_SYSTEM_TESTS` that enables system tests when a VM is provisioned.

```shell
cd ~/src/subscription-manager
export SUBMAN_WITH_SYSTEM_TESTS=1
vagrant up
```
An URL of this VM is `centos7.subman.example.com` by default.

#### Proxy server
This is an optional player. If you want to run test cases when a proxy is used it is necessary to use some proxy server.
There is a vagrant box in Vagrantfile to make VM with squid auth proxy server.
See in `vagrant/roles/proxy-server/default/main.yml` for username, password and more details.

An URL of this server is `proxy-server.subman.example.com` and `squid` is listening on a port `3128`.

```shell
cd ~/src/subscription-manager
vagrant up proxy-server
```

#### RHSM services

RHSM services is a bunch of websocket services that offers a way to perfom some task inside a tested machine.
The service is provisioned once you set a variable `SUBMAN_WITH_SYSTEM_TESTS=1` for `vagrant up`. 
See [previous comment](#tested-vm).

A base URL of the services is `ws:/centos7.subman.example.com:9091`. 

There are a few services at the moment implemented:



- a monitor of file changes

  | what?      | that's it!                                                                                   |
  |------------|----------------------------------------------------------------------------------------------|
  | base url   | `ws://centos7.subman.example.com:9091/monitor/`                                              |
  | an example | `ws://centos7.subman.example.com:9091/monitor//etc/rhsm/rhsm.conf`                           |
  |            | `ws://centos7.subman.example.com:9091/monitor/etc/rhsm/rhsm.conf`                            |

  > if you send something back to the connection it gives you back an actual content of the file

- an execution of some command

  | what?      | that's it!                                                                   |
  |------------|------------------------------------------------------------------------------|
  | base url   | `ws://centos7.subman.example.com:9091/execute/`                              |
  | an example | `ws://centos7.subman.example.com:9091/execute//usr/bin/subscription-manager` |
  |            | `ws://centos7.subman.example.com:9091/execute/usr/bin/subscription-manager`  |

  > it is necessary to send args of the command after a connection is openned to execute the command 
  
  > for example: `register --username TEST --password PSWD --auto-attach`

##### It is a systemd service

See `/etc/systemd/system/rhsm-services` for more details.

You can see a status of the services:

```shell
systemctl status rhsm-services
```
