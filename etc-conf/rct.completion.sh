#
# rct bash completion script
# vim:ts=2:sw=2:et:


# main complete function
_rct()
{
  local opts="cat-cert stat-cert"
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local first="${COMP_WORDS[1]}"

  COMPREPLY=()

  case "${first}" in
    cat-cert)
        opts="--no-products --no-content"
        ;;
    stat-cert)
        opts=""
        ;;
  esac

  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _rct rct
