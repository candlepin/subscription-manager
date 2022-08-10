FROM registry.fedoraproject.org/fedora:34

MAINTAINER "Candlepin Team" <candlepin@redhat.com>
# should be the UID of whatever user is running podman, change this with: podman build --build-arg UID="$(id -u)"
ARG UID=1000
ARG GIT_HASH=main
ENV SMDEV_CONTAINER_OFF='True'

RUN dnf -y update

RUN dnf install -y \
    cmake \
    dbus-daemon \
    dnf-utils \
    gcc \
    gettext \
    git \
    glibc-langpack-de \
    glibc-langpack-en \
    glibc-langpack-ja \
    json-c-devel \
    libdnf-devel \
    make \
    openssl \
    openssl-devel \
    procps-ng \
    python3-coverage \
    python3-dateutil \
    python3-decorator \
    python3-devel \
    python3-ethtool \
    python3-gobject-base \
    python3-iniparse \
    python3-inotify \
    python3-librepo \
    python3-mock \
    python3-pip \
    python3-polib \
    python3-pytest \
    python3-pytest-flake8 \
    python3-pytest-forked \
    python3-pytest-randomly \
    python3-pytest-timeout \
    python3-requests \
    python3-rpm \
    python3-simplejson \
    python3-virtualenv \
    redhat-rpm-config \
    rpm-build \
    rpmlint \
    subscription-manager-rhsm-certificates \
    sudo \
    tito \
    vim \
    wget \
    && dnf clean all

RUN useradd -u ${UID} -m user && usermod -aG wheel user && \
    chown -R user:user /home/user && \
    echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

RUN echo "export SMDEV_CONTAINER_OFF='True'" >> /root/.bashrc && \
    echo "export SMDEV_CONTAINER_OFF='True'" >> /root/.zshrc

RUN mkdir /build
COPY requirements.txt dev-requirements.txt test-requirements.txt /build/
COPY build_ext /build/build_ext
WORKDIR /build
RUN pip3 install -r dev-requirements.txt && \
    git clone https://github.com/candlepin/subscription-manager.git && \
    cd /build/subscription-manager && \
    git config --add remote.origin.fetch +refs/pull/*/head:refs/remotes/origin/pr/* && \
    git fetch && \
    git checkout $GIT_HASH && \
    dnf builddep -y ./subscription-manager.spec && \
    python3 ./setup.py build && \
    python3 ./setup.py build_ext --inplace

RUN chown -R user:user /build
USER user
ENV DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/bus'
RUN echo "export SMDEV_CONTAINER_OFF='True'" >> /home/user/.bashrc && \
    echo "export SMDEV_CONTAINER_OFF='True'" >> /home/user/.zshrc
WORKDIR /build/subscription-manager
