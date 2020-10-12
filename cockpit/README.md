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
> An important note for Red Hat developers: If you develop the cockpit
plugin outside of the Red Hat office, no changes to the configuration file are
needed . If you are Red Hat developer working in the Red Hat office, then please use
our internal cache of the nmpjs repository called Nexus. Configure
npm with:

`npm config set registry https://repository.engineering.redhat.com/nexus/repository/registry.npmjs.org`

 - `nvm` is recommended but not required (https://github.com/creationix/nvm).
 - `npm install` needs to be run from the `cockpit` subdirectory.

With these steps, the cockpit plugin code can be built from the host.

NPM
----
NPM is used to install, remove, and update js packages for the plugin.

The most common commands are:
 - `npm add <package> --dev`: Add a JavaScript dependency.
 - `npm install`: Install JavaScript dependencies and update the lockfile if
   necessary.
 - `npm shrinkwrap`: Lock the current dependencies into lockfile.

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
