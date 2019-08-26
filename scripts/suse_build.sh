#!/bin/bash
. $(dirname "$BASH_SOURCE")/suse_functions.sh
project_name="$1"
shift

if [ -z "$project_name" ]; then
    echo "Usage: $0 {project_name} [args_for_osc_build]..."
    exit 1
fi

prepare_obs "$project_name"
cd "$OBS_DIR/$project_name/$package_name"

osc build --clean "$@"
