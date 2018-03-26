
# Testing of the game

- [System testing](#system-testing)
- [Cockpit Subscriptions Plugin Tests](#cockpit-subscriptions-plugin-tests)


## System testing

If you want to test subscription-manager or cockpit plugin in real life
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

## Cockpit Subscriptions Plugin Tests
The tests live in its own repo actually. They fire up firefox and play with Cockpit Subscription Plugin.

```shell
cd ~/src
git clone https://github.com/RedHatQE/rhsm-cockpit-qe.git
cd rhsm-cockpit-qe
npm install
npm run e2e-setup
```

It is important to install `npm` since it uses `nodejs ecosystem`.

### Run them!

```shell
cd rhsm-cockpit-qe
npm run test
```

If you want to run just one test specification:
```shell
./node_modules/.bin/wdio wdio.conf.js test/spec/proxy-dialog.js
```

### Configuration is super duper easy
Configuration follows a style of [The Twelve-Factor App](https://12factor.net/config)

```shell
cd rhsm-cockpit-qe
cp env-example .env
vim .env
```

See [env2 repo](https://github.com/dwyl/env2) for more details.

### Stop firefox run!

If you want to stop running of a test at the right moment
you can set `browser.debug()` in the code line whatever you want.

WDIO executer stops running and offers you a REPL console. 

See [Debugging of WebdriverIO test](http://webdriver.io/guide/testrunner/debugging.html) for details.

### Extending of the tests

There are page objects that describe the main parts of Cockpit Subscription web application.

see `rhsm-cockpit-qe/page_objects`.

Each page object desribes main parts and main operations on a proper web dialog, web page.
This kind of separation of concern help developers to write well readable tests.
See http://webdriver.io/guide/testrunner/pageobjects.html for more details.
