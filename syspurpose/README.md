# Getting started developing the syspurpose utility

This subpackage in the rhsm ecosystem uses pipenv to define python requirements and maintain a
virtual environment for development.

The recommended workflow is as follows:

1) Install pipenv via pip: `sudo pip install pipenv`
1) From this directory, run `pipenv --three` This creates a new virtual env for just this package
1) Run the following to install project deps and test deps in the virtualenv: `pipenv install --dev`
1) Run the following to enter the virtual env: `pipenv shell`

From inside this virtual env you can freely install the syspurpose tool and test it as you like.
Just run `python ./setup.py install` to install and `python ./setup.py test` to run the tests.
