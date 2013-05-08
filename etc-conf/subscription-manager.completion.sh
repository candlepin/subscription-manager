#
# subscription-manager bash completion script
#   based on katello script
# vim:ts=2:sw=2:et:
#

# options common to all subcommands (+ 3rd level opts for simplicity)
_subscription_manager_common_opts="-h --help --proxy --proxyuser --proxypassword"
_subscription_manager_common_url_opts="--serverurl"
# complete functions for subcommands ($1 - current opt, $2 - previous opt)

_subscription_manager_attach()
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
  local opts="i--auto --pool --quantity --servicelevel
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_unregister()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_remove()
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

_subscription_manager_clean()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_config()
{
  # TODO: we could probably generate the options from the help
  CONFIG_OPTS=$(subscription-manager config --help | sed -ne "s|\s*\(\-\-.*\..*\)\=.*\..*|\1|p")
  local opts="--list --remove
              ${CONFIG_OPTS}
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_environments()
{
  local opts="--org --password --password
              ${_subscription_manager_common_url_opts}
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_facts()
{
  local opts="--list --update
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_identity()
{
  local opts="--force --password --regenerate --username
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_import()
{
  # TODO: auto complete *.pem?
  local opts="--certificate
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_list()
{
  local opts="--all --available --consumed --installed
              --ondate --servicelevel --status
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_orgs()
{
  local opts="--password --username
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_plugins()
{
  local opts="--list --listhooks --listslots --verbose
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_redeem()
{
  local opts="--email --locale
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_refresh()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


_subscription_manager_register()
{
  local opts="--activationkey --auto-attach --autosubscribe --consumerid
              --environment --force --name --org --password --release
              --servicelevel --type --username
              ${_subscription_manager_common_url_opts}
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_release()
{
    # we could autocomplete the release version for
    # --set
    local opts="--list --set --show --unset
                  ${_subscription_manager_common_opts}"
    COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_repos()
{
  local opts="--disable --enable --list
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_service_level()
{
    local opts="--list --org --set --show --unset
                ${_subscription_manager_common_url_opts}
                ${_subscription_manager_common_opts}"
    COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_version()
{
  local opts="${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

# main complete function
_subscription_manager()
{
  local first cur prev opts base
  COMPREPLY=()
  first=${COMP_WORDS[1]}
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  # top-level commands and options
  opts="attach clean config environments facts identity import list orgs
        plugins redeem refresh register release remove repos service-level subscribe
        unregister unsubscribe version"

  case "${first}" in
      clean|\
      config|\
      environments|\
      facts|\
      identity|\
      import|\
      list|\
      orgs|\
      plugins|\
      redeem|\
      refresh|\
      register|\
      release|\
      repos|\
      unregister|\
      version)
      "_subscription_manager_$first" "${cur}" "${prev}"
      return 0
      ;;
      service-level)
      "_subscription_manager_service_level" "${cur}" "${prev}"
      return 0
      ;;
      attach|subscribe)
      "_subscription_manager_attach" "${cur}" "${prev}"
      return 0
      ;;
      remove|unsubscribe)
      "_subscription_manager_remove" "${cur}" "${prev}"
      return 0
      ;;
      *)
      ;;
  esac

  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _subscription_manager subscription-manager
