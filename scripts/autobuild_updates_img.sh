#!/bin/bash

# Bash script used for automatic rebuilding of updates.img used by Anaconda installer.
# This script is usually started as service by systemd, but it can be also started manually
# On PXE server providing updates.img to PXE client.

usage() {
    cat << USAGE

Usage: $0 [options]
OPTIONS:
  -p | --python <python_interpreter>  Python interpreter to use. Use to differentiate between Python 2
                                        and Python 3.
  -s | --src <src_dir>                Directory with source code used for creating updates.img
  -d | --dest <dest_dir>              Destination directory, where updates.img will be created.
  -h | --help                         Print this help text

USAGE
}

SHORT_OPTIONS="hs:d:p:"
LONG_OPTIONS="help,src:,dest:,python:"

ARGS=$(getopt -s bash --options $SHORT_OPTIONS --longoptions $LONG_OPTIONS -- "$@")

eval set -- $ARGS

while [[ $# -gt 0 ]]
do
    case $1 in
        -p|--python)
            # Note to future self, shift moves all positional parameters to n-1
            # (e.g. after shift the value of $1 becomes whatever $2 was prior)
            PYTHON_BIN=$2
            shift
            ;;
        -s|--src)
            SRC_DIR=$2
            shift
            ;;
        -d|--dest)
            DEST_DIR=$2
            shift
            ;;
        -h|--help)
            usage
            exit
            ;;
        *)
            # Stop parsing on anything other than a long or short option we expected.
            break
            ;;
    esac
    shift
done


# Setting default values, when no arguments were provided
if [ "${PYTHON_BIN}" = "" ]; then
    PYTHON_BIN="python"
    echo "Python interpreter not specified, using ${PYTHON_BIN}"
fi
if [ "${SRC_DIR}" = "" ]; then
    SRC_DIR=$PWD
    echo "Source directory not specified, using ${PWD}"
fi
if [ "${DEST_DIR}" = "" ]; then
    DEST_DIR=$PWD
    echo "Destination directory not specified, using ${PWD}"
fi


# Never ending loop
while inotifywait -r "${SRC_DIR}"; do
	pushd "${SRC_DIR}"
	echo "Building new updates.img ..."
	sudo -u vagrant ${0%/*}/build_updates_img.sh --python ${PYTHON_BIN}
	echo "Done"
	if [ $? -eq 0 ]; then
		cp updates.img "${DEST_DIR}"
	fi
	popd
	# Wait 10 seconds.
	sleep 10
done
