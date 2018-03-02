#!/bin/bash

apt-get install -y lib{ffi,xml{sec1,2}}-dev python3-{setuptools,pip} nmap git

if [[ $# -eq 1 ]]; then
    cd "$1"
fi

repos=( "https://github.com/sullo/nikto.git" "https://github.com/maurosoria/dirsearch.git" )
for repo in "${repos}"; do
    git clone --single-branch -b master --depth 1 "$repo" "external/$repo"
done
