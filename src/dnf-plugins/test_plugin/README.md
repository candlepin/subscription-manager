Hello World libdnf Plugin
=========================

This libdnf plugin can be tested with microdnf or PackageKit (command line
tool is `pkcon`). It is recommended to use microdnf, because it possible to
use `printf()` for debug print. When `pkcon` is used, then it is necessary
to restart packagekit service after any change of libdnf plugin.

Requirements
------------

* VM running Fedora 28.
* Feature branch of libdnf created by Jaroslav Rohel:

  https://github.com/jrohel/libdnf/tree/feature/plugins

* You have to use master branch of microdnf it is available here:

  https://github.com/rpm-software-management/microdnf

Installation of libdnf
----------------------

> Note: It is recommended to create snapshots of the VM before libdnf is
> installed to system.

    git clone git@github.com:jrohel/libdnf.git
    cd libdnf
    git checkout feature/plugins
    sudo dnf builddep libdnf.spec
    mkdir build
    cd build
    # Configure cmake to install libdnf to /usr and not /usr/local
    cmake ../ -DPYTHON_DESIRED=3 -DCMAKE_INSTALL_PREFIX:PATH=/usr
    # Build libdnf
    make
    # Install libdnf to the system
    sudo make install

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

    mkdir build
    cd build
    cmake ../
    make

You can test microdnf now and install some package:

    sudo ./dnf/microdnf install zsh

> Warning: `microdnf` install/remove package without any confirmation.
> It behaves like `dnf -y install`

Compile
-------

Building of our libdnf plugin can be triggered using this:

    $ make

Install
-------

We are not providing make install in Makefile. Thus it has to be
installed in this way:

    $ sudo cp hello_dnf.so /usr/lib64/libdnf/plugins/hello_dnf.so

Testing of our plugin
---------------------

You should be able to see some extra debug messages, when `microdnf`
is used.

    sudo ./dnf/microdnf install zsh

It also creates log file `/tmp/libdnf_plugin.log` and it writes
some timestamps there (useful for testing of `pkcon`).

Not installing to the root
--------------------------

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
* Run `make` list so:

  ```
  LIBRARY_PATH=$HOME/libdnf/lib64 make
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
* To compile the sample plugin, run

  ```
  CPATH=~/libdnf/include make
  ```
* Make the directory `/usr/lib64/libdnf/plugins` and place the plugin's so file
  in it.  Currently libdnf only reads plugins out of this directory.  You could
  hack the source to look elsewhere.  The constant is defined in dnf-context.cpp
