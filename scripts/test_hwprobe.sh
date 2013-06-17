#!/bin/bash

# Runs hwprobe.py against a set of collection hardware
# inventories, and validates that the cpu.* facts
# match those of lscpu.*.
#
# Aka, make sure the new socket counting code matches
# the output of 'lscpu'
#
# see "socket-count-test-data" repo to get a copy of
# the dumps.
#
# Run like:
#
#    ./test_hwprobe.sh /path/to/socket-count-test-data/dumps/
#

SYS_DUMPS_PATH="$1"
SYS_DUMPS=$(find "${SYS_DUMPS_PATH}" -mindepth 1 -maxdepth 1 -type d)

for sys_dump in ${SYS_DUMPS}
do
    echo "sys_dump: ${sys_dump}"
    python src/subscription_manager/hwprobe.py "${sys_dump}"
    echo
done
