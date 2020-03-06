pushd $(git rev-parse --show-toplevel) >/dev/null
cat $(cat .deplist | tr "\n" " ") | md5sum -z | cut -d" " -f1
popd >/dev/null
