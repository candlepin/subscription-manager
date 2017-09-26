# Subscription-manager
**A Cockpit plugin to administer candlepin subscriptions**

Development Quickstart
----------------------
Run `vagrant up`. subscription-manager cockpit plugin code lands in
`/vagrant/cockpit`.

Once the VM is up, cockpit is accessible via https://centos7.subman.example.com:9090 (must have vagrant hostmanager plugin installed). The fedora VM works similarly.

NPM scripts (documented below) should be used to rebuild plugin artifacts when
code is edited.

Development Outside of Vagrant
------------------------------
 - `nvm` is recommended but not required (https://github.com/creationix/nvm).
 - `yarn` needs to be installed globally (`npm install -g yarn`).
 - `yarn install` needs to be run from the `cockpit` subdirectory.

With these steps, the cockpit plugin code can be built from the host.

Yarn
----
Yarn is used to install, remove, and update NPM packages for the plugin.

The most common commands are:
 - `yarn add <package> --dev`: Add a JavaScript dependency.
 - `yarn install`: Install JavaScript dependencies and update the lockfile if
   necessary.

(See https://yarnpkg.com for more details on using yarn).

NPM Scripts
-----------
There are several commands configured in `package.json`, these should be run
from the `cockpit` subdirectory:
 - `npm run build` - do a build of the JavaScript source with results in `dist`
 - `npm run watch` - monitor the source for changes and rebuild the cockpit
   plugin when necessary.
 - `npm run vagrant-watch`: same as `npm run watch`, and also invokes
   `vagrant rsync-auto`. Useful if you want to develop on the host and see the
   effects in a VM.
