#!/bin/bash

FACTS="com.redhat.Subscriptions1.Facts"
FACTS_PATH="/com/redhat/Subscriptions1/Facts/Host"
FACTS_INTF="com.redhat.Subscriptions1.Facts"
PROPS_INTF="org.freedesktop.DBus.Properties"
INTRO_INTF="org.freedesktop.DBus.Introspectable"

busctl | grep 'rhsm'
busctl status "${FACTS}"

pkaction | grep 'Subscriptions1'

busctl tree "${FACTS}"
SERVICE="${FACTS}"
OBJECT_PATH="${FACTS_PATH}"

# yes, it is using global variables and args
dbus_call () {
    local the_rest=$*

    local CALL_ARGS="${SERVICE} ${OBJECT_PATH} ${INTF}"

    busctl call ${CALL_ARGS} ${the_rest}
}

per_fact_object () {
    OBJECT_PATH="${1}"
        
    busctl introspect "${SERVICE}" "${OBJECT_PATH}"
    
    INTF="${PROPS_INTF}"
    dbus_call GetAll s "${FACTS_INTF}"
    dbus_call Get ss "${FACTS_INTF}" "version"
    dbus_call Get ss "${FACTS_INTF}" "some_prop_that_doesnt_exist"

    INTF="${FACTS_INTF}"
    dbus_call GetFacts

    INTF="${INTRO_INTF}"
    dbus_call Introspect
}

per_fact_object "${FACTS_PATH}"

#CALL_ARGS="${SERVICE} ${OBJECT_PATH} ${INTF}"
