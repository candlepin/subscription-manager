#!/bin/bash
set -e
CHECKOUT=$(git rev-parse --show-toplevel)
which ansible >/dev/null || sudo dnf -y install ansible
ansible-galaxy install --ignore-errors -r "$CHECKOUT/vagrant/requirements.yml"
ansible-playbook -e subman_checkout_dir="$CHECKOUT" -K "$CHECKOUT/scripts/localhost.yml"
echo "**** NOTE ****"
echo Some configuration written to .bashrc.
echo You may need to launch a new login shell, source .bashrc, or re-login.
echo "**************"
