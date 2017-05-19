#
#	rhsm-icon bash completion script
#	  based on rhn-migrate-classic-to-rhsm bash completion script
#

# main completion function
_rhsm_icon()
{
	local first cur prev opts base
	COMPREPLY=()
	first="${COMP_WORDS[1]}"
	cur="${COMP_WORDS[COMP_CWORD]}"
	prev="${COMP_WORDS[COMP_CWORD-1]}"
	opts="-h --help --help-all --help-gtk  -c --check-period -d
		--debug -f --force-icon -i --check-immediately --display"

	case "${cur}" in	
		-*)
			COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
			return 0
			;;
	esac

	COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
	return 0
}

complete -F _rhsm_icon rhsm-icon
