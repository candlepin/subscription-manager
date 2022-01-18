#
# subscription-manager bash completion script
#   based on katello script
# vim:ts=2:sw=2:et:
#

# options common to all subcommands (+ 3rd level opts for simplicity)
_subscription_manager_help_opts="-h --help"
_subscription_manager_common_opts="--proxy --proxyuser --proxypassword --noproxy ${_subscription_manager_help_opts}"
_subscription_manager_common_url_opts="--insecure --serverurl"
# complete functions for subcommands ($1 - current opt, $2 - previous opt)

_subscription_manager_auto_attach()
{
  local opts="--enable --disable --show ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_attach()
{
  # try to autocomplete pool id's as well
  # doesn't work well with sudo/non root users though
  case $prev in
      --pool)
          # wee bit of a hack to handle that we can't actually run subscription-manager list --available unless
          # we are root. try it directly (as opposed to userhelper links) and if it fails,ignore it
          POOLS=$(LANG=C /usr/sbin/subscription-manager list --available 2>/dev/null | sed -ne "s|Pool ID:\s*\(\S*\)|\1|p" )
          COMPREPLY=($(compgen -W "${POOLS}" -- ${1}))
          return 0
  esac
  local opts="--auto --pool --quantity --servicelevel --file
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_syspurpose()
{
  local opts="addons role service-level usage --show ${_subscription_manager_common_opts}"

  case "${2}" in
      addons|\
      role|\
      usage)
      "_subscription_manager_$2" "${1}" "${2}"
      return 0
      ;;
      service-level)
      "_subscription_manager_service_level" "${1}" "${2}"
      return 0
      ;;
      *)
      ;;
  esac

  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


_subscription_manager_role()
{
  local opts="--list --org --set --show
            --unset --username --password --token
            ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_usage()
{
  local opts="--list --org --set --show
            --unset --username --password --token
            ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_addons()
{
  local opts="--list --org --show --add --remove
            --unset --username --password --token
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
          SERIALS=$(LANG=C /usr/sbin/subscription-manager list --consumed 2>/dev/null | sed -ne "s|Serial:\s*\(\S*\)|\1|p" )
          COMPREPLY=($(compgen -W "${SERIALS}" -- ${1}))
          return 0
          ;;
      --pool)
          POOLS=$(LANG=C /usr/sbin/subscription-manager list --consumed 2>/dev/null | sed -ne "s|Pool ID:\s*(\S*\)|\1|p" )
          COMPREPLY=($(compgen -W "${POOLS}" -- ${1}))
          return 0
          ;;
  esac
  local opts="--serial --pool --all
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_clean()
{
  local opts="-h --help"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_config()
{
  # TODO: we could probably generate the options from the help
  CONFIG_OPTS=$(LANG=C subscription-manager config --help | sed -ne "s|\s*\(\-\-.*\..*\)\s.*|\1|p")
  local opts="--list --remove
              ${CONFIG_OPTS}
              -h --help"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_environments()
{
  local opts="--org --password --username --token --set --list --list-enabled --list-disabled
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
  local opts="--force --password --regenerate --username --token
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_import()
{
  # TODO: auto complete *.pem?
  local opts="--certificate
              -h --help"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_list()
{
  local opts="--afterdate --all --available --consumed --installed
              --ondate --servicelevel
              --match-installed --no-overlap
              --matches
              --pool-only
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_orgs()
{
  local opts="--password --username --token
              ${_subscription_manager_common_url_opts}
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_repo_override()
{
  local opts="--repo --list --add --remove --remove-all
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_plugins()
{
  local opts="--list --listhooks --listslots --verbose
              -h --help"
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
  local opts="--force
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


_subscription_manager_register()
{
  local opts="--activationkey --auto-attach --autosubscribe --baseurl --consumerid
              --environments --force --name --org --password --release
              --servicelevel --username --token
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
  local opts="--disable --enable --list --list-enabled --list-disabled
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_service_level()
{
    local opts="--list --org --set --show
                --unset --username --password --token
                ${_subscription_manager_common_url_opts}
                ${_subscription_manager_common_opts}"
    COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_status()
{
  local opts="${_subscription_manager_common_opts} --ondate"
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

  # Because the 'prev' may be optional argument like '--list', we iterate from the start
  # until we find string that starts with a dash. The word before is the subcommand
  # which should be used for completion.
  for word in ${COMP_WORDS[@]}; do
    if [[ $word == -* ]]; then
      break;
    fi
    prev=$word
  done

  # top-level commands and options
  opts="addons attach auto-attach clean config environments facts identity import list orgs
        repo-override plugins redeem refresh register release remove repos role service-level status
        subscribe syspurpose unregister unsubscribe usage version ${_subscription_manager_help_opts}"

  case "${first}" in
      addons|\
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
      role|\
      status|\
      syspurpose|\
      unregister|\
      usage|\
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
      auto-attach)
      "_subscription_manager_auto_attach" "${cur}" "${prev}"
      return 0
      ;;
      repo-override)
      "_subscription_manager_repo_override" "${cur}" "${prev}"
      return 0
      ;;
      *)
      ;;
  esac

  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _subscription_manager subscription-manager
