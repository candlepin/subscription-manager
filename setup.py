#!/usr/bin/env python

#
# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
import os
import sys
import subprocess

from glob import glob
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install as _install


from distutils import log
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build
from distutils.command.build_py import build_py as _build_py

# Note that importing build_ext alone won't be enough to make certain tasks (like lint) work
# those tasks require that some dependencies be installed.  Munging the syspath
# here is just so that setup.py will be able to load and run in Jenkins jobs and RPM builds
# that don't set up a proper development environment.
build_ext_home = os.path.abspath(os.path.join(os.path.dirname(__file__), "./build_ext"))
sys.path.append(build_ext_home)
from build_ext import i18n, lint, template, utils  # noqa: E402


# Read packages we should exclude from the environment
# This is used to deal with the fact that we have multiple packages which
# might be built optionally all tracked / installed via one setup.
exclude_packages = [x.strip() for x in os.environ.get("EXCLUDE_PACKAGES", "").split(",") if x != ""]
exclude_packages.extend(
    [
        "*.plugin.ostree",
        "*.services.examples",
    ]
)


PKG_VERSION = None


# subclass build_py so we can generate version.py based on --pkg-version or
# from a guess generated from 'git describe'
class pkg_version_release_build_py(_build_py):
    user_options = _build_py.user_options + [
        ("pkg-version=", None, "version and release of the PKG this is built for")
    ]

    def initialize_options(self):
        _build_py.initialize_options(self)
        self.pkg_version = None
        self.versioned_packages = []

    def finalize_options(self):
        # When --pkg-version was provided as command line
        # option of install command, then get this value from global variables
        if self.pkg_version is None and PKG_VERSION is not None:
            self.pkg_version = PKG_VERSION
        _build_py.finalize_options(self)
        self.set_undefined_options(
            "build",
            ("pkg_version", "pkg_version"),
        )

    def run(self):
        log.debug("Building with PKG_VERSION=%s" % self.pkg_version)
        _build_py.run(self)
        # create a "version.py" that includes the pkg version
        # info passed to our new build_py args
        if not self.dry_run:
            for package in self.versioned_packages:
                version_dir = os.path.join(self.build_lib, package)
                version_file = os.path.join(version_dir, "version.py")
                try:
                    lines = []
                    with open(version_file, "r") as file:
                        for line in file.readlines():
                            line = line.replace("PKG_VERSION", str(self.pkg_version))
                            lines.append(line)

                    with open(version_file, "w") as file:
                        for line in lines:
                            file.write(line)
                except EnvironmentError:
                    raise


class install(_install):
    user_options = _install.user_options + [
        ("pkg-version=", None, "version and release of the PKG this is built for"),
    ]

    def initialize_options(self):
        _install.initialize_options(self)
        self.pkg_version = None

    def finalize_options(self):
        global PKG_VERSION
        if self.pkg_version is not None:
            PKG_VERSION = self.pkg_version
        _install.finalize_options(self)
        self.set_undefined_options(
            "build",
            ("pkg_version", "pkg_version"),
        )


