#
# syspurpose bash completion script
#   based on subscription-manager script
# vim:ts=2:sw=2:et:
#

# Known and shared constants of syspurpose
_syspurpose_help_opts="-h --help"

# complete functions for subcommands ($1 - current opt, $2 - previous opt)

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

  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _syspurpose syspurpose
