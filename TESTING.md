# TESTING

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

To run tests in virtual machine or container without GUI, where DBus is not running, you can start it on-demand:

```bash
dbus-run-session pytest
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
