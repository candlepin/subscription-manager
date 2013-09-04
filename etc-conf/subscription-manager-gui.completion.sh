#
# subscription-manager-gui bash completion script
#   based on katello script
# vim:ts=2:sw=2:et:
#

# main complete function
_subscription_manager_gui()
{
  local first cur prev opts base
  COMPREPLY=()
  first=${COMP_WORDS[1]}
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  # top-level commands and options

  COMPREPLY=($(compgen -W "-h --help --register"))
  return 0
}

complete -F _subscription_manager_gui subscription-manager-gui
