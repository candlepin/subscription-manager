#!/bin/bash
#
# rhsmcertd     This shell script controls the Red Hat Subscription Manager
#               certificate management daemon.
#
# Author:       Jeff Ortel <jortel@redhat.com>
#
# chkconfig:  - 97 01
#
# description:  Enable periodic update of entitlement certificates.
# processname:  rhsmsertd
#

# source function library
. /etc/rc.d/init.d/functions

DIR=/usr/share/rhsm
PROG=rhsmcertd

RETVAL=0

start() {
  echo -n $"Starting rhsmcertd"
  cd $DIR
  ./$PROG
  RETVAL=$?
  echo
}

stop() {
  echo -n $"Stopping rhsmcertd"
  pkill $PROG
  RETVAL=$?
  echo
}

restart() {
  stop
  start
}

status() {
  pgrep rhsmsertd
  if [ $? == 0 ]; then
    RETVAL=0
    echo $"$PROG is running"
  else
    RETVAL=3
    echo $"$PROG is not running"
  fi
}

case "$1" in
  start)
  start
  ;;
  stop)
  stop
  ;;
  restart)
  restart
  ;;
  status)
  status
  ;;
  *)
  echo $"Usage: $0 {start|stop|status|restart|}"
  exit 1
esac

exit $RETVAL
