#!/bin/bash

SYS_DUMPS_PATH="$1"

SYS_DUMPS=$(find "${SYS_DUMPS_PATH}" -mindepth 1 -maxdepth 1 -type d)

for sys_dump in ${SYS_DUMPS}
do
    echo "sys_dump: ${sys_dump}"
    python ../src/subscription_manager/hwprobe.py "${sys_dump}"
    echo
done
