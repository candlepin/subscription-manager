#
#	rhn migration bash completion script
#	  based on subscription-manager bash completion script
#

# main completion function
_rhn-migrate-classic-to-rhsm()
{
	local first cur prev opts base
	COMPREPLY=()
	first="${COMP_WORDS[1]}"
	cur="${COMP_WORDS[COMP_CWORD]}"
	prev="${COMP_WORDS[COMP_CWORD-1]}"
	opts="-h --help --environment -f --force -g --gui -n --no-auto --no-proxy --org -s --servicelevel --serverurl"

	case "${cur}" in	
		-*)
			COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
			return 0
			;;
	esac

	COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
	return 0
}

complete -F _rhn-migrate-classic-to-rhsm rhn-migrate-classic-to-rhsm
