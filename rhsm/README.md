Python-RHSM
===========

python-rhsm is a small Python wrapper for making REST calls to a Candlepin
Subscription Management Engine. Information about this library and Candlepin
can be found at: 

http://www.candlepinproject.org

To use, create an `rhsm.connection.UEPConnection` object and examine the methods
it provides. The vast majority of what this library offers is on this class.

Installing package
------------------

This Python package is part of all RHEL distibutions and it is strongly
recommended to use only rhsm package provided by RPM. It is also possible
to install this package on Fedora using:

    $ sudo dnf install python3-subscription-manager-rhsm

When you use some other Linux distribution (Debian, SuSE, etc.), then it is
possible to install rhsm python package using:

    $ pip install rhsm

Uploading package to the pypi.org
---------------------------------

First delete everything in the distribution directory

    $ rm -rf dist

Then create only source package using:

    $ python3 setup.py sdist

> Note: Do not try to create wheel distribution using `python 3 setup.py bdist_wheel`,
> because the package would contain binary module `_certificate.so`. This module has
> too many dependencies and it is not possible to create portable binary package.

Then try to upload source package to the testing repository:

    $ python3 -m twine upload --verbose --repository testpypi dist/*

When it was possible to upload package to the testing repository, then try to
install the rhsm package in e.g. pipenv environment:

    $ pipenv --three
    $ pipenv shell
    $ python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps rhsm

After smoke testing of rhsm package in the virtual environment it is possible to
upload package to production repository:

    $ python3 -m twine upload --verbose dist/*