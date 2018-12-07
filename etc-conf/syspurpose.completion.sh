#
# syspurpose bash completion script
#   based on subscription-manager script
# vim:ts=2:sw=2:et:
#

# Known and shared constants of syspurpose
_syspurpose_help_opts="-h --help"

# complete functions for subcommands ($1 - current opt, $2 - previous opt)
_syspurpose_add()
{
  # This list should include all known names of keys which are handled by the rhsm ecosystem
  # that can be treated as a list
  local opts="${_syspurpose_help_opts} addons"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_syspurpose_remove()
{
  # This list should include all known names of keys which are handled by the rhsm ecosystem
  # that can be treated as a list
  local opts="${_syspurpose_help_opts} addons"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_syspurpose_set()
{
  # This list should include all known names of keys which are handled by the rhsm ecosystem
  # that can be treated as a singular value
  local opts="${_syspurpose_help_opts} role usage service_level_agreement"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}

_syspurpose_unset()
{
  # This list should include all known names of keys which are handled by the rhsm ecosystem
  # that can be unset
  local opts="${_syspurpose_help_opts} role usage service_level_agreement addons"
  COMPREPLY=($(compgen -W "${opts}" -- ${1}))
}


# main complete function
_syspurpose()
{
  local first cur prev opts base
  COMPREPLY=()
  first=${COMP_WORDS[1]}
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  # top-level commands and options
  opts="set unset add remove set-role unset-role set-usage unset-usage add-addons remove-addons
  set-sla unset-sla show -h --help"

  case "${first}" in
    add|\
    remove|\
    set|\
    unset)
    "_syspurpose_$first" "${cur}" "${prev}"
    return 0
    ;;
    *)
    ;;
  esac

  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _syspurpose syspurpose
