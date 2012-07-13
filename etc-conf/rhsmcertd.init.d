#!/bin/bash
#
# rhsmcertd     This shell script controls the Red Hat Subscription Manager
#               certificate management daemon.
#
# Author:       Jeff Ortel <jortel@redhat.com>
#
# chkconfig:    345 97 2
#
# description:  Enable periodic update of entitlement certificates.
# processname:  rhsmsertd
#

# source function library
. /etc/rc.d/init.d/functions

BINDIR=/usr/bin
PROG=rhsmcertd
LOCK=/var/lock/subsys/$PROG

RETVAL=0

start() {
  if [ ! -f $LOCK ]; then
    echo -n "Starting rhsmcertd..."
    daemon $BINDIR/$PROG
    RETVAL=$?
    [ $RETVAL -eq 0 ] && touch $LOCK
    [ -x /sbin/restorecon ] && /sbin/restorecon $LOCK
  else
    echo -n "rhsmcertd is already running."
  fi
  echo
  return $RETVAL
}

stop() {
  echo -n "Stopping rhsmcertd..."
  killproc $PROG || failure
  RETVAL=$?
  echo
  [ $RETVAL -eq 0 ] && rm -f $LOCK
  return $RETVAL
}

restart() {
  stop
  start
}

reload() {
    restart
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
  reload)
  reload
  ;;  
  condrestart)
  [ -e $LOCK ] && restart || :
  ;;
  status)
  status $PROG
  RETVAL="$?"
  ;;
  *)
  echo $"Usage: $0 {start|stop|status|restart|reload|}"
  exit 1
esac

exit $RETVAL
