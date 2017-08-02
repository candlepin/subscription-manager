# Subscription-manager
**A Cockpit plugin to administer candlepin subscriptions**

See [docs/build-notes.md](docs/build-notes.md) for more information on how to build and install this package.

Development Quickstart
----------------------
To install necessary libraries & get a development VM provisioned:

```bash
sudo dnf install -y npm
sudo npm install -g yarn
yarn install
vagrant up
```

Once the VM is up, cockpit is accessible via https://centos7.subman.example.com:9090 (must have vagrant hostmanager plugin installed). The fedora VM works similarly.

Afterwards:
```bash
npm run watch  # shortcut to webpack --watch & vagrant rsync-auto
```

Then any changes to `src/*` will be picked up by webpack and built, and subsequently synced to the VM.