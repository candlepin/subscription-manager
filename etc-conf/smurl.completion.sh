#!/bin/bash

METHODS="
/activation_keys
/activation_keys/{activation_key_id}
/activation_keys/{activation_key_id}/pools
/activation_keys/{activation_key_id}/pools/{pool_id}
/admin/init
/atom
/serials/{serial_id}
/serials
/cdn
/consumers
/consumers/{consumer_uuid}
/consumers/{consumer_uuid}/entitlements/dry-run
/consumers/{consumer_uuid}/certificates
/consumers/{consumer_uuid}/export
/consumers/{consumer_uuid}/compliance
/consumers/{consumer_uuid}/content_overrides
/consumers/compliance
/consumers/{consumer_uuid}
/consumers/{consumer_uuid}/events
/consumers/{consumer_uuid}/certificates/serials
/consumers/{consumer_uuid}/certificates
/consumers/{consumer_uuid}/guests
/consumers/{consumer_uuid}/guestids
/consumers/{consumer_uuid}/host
/consumers/{consumer_uuid}/owner
/consumers/{consumer_uuid}/release
/consumers/{consumer_uuid}/entitlements
/consumers/{consumer_uuid}/certificates
/consumers/{consumer_uuid}/deletionrecord
/consumers/{consumer_uuid}/entitlements/{dbid}
/consumers/{consumer_uuid}/entitlements
/consumers/{consumer_uuid}/certificates/{serial}
/consumers/{consumer_uuid}
/consumertypes
/consumertypes/{id}
/content
/content/{content_id}
/crl
/deleted_consumers
/distributor_versions
/distributor_versions/{id}
/distributor_versions
/distributor_versions/{id}
/entitlements/{dbid}
/entitlements/{dbid}/upstream_cert
/entitlements/consumer/{consumer_uuid}/product/{product_id}
/entitlements
/entitlements/product/{product_id}
/entitlements/{dbid}
/entitlements/{entitlement_id}
/environments/{env_id}/consumers
/environments/{env_id}
/environments/{env_id}/content
/events/{uuid}
/events
/hypervisors
/jobs/scheduler
/jobs/{job_id}
/jobs
/jobs/scheduler
/migrations
/owners/{owner_key}/activation_keys
/owners/{owner_key}/environments
/owners
/owners/{owner_key}
/owners/{owner_key}/subscriptions
/owners/{owner_key}/uebercert
/owners/{owner_key}/consumers/{consumer_uuid}/atom
/owners/{owner_key}/events
/owners/{owner_key}/imports
/owners/{owner_key}/atom
/owners/{owner_key}/info
/owners/{owner_key}/pools
/owners/{owner_key}/statistics/{qtype}/{vtype}
/owners/{owner_key}/subscriptions
/owners/{owner_key}/uebercert
/owners/{owner_key}/upstream_consumers
/owners/{owner_key}/entitlements
/owners/{owner_key}/imports
/owners
/owners/{owner_key}/environments
/owners/{owner_key}/activation_keys
/owners/{owner_key}/consumers
/owners/{owner_key}/entitlements
/owners/{owner_key}/servicelevels
/owners/{owner_key}/subscriptions
/owners/{owner_key}/imports
/owners/subscriptions
/pools/{pool_id}
/pools/{pool_id}/entitlements
/pools/{pool_id}/statistics/{vtype}
/pools
/products
/products/owners
/products/{product_uuid}/content/{content_id}
/products/{product_uuid}/reliance/{rely_product_id}
/products/{product_uuid}
/products/{product_uuid}/certificate
/products/{prod_id}/statistics
/products/{product_uuid}/subscriptions
/products/{product_uuid}/content/{content_id}
/products/{product_uuid}/reliance/{rely_product_uuid}
/roles/{role_id}/permissions
/roles/{role_id}/users/{username}
/roles/{role_id}/users/{username}
/roles
/roles/{role_id}/permissions/{perm_id}
/roles/{role_id}
/rules
/serials
/statistics/generate
/status
/subscriptions
/subscriptions/{subscription_id}/cert
/subscriptions/{subscription_id}
/users
/users/{username}
/users/{username}/roles
/users/{username}/owners
/users/{username}"


_smurl_api()
{
    local opts="--method --auth -d -X --request --username --password --org"
    local all_comp="${opts} ${METHODS}"
    COMPREPLY=($(compgen -W "${all_comp}" -- ${1}))
}

_smurl()
{
  local first cur prev opts base
  COMPREPLY=()

  first=${COMP_WORDS[1]}
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  opts="api
        get post put delete head patch
        --method --auth -d -X --request --username --password --org"

  case "${prev}" in
     -X|--request)
        local REQUEST_TYPES="GET POST PUT DELETE HEAD"
        COMPREPLY=($(compgen -W "${REQUEST_TYPES}" -- ${cur}))
        return 0
        ;;
    --auth)
        local AUTH_TYPES="consumer user none"
        COMPREPLY=( $(compgen -W "${AUTH_TYPES}" -- ${cur}) )
        return 0
        ;;
    -d)
        local filename="${1#@}"
        COMPREPLY=( $( compgen -W -o filenames "@- " -- "${filename}" ) )
        return 0
        ;;
    api|--method)
         "_smurl_api" "${cur}" "${prev}"
         return 0
         ;;
   esac

  case "${cur}" in
      --*)
          local OPTIONS="--method --auth -d -X --request --username --password --org"
          COMPREPLY=($(compgen -W "${OPTIONS}" -- ${cur}))
          # expand options
          return 0
          ;;
          # also need to complete get, etc, and handle get something_to_expand
          # if not a subcommand or option, try to expand method paths\
      *get|put|post|head|delete|patch)
          "_smurl_api" "${cur}" "${prev}"
          return 0
          ;;
      *)
         "_smurl_api" "${cur}" "${prev}"
         return 0
         ;;
   esac

  method_and_opts="${opts} ${METHODS}"
  COMPREPLY=($(compgen -W "${method_and_opts}" -- ${cur}))
  return 0

}

complete -F _smurl -o default smurl
