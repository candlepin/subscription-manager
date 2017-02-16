OBS_DIR=${OBS_DIR:-~/obs}
source_dir="$(pwd)"
package_name="$(basename $(pwd))"
prepare_obs() {
    project_name="$1"

    tempdir="$(mktemp -d)"
    echo "Packaging sources w/ tito"
    tito build --srpm --test -o "$tempdir"

    if [ ! -d ~/obs ]; then
        mkdir ~/obs
    fi
    pushd ~/obs

    if [ ! -d "$project_name" ]; then
        osc co "$project_name"
        pushd "$project_name"
    else
        pushd "$project_name"
        echo "Ensuring $project_name is up-to-date."
        osc update
    fi

    pushd "$package_name"
    echo "Removing any existing sources"
    osc rm *
    rpm2cpio "${tempdir}"/*.rpm | cpio -i
    echo "Adding ${package_name}-rpmlintrc"
    cp "${source_dir}/${package_name}-rpmlintrc" .

    echo "Cleaning up tito tempdir"
    rm -rf "${tempdir}"
}

