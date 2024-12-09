#
# subscription-manager bash completion script
#   based on katello script
# vim:ts=2:sw=2:et:
#

# options common to all subcommands (+ 3rd level opts for simplicity)
_subscription_manager_help_opts="-h --help"
_subscription_manager_common_opts="--proxy --proxyuser --proxypassword --noproxy --no-progress-messages ${_subscription_manager_help_opts}"
_subscription_manager_common_url_opts="--insecure --serverurl"
# complete functions for subcommands ($1 - current opt, $2 - previous opt)

_subscription_manager_syspurpose()
{
  local opts="role service-level usage --show ${_subscription_manager_common_opts}"

  case "${2}" in
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
            --unset --username --password
            ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_usage()
{
  local opts="--list --org --set --show
            --unset --username --password
            ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_unregister()
{
  local opts="${_subscription_manager_common_opts}"
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
  local opts="--org --password --username --set --list --list-enabled --list-disabled
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

_subscription_manager_list()
{
  local opts="--installed
              --matches
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_subscription_manager_orgs()
{
  local opts="--password --username
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

_subscription_manager_refresh()
{
  local opts="--force
              ${_subscription_manager_common_opts}"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


_subscription_manager_register()
{
  local opts="--activationkey --baseurl --consumerid
              --environments --force --name --org --password --release
              --username
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
                --unset --username --password
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
  opts="clean config environments facts identity list orgs
        repo-override plugins refresh register release repos status
        syspurpose unregister version ${_subscription_manager_help_opts}"

  case "${first}" in
      clean|\
      config|\
      environments|\
      facts|\
      identity|\
      list|\
      orgs|\
      plugins|\
      refresh|\
      register|\
      release|\
      repos|\
      status|\
      syspurpose|\
      unregister|\
      version)
      "_subscription_manager_$first" "${cur}" "${prev}"
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
