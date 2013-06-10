#
# rct bash completion script
# vim:ts=2:sw=2:et:


# main complete function
_rct()
{
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local first="${COMP_WORDS[1]}"

  COMPREPLY=()

  case "${first}" in
    cat-cert)
        COMPREPLY=( $( compgen -W -o filenames "-h --help --no-products --no-content" -- "$cur" ) )
        return 0
        ;;
    stat-cert)
        COMPREPLY=( $( compgen -W -o filenames "-h --help" -- "${cur}" ) )
        return 0
        ;;
    cat-manifest)
        COMPREPLY=( $( compgen -W -o filenames "-h --help" -- "${cur}" ) )
        return 0
        ;;
    dump-manifest)
        COMPREPLY=( $( compgen -W -o filenames "-h --help --force" -- "${cur}" ) )
        return 0
        ;;
  esac

  COMPREPLY=($(compgen -W "cat-cert stat-cert cat-manifest dump-manifest" -- ${cur}))
  return 0
}

complete -F _rct -o default rct