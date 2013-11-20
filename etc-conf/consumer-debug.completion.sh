#
# consumer-debug bash completion script
# vim:ts=2:sw=2:et:


# main complete function
_consumer-debug()
{
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local first="${COMP_WORDS[1]}"

  COMPREPLY=()

  case "${first}" in
    compile)
        case "${cur}" in
            -*)
                COMPREPLY=( $( compgen -W "-h --help --destination" -- "$cur" ) )
                return 0
                ;;
        esac
            COMPREPLY=( $( compgen -o filenames -- "$cur" ) )
            return 0
            ;;
  esac

  COMPREPLY=($(compgen -W "compile" -- ${cur}))
  return 0
}

complete -F _consumer-debug -o default consumer-debug
