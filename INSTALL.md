# Installation

The subscription-manager codebase is on [GitHub](https://github.com/candlepin/subscription-manager).
The project is built for the latest versions of Fedora (and submitted to Fedora Updates), CentOS Stream and RHEL.

To install subscription-manager, run

```bash
sudo dnf install subscription-manager
```

## Developer installation

The process below has been tested on Fedora 36.
Other Fedora versions or distributions may require some adaptation.

1. First you need to install RPM packages to build and run subscription-manager binaries:

   ```bash
   sudo dnf install git gcc python3-devel openssl-devel glib2-devel \
       python3-rpm python3-librepo libdnf-devel cmake
   ```

   <!-- libdnf-devel, cmake are required to build product-id plugin -->

2. Install Fedora's subscription-manager RPM and packages required to run the test suite:

   ***NOTE**: Installing `subscription-manager` package is strictly not necessary, but it will pull down all dependencies and create all the files used by subscription-manager.*

   ```bash
   sudo dnf install --setopt install_weak_deps=False subscription-manager \
       dbus-daemon glibc-langpack-en glibc-langpack-de glibc-langpack-ja
   ```

3. Install Python packages in virtual environment to prevent polluting userspace:
 
   ***NOTE**: This step is optional.*

   ```bash
   sudo dnf install python3-pip
   mkdir -p ~/.venvs/
   python3 -m venv --system-site-packages ~/.venvs/subscription-manager
   source ~/.venvs/subscription-manager/bin/activate
   python3 -m pip install wheel
   ```

4. Clone the repository:

   ```bash
   git clone https://github.com/candlepin/subscription-manager.git
   cd subscription-manager/
   ```

5. Build the project:

   ```
   ./setup.py build
   ./setup.py build_ext --inplace
   ```

6. Test your local installation:

   ```bash
   sudo PYTHONPATH=./src python3 -m subscription_manager.scripts.subscription_manager
   ```
   
   ***NOTE**: Adjust the path accordingly.*

   You can setup an alias in `.bashrc` (or equivalent), so you can run it more easily:

   ```bash
   alias subscription-manager="sudo \
       PYTHONPATH=/path/to/subscription-manager/src \
       $(which python3) \
       -m subscription_manager.scripts.subscription_manager"
   ```

7. You can also set up aliases for rhsm.service and rhsmcertd.service.

   ***NOTE**: Adjust the paths accordingly.*

   ```bash
   alias rhsm-service="sudo \
       PYTHONPATH=/path/to/subscription-manager/src \
       $(which python3) \
       -m subscription_manager.scripts.rhsm_service --verbose"
   alias rhsmcertd="sudo \
       PYTHONPATH=/path/to/subscription-manager/src \
       $(which python3) \
       -m subscription_manager.scripts.rhsmcertd_worker --autoheal"
   ```

   Before you run rhsm service manually, ensure you have disabled the system service first:

   ```bash
   sudo systemctl stop rhsm.service
   ```
