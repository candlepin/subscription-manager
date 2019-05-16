Product-id libdnf Plugin
========================

This libdnf plugin can be tested with microdnf or PackageKit (command line
tool is `pkcon`). It is recommended to use microdnf, because it possible to
use `printf()` for debug print. When `pkcon` is used, then it is necessary
to restart packagekit service after any change of libdnf plugin.

Requirements
------------

You have two options. You can install Fedora 29 and then install
libdnf and microdnf packages from default repositories or you can use
following steps:

* VM running Fedora 28.
* Master branch of libdnf:

  https://github.com/rpm-software-management/libdnf/

* Master branch of microdnf:

  https://github.com/rpm-software-management/microdnf

Installation of libdnf
----------------------

> Note: It is recommended to create snapshots of the VM before libdnf is
> installed to system.


    $ git clone git@github.com:rpm-software-management/libdnf.git
    $ cd libdnf
    $ sudo dnf builddep libdnf.spec
    $ mkdir build
    $ cd build
    # Configure cmake to install libdnf to /usr and not /usr/local
    $ cmake ../ -DPYTHON_DESIRED=3 -DCMAKE_INSTALL_PREFIX:PATH=/usr
    # Build libdnf
    $ make
    # Install libdnf to the system
    $ sudo make install

Building of microdnf
--------------------

> Note: it is not necessary to install microdnf to the system.

    git clone git@github.com:rpm-software-management/microdnf.git
    cd microdnf

It is recommended now to make small change of source code of
microdnf. You have to change line 102 in file `dnf/dnf-main.c` to
something like this:

```c
dnf_context_set_cache_age (ctx, 3600*24);
```

to avoid downloading metadata from repositories each time microdnf
is executed

    $ mkdir build
    $ cd build
    $ cmake ../
    $ make

You can test microdnf now and install some package:

    sudo ./dnf/microdnf install zsh

> Warning: `microdnf` install/remove package without any confirmation.
> It behaves like `dnf -y install`

Compile
-------

Building of our libdnf plugin can be triggered using this:

    $ mkdir build
    $ cd build
    $ cmake .. -DCMAKE_INSTALL_LIBDIR=/usr/lib64
    $ make
    
CMake has the concept of "in source" and "out of source" builds.  These build
types refer to the location that CMake outputs generated files to.  It is 
preferable to do an "out of source" build which is why we create the `build`
directory and then have CMake generate the Makefile there.  Among other reasons
"out of source" builds are desirable because "in source" builds wreck havoc
with CLion.

Install
-------

When plugin is compiled from source code, then you can install plugin to the system.

    $ cd build
    $ sudo make install

Testing of product-id plugin
----------------------------

You can test libdnf product-id plugin with candlepin server (e.g. in VM created
using vagrant). You have to deploy candlepin server with option `-r` like this:

```
[root@candlepin /vagrant] ./server/bin/deploy -gtar
```

To use testing repository you have to do several steps:

* Register

  ```
  subscription-manager register --username admin --password admin --org admin
  ```

* Attach some subscription:

  ```
  subscription-manager attach --pool <pool_id>
  ```

* Choose some repository from output of `subscription-manager repos --list` and
  enable the repository:
  
  ```
  subscription-manager repos --enable <repository_id>
  ```

* List RPMs in the repository:

  ```
  dnf list | grep <repository_id>
  ```

* Install RPM from given repository using `microdnf` or `pkcon`.

You should see some messages in log file: `/var/log/rhsm/productid.log`

> Note: It is important to test libdnf plugin in `microdnf` as well in `pkcon`,
  because both applications triggers libdnf plugin hooks in different ways.

Unit Tests
----------

The unit tests are built when you run `make`, but you can have CMake run them
with `make test`.  That's fine for quick checks, but if you want to see console
output from the tests or more details, run the test directly in the build
directory.  The tests also take a `--verbose` flag.  E.g.
`./test-product-id --verbose`.  There are other flags to; use `--help` to 
see them.

Not installing libdnf to the root
---------------------------------

With some extra work, you can avoid installing anything to the root filesystem.

* Run `cmake` for libdnf as follows:

  ```
  mkdir ~/libdnf
  cmake ../ -DPYTHON_DESIRED=3 -DCMAKE_INSTALL_PREFIX:PATH=~/libdnf
  ```

* Run `make` and `make install`.  The libdnf so file will be in `~/libdnf/lib64`
* Go to your microdnf checkout and run `cmake` as follows:

  ```
  PKG_CONFIG_PATH=~/libdnf/lib64/pkgconfig cmake ../
  ```

* CMake will build the make file
* Run `make` like so:

  ```
  LIBRARY_PATH=~/libdnf/lib64 make
  ```

* `microdnf` is now compiled and linked against your custom libdnf, but you
  still need to tell it how to find libdnf at runtime.  You can do this using
  the `LD_LIBRARY_PATH` environment variable although I had some trouble with
  getting that passed through when using `sudo`.  The easier way is just to
  update where the linker looks for libraries.
* Open `/etc/ld.so.conf.d/libdnf.conf` in an editor and put the text
  "HOME/libdnf/lib64" in the file (substituting your home directory for
  HOME)
* Run `ldconfig` to update the runtime bindings for the linker
* `microdnf` will now run against the `libdnf` you have in your home directory
  and you haven't messed up your root filesystem at all.
* To compile the plugin, run

  ```
  $ export CPATH=~/libdnf/include
  $ export LIBRARY_PATH=~/libdnf/lib64
  $ mkdir build
  $ cd build
  $ cmake ..
  $ make
  ```

  Those variables tell GCC where to find the necessary header files and tell
  the linker where to find the libdnf.so file.
* Make the directory `/usr/lib64/libdnf/plugins` and place the plugin's so file
  in it.  Currently libdnf only reads plugins out of this directory.  You could
  hack the source to look elsewhere.  The constant is defined in dnf-context.cpp

Debugging
---------

If you get a core dump, use `coredumpctl list` to list the coredumps you can
view.  Your most recent coredump will be at the bottom.  Get the PID and run
`coredumpctl gdb PID` where PID is the relevant PID.  Tab completion also works
for me, but I use zsh so your mileage may vary.  Once in gdb, run `gdb bt` to
see a backtrace and help you pinpoint the issue.  You can do a few other things
too.

Memory Leaks
------------

CLion will run valgrind for you with reasonable settings, but if you want to
run it yourself, start with

```
$ valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes --verbose EXECUTABLE
```

For `EXECUTABLE`, I like to run the unit test instead of `microdnf` itself.
