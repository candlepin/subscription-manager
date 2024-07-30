# TESTING

## subscription-manager

First, install the tests dependencies from [`test-requirements.txt`](test-requirements.txt). Make sure your virtual environment is activated.

```bash
pip install -r test-requirements.txt
```

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

When debugging, you may want to add `--failed-first` argument, so previously failed tests are run first:

```bash
pytest --ff
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

To disable pytest-randomly plugin, run

```bash
pytest -p no:randomly test/
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
NAME="subscription-manager"  # Or something more descriptive, like "rhsm-cs9"
podman run -it --rm \
  --name $NAME \
  -v .:/subscription-manager --workdir /subscription-manager --privileged \
  $IMAGE bash
bash scripts/container-pre-test.sh
```

Then you can run the test suite. You have to use `dbus-run-session` wrapper, because D-Bus is not running in containers:

```bash
dbus-run-session python3 -m pytest
```

### Local subscription-manager images

If you use Podman frequently, it may be worth creating local image that already has the packages pre-installed.

1. Run the commands above (`podman run ...`, `bash ...`). Do not exit the container.
2. ```bash
   IMAGENAME="subscription-manager"  # Or something more descriptive, like "rhsm-cs9-main"
   podman commit $NAME $IMAGENAME
   ```
3. Now exit the container in the first terminal.
4. Start a new container with `$IMAGENAME` instead of `$IMAGE`.
5. You can directly run pytest or other commands, no need to run the initial script again.


## Further reading

### Candlepin server

It is necessary to clone `candlepin` repo.

```shell
cd ~/src
git clone https://github.com/candlepin/candlepin.git
cd candlepin
export CANDLEPIN_VAGRANT_NO_NFS=1 
export CANDLEPIN_DEPLOY_ARGS="-gTa"
vagrant up
```

See `README.md` in the repo or [their documentation](https://www.candlepinproject.org/docs/candlepin/developer_deployment.html) for more details.
An URL of this server is `candlepin.example.com` by default.
