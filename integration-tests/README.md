# Integration Test for subscription-manager

There are integration tests for all parts of subscription-manager 
in this directory.

DBus tests are presented currently - they verify DBus api of *rhsm.service*
see [DBus objects](https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html)

The tests use pytest ecosystem.

## Installation

1) Run local candlepin

```shell
podman run -d --name canlepin -p 8080:8080 -p 8443:8443 --hostname candlepin.local ghcr.io/ptoscano/candlepin-unofficial:latest
```

2) Create additional testing data in candlepin

Environments for *donaldduck* organization

```
curl --stderr /dev/null --insecure --user admin:admin --request POST \
--data '{"id": "env-id-1", "name": "env-name-1", "description": "Testing environment num. 1"}' \
--header 'accept: application/json' --header 'content-type: application/json' \
https://localhost:8443/candlepin/owners/donaldduck/environments

curl --stderr /dev/null --insecure --user admin:admin --request POST \
--data '{"id": "env-id-2", "name": "env-name-2", "description": "Testing environment num. 2"}' \
--header 'accept: application/json' --header 'content-type: application/json' \
https://localhost:8443/candlepin/owners/donaldduck/environments
```

> citation from 'man subscription-manager'
>   With on-premise subscription services, such as Subscription Asset
>   Manager, the infrastructure is more complex. The local
>   administrator can define independent groups called organizations 
>   which represent physical  or  organizational divisions (--org). 
>   Those organizations can be subdivided into environments.

Activation keys for *donaldduck* organization

> The tests use already installed test activation keys
> They are:
>  - *default_key*
>  - *awesome_os_pool"

## Configuration

Tests use [Dynaconf](https://www.dynaconf.com/) to load config
values.

They are stored in a file in this directory *settings.toml*

Config values for _testing_ environment

```yaml
[testing]
candlepin.host = "localhost"
candlepin.port = 8443
candlepin.insecure = true
candlepin.prefix = "/candlepin"
candlepin.username = "duey"
candlepin.password = "password"
candlepin.org = "donaldduck"
candlepin.activation_keys = ["default_key","awesome_os_pool"]
candlepin.environment.names = ["env-name-01","env-name-02"]
candlepin.environment.ids =   ["env-id-01","env-id-02"]

insights.legacy_upload = false
console.host = "cert.console.redhat.com"

auth_proxy.host = 
auth_proxy.port = 3127
auth_proxy.username = "redhat"
auth_proxy.password = "redhat"

noauth_proxy.host = 
noauth_proxy.port = 3129

insights.hbi_host = "cert.console.redhat.com"
```

Configuration for pytest 

> There is a file *pytest.ini* in the main directory of this repo.
> It has nothing to do with integration-tests. It is a confiuration
> for unittests.

*integration-tests/pytest.ini*

```ini
[pytest]
addopts = "-srxv --capture=sys"
testpaths = "./"
log_cli = true
log_level = INFO
```

## Python virtual environment for testing

It is good practice to use python virtual environment to run the
tests. All required packages for pytest are stored in
*requirements.txt*.

> There is a file *requirements.txt* in the main directory of the
> repo. It is used by unittests. I has nothing to do with
> integration-tests at all.

```shell
cd integration-tests
python3 -mvenv venv
source venv
pip install -r requirements.txt
deactivate
```

## Running the tests

```shell
cd integration-tests
source venv
pytest
deativate
```

> There is a nice help for pytest in [Testing](../TESTING.md). It is
> full of interesting hits to run just a few tests, to increase output
> of a test run ...

### Runnning integration tests using tmt

You can use [Testing Farm](https://docs.testing-farm.io/Testing%20Farm/0.1/index.html) 
to run the tests.

It suposes that the package *subscription-manager* is installed at a local box.

```shell
cd subscription-manager
sudo tmt --feeling-safe run -vvv --all provision --how local
```

> All details for tmt to run are stored at directory *systemtest*
> It is a starting point for deeper investigation to understand how
> the tests are run using tmt.
