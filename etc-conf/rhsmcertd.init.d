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
### BEGIN INIT INFO
# Provides:       rhsmcertd
# Required-Start: $local_fs $network $remote_fs $named $time
# Required-Stop:  $local_fs $network $remote_fs $named
# Default-Start:  3 5
# Default-Stop:   0 1 6
### END INIT INFO

VENDOR=$( rpm --eval %_vendor )

# source function library
[ -f /etc/rc.d/init.d/functions ] && . /etc/rc.d/init.d/functions
[ -f /etc/rc.status ] && . /etc/rc.status

if [ ! -f /etc/rc.d/init.d/functions ]; then
  status() {
    /sbin/checkproc $PROG
    rc_status -v
  }
fi

BINDIR=/usr/bin
PROG=rhsmcertd
LOCK=/var/lock/subsys/$PROG

RETVAL=0

start() {
  if [ ! -f $LOCK ]; then
    echo -n "Starting rhsmcertd..."
    if [[ "$VENDOR" == "suse" ]] ;then
      startproc $BINDIR/$PROG
      rc_status -v
    else
      daemon $BINDIR/$PROG
    fi
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
