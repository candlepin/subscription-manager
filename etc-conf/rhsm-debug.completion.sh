#
# rhsm-debug bash completion script
# vim:ts=2:sw=2:et:

# common options
_rhsm_debug_common_opts="-h --help --proxy --proxyuser --proxypassword"

# main complete function
_rhsm-debug()
{
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local first="${COMP_WORDS[1]}"

  COMPREPLY=()

  case "${first}" in
    system)
        case "${cur}" in
            -*)
                local opts="--destination --no-archive
                            --no-subscriptions --subscriptions
                            --sos ${_rhsm_debug_common_opts}"
                COMPREPLY=( $( compgen -W "${opts}" -- "$cur" ) )
                return 0
                ;;
        esac
            COMPREPLY=( $( compgen -o filenames -- "$cur" ) )
            return 0
            ;;
  esac

  COMPREPLY=($(compgen -W "system" -- ${cur}))
  return 0
}

complete -F _rhsm-debug -o default rhsm-debug
