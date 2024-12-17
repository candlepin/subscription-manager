#!/bin/bash

USERNAME=admin
PASSWORD=admin
ORG=donaldduck


# The script will create two environments for an organization.
#
# citation from 'man subscription-manager':
#
#   With on-premise subscription services, such as Subscription Asset Manager,
#   the infrastructure is more complex. The local administrator can define
#   independent groups called organizations which represent physical
#   or organizational divisions (--org). Those organizations can be subdivided
#   into environments (--environment).
#

curl -k --request POST --user ${USERNAME}:${PASSWORD} \
     --data '{"id": "env-id-01", "name": "env-name-01", "description": "Testing environment num. 1"}' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     https://localhost:8443/candlepin/owners/${ORG}/environments

curl -k --request POST --user ${USERNAME}:${PASSWORD} \
     --data '{"id": "env-id-02", "name": "env-name-02", "description": "Testing environment num. 2", "type": "content-template"}' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     https://localhost:8443/candlepin/owners/${ORG}/environments
 
