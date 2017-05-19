#
#	rhn migration bash completion script
#	  based on subscription-manager bash completion script
#

# main completion function
_rhn_migrate_classic_to_rhsm()
{
	local first cur prev opts base
	COMPREPLY=()
	first="${COMP_WORDS[1]}"
	cur="${COMP_WORDS[COMP_CWORD]}"
	prev="${COMP_WORDS[COMP_CWORD-1]}"
	opts="-h --help --environment -f --force -n --no-auto --no-proxy --org -s --servicelevel --legacy-user --legacy-password --destination-url --destination-user --destination-password --activation-key --keep --remove-rhn-packages"

	case "${cur}" in
		-*)
			COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
			return 0
			;;
	esac

	COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
	return 0
}

complete -F _rhn_migrate_classic_to_rhsm rhn-migrate-classic-to-rhsm
