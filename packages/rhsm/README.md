This subpackage in the rhsm ecosystem uses pipenv to define python requirements and maintain a
virtual environment for development.

The recommended workflow is as follows:

1) Install pipenv via pip: `sudo pip install pipenv`
1) From this directory, run `pipenv --three` This creates a new virtual env for just this package
1) Run the following to install project deps in the virtualenv: `pipenv install`
1) Run the following to enter the virtual env: `pipenv shell`


From inside this virtual env you can freely install python-rhsm and test it as you like.
Just run `python ./setup.py install` to install and `python ./setup.py test` to run the tests.

The source for this subpackage is located (from checkout root) at ./src/rhsm
The tests for this subpackage is located (from checkout root) at ./test/rhsm/unit