class build(_build):
    user_options = _build.user_options + [
        ("pkg-version=", None, "version and release of the PKG this is built for")
    ]

    def initialize_options(self):
        _build.initialize_options(self)
        self.pkg_version = None
        self.git_tag_prefix = "subscription-manager-"

    def finalize_options(self):
        # When --pkg-version was provided as command line
        # option of install command, then get this value from global variables
        if self.pkg_version is None and PKG_VERSION is not None:
            self.pkg_version = PKG_VERSION

        _build.finalize_options(self)

        # When the pkg-version was not provided as command line options,
        # then try to get such information from .git or rpm
        if not self.pkg_version:
            self.pkg_version = self.get_git_describe()

    def get_git_describe(self):
        try:
            cmd = ["git", "describe"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            output = process.communicate()[0].decode("utf-8").strip()
            if output.startswith(self.git_tag_prefix):
                return output[len(self.git_tag_prefix) :]
        except OSError:
            # When building the package there won't be a git repo to introspect so
            # builders *must* specify the version via the --pkg-version option
            return "unknown"

    def has_po_files(self):
        try:
            next(utils.Utils.find_files_of_type("po", "*.po"))
            return True
        except StopIteration:
            return False

    sub_commands = _build.sub_commands + [("build_trans", has_po_files), ("build_template", lambda arg: True)]


class install_data(_install_data):
    """Used to intelligently install data files.  For example, files that must be generated
    (such as .mo files) or an entire tree of data files."""

    user_options = _install_data.user_options + []

    def initialize_options(self):
        _install_data.initialize_options(self)
        # Can't use super() because Command isn't a new-style class.

    def finalize_options(self):
        _install_data.finalize_options(self)

    def run(self):
        self.add_messages()
        self.add_dbus_service_files()
        self.add_systemd_services()
        _install_data.run(self)

    def join(self, *args):
        return os.path.normpath(os.path.join(*args))

    def add_messages(self):
        for lang in os.listdir(self.join("build", "locale")):
            lang_dir = self.join("share", "locale", lang, "LC_MESSAGES")
            lang_file = self.join("build", "locale", lang, "LC_MESSAGES", "rhsm.mo")
            self.data_files.append((lang_dir, [lang_file]))

    def add_dbus_service_files(self):
        """
        Add D-Bus service files to the list of files installed to the system
        """
        dbus_service_directory = self.join("share", "dbus-1", "system-services")
        source_dir = self.join("build", "dbus", "system-services-systemd")
        for template_file in os.listdir(source_dir):
            self.data_files.append((dbus_service_directory, [self.join(source_dir, template_file)]))

    def add_systemd_services(self):
        """
        Add .service files for systemd
        """
        systemd_install_directory = self.join("lib", "systemd", "system")
        source_dir = self.join("build", "dbus", "systemd")
        for file in os.listdir(self.join("build", "dbus", "systemd")):
            self.data_files.append((systemd_install_directory, [self.join(source_dir, file)]))


class GettextWithArgparse(i18n.Gettext):
    def find_py(self):
        # Can't use super since we're descended from a old-style class
        files = i18n.Gettext.find_py(self)

        # We need to grab some strings out of argparse for translation
        import argparse

        argparse_source = "%s.py" % os.path.splitext(argparse.__file__)[0]
        if not os.path.exists(argparse_source):
            raise RuntimeError("Could not find argparse.py at %s" % argparse_source)
        files.append(argparse_source)
        return files


setup_requires = []

install_requires = [
    "iniparse",
    "python-dateutil",
    "dbus-python",
]

test_require = (
    [
        "pytest",
        "pytest-randomly",
        "pytest-timeout",
        "coverage",
        "polib",
        "flake8",
    ]
    + install_requires
    + setup_requires
)

cmdclass = {
    "clean": utils.clean,
    "install": install,
    "install_data": install_data,
    "build": build,
    "build_py": pkg_version_release_build_py,
    "build_trans": i18n.BuildTrans,
    "build_template": template.BuildTemplate,
    "update_trans": i18n.UpdateTrans,
    "uniq_trans": i18n.UniqTrans,
    "gettext": GettextWithArgparse,
    "lint": lint.Lint,
    "lint_rpm": lint.RpmLint,
    "flake8": lint.Flake8,
}

setup(
    name="subscription-manager",
    version="1.29.47.1",
    url="http://www.candlepinproject.org",
    description="Manage subscriptions for Red Hat products.",
    license="GPLv2",
    author="Adrian Likins",
    author_email="alikins@redhat.com",
    cmdclass=cmdclass,
    packages=find_packages("src", exclude=exclude_packages),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "subscription-manager = subscription_manager.scripts.subscription_manager:main",
            "rct = subscription_manager.scripts.rct:main",
            "rhsm-debug = subscription_manager.scripts.rhsm_debug:main",
            "rhsm-facts-service = subscription_manager.scripts.rhsm_facts_service:main",
            "rhsm-service = subscription_manager.scripts.rhsm_service:main",
            "rhsmcertd-worker = subscription_manager.scripts.rhsmcertd_worker:main",
            "rhsm-package-profile-uploader = subscription_manager.scripts.package_profile_upload:main",
        ],
    },
    data_files=[
        # man pages for gui are added in add_gui_doc_files(), when GUI package is created
        ("share/man/man8", set(glob("man/*.8"))),
        ("share/man/man5", glob("man/*.5")),
    ],
    command_options={
        "egg_info": {
            "egg_base": ("setup.py", os.curdir),
        },
        "build_py": {
            "versioned_packages": ("setup.py", ["subscription_manager", "rct"]),
        },
    },
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL License",
        "Operating System :: Linux",
    ],
    include_package_data=True,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=test_require,
    ext_modules=[
        Extension("rhsm._certificate", ["src/certificate.c"], libraries=["ssl", "crypto"]),
    ],
)
