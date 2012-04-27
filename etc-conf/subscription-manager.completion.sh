#
# subscription-manager bash completion script
#   based on katello script
# vim:ts=2:sw=2:et:
#

# options common to all subcommands (+ 3rd level opts for simplicity)
_subscription_manager_common_opts="-h --help --proxy --proxyuser --proxypassword"

# complete functions for subcommands ($1 - current opt, $2 - previous opt)

_subscription-manager_list()
{
  local opts="--installed --available --ondate --consumed --all
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


_subscription-manager_refresh()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_register()
{
  local opts="--username --password --type --name --consumerid
              --org --environment --autosubscribe --force --activationkey
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_subscribe()
{
  # try to autocomplete pool id's as well
  # doesn't work well with sudo/non root users though
  case $prev in
      --pool)
          # wee bit of a hack to handle that we can't actually run subscription-manager list --available unless
          # we are root. try it directly (as opposed to userhelper links) and if it fails,ignore it
          POOLS=$(/usr/sbin/subscription-manager list --available 2>/dev/null | sed -ne "s|PoolId:\s*\(\S*\)|\1|p" )
          COMPREPLY=($(compgen -W "${POOLS}" -- ${1}))
          return 0
  esac
  local opts="--pool --quantity --auto
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_unregister()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_unsubscribe()
{
 # try to autocomplete serial number as well
  case $prev in
      --serial)
          SERIALS=$(/usr/sbin/subscription-manager list --consumed 2>/dev/null | sed -ne "s|SerialNumber:\s*\(\S*\)|\1|p" )
          COMPREPLY=($(compgen -W "${SERIALS}" -- ${1}))
          return 0
  esac
  local opts="--serial --all
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_clean()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_config()
{
  # TODO: we could probably generate the options from the help
  CONFIG_OPTS=$(subscription-manager config --help | sed -ne "s|\s*\(\-\-.*\..*\)\=.*\..*|\1|p")
  local opts="--list --remove
              ${CONFIG_OPTS}
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_environments()
{
  local opts="--username --password --org
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_facts()
{
  local opts="--list --update
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_identity()
{
  local opts="--username --password --regenerate --force
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_import()
{
  # TODO: auto complete *.pem?
  local opts="--certificate
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_orgs()
{
  local opts="--username --password
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_redeem()
{
  local opts="--email --locale
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_release()
{
    # we could autocomplete the release version for
    # --set
    local opts="--list --set
                  ${_subscription_manager_common_opts}"
    COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_repos()
{
  local opts="--list
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription-manager_service-level()
{
    local opts="--show --org --list
                  ${_subscription_manager_common_opts}"
    COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


# main complete function
_subscription-manager()
{
  local first cur prev opts base
  COMPREPLY=()
  first=${COMP_WORDS[1]}
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  # top-level commands and options
  opts="list refresh register subscribe unregister unsubscribe clean config environments
  facts identity import orgs release redeem repos service-level"

  case "${first}" in
      list|\
      refresh|\
      register|\
      subscribe|\
      unregister|\
      unsubscribe|\
      clean|\
      config|\
      environments|\
      facts|\
      identity|\
      import|\
      orgs|\
      redeem|\
      release|\
      repos|\
      service-level)
      "_subscription-manager_$first" "${cur}" "${prev}"
      return 0
      ;;
    *)
      ;;
  esac

  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _subscription-manager subscription-manager
