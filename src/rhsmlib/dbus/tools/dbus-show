#!/bin/bash

# For a given bus/service name, find all of it's object paths
# and show introspection data for each.
# Uses 'busctl' cli for the heavy work.
#
# If a service name isn't specified, default to all the
# well known names that have been acquired. This potentially
# doesn't include apps that only use a unique name, or services
# that need to be activated.
#
# Example usage:
# $ dbus-show org.storaged.Storaged

BUS=${BUS:-"system"}


if [ -n "${1}" ]
then
    SERVICENAMES=( "$@" )
else
    SERVICENAMES=( $(busctl --no-legend "--${BUS}" --acquired | awk -e '{print $1}') )
fi


for service_name in "${SERVICENAMES[@]}"
do

    dbus_paths=$(busctl "--${BUS}" tree  --list "${service_name}")
    tree_exit_code="$?"

    if [ "${tree_exit_code}" -eq "1" ]
    then
        printf "Service name %s not found on this bus." "${service_name}"
        continue
    fi

    printf "service name: %s" "${service_name}"
    for dbus_path in ${dbus_paths}
    do
        declare -a intro_data
        printf "  object path: %s\n" "${dbus_path}"

        # pull the intro_data into an array, one line per array entry (split on newline via readarray -t)
        # So that we can indent it slightly for purely cosmetic reasons.
        intro_data_raw=$(busctl "--${BUS}" "introspect" "--no-legend" "${service_name}" "${dbus_path}")
        readarray -t intro_data <<<"${intro_data_raw}"

        if [ -n "${intro_data}" ]
        then
            for intro_data_line in "${intro_data[@]}"
            do
                printf "    %s\n" "${intro_data_line}"
            done
            echo
        fi

    done
    echo
done

