#
# subscription-manager-gui bash completion script
#   based on katello script
# vim:ts=2:sw=2:et:
#

# main complete function
_subscription_manager_gui()
{
  local cur
  cur=${COMP_WORDS[COMP_CWORD]}
  COMPREPLY=($(compgen -W "-h --help --register" -- ${cur}))
  return 0
}

complete -F _subscription_manager_gui subscription-manager-gui
