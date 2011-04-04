#!/bin/bash
#this script gets some info about your repo, and posts up to BZ about the bug you just fixed.


function getstatus() {

HASH=$(git show | head -n1 | sed 's/commit //')
VERSION=$(cat subscription-manager.spec | grep Version | awk '{print $2}' | awk -F "." '{$NF++; OFS=".";print $0}')
BRANCH=$(git branch --contains $HASH | sed 's/* //')

STR=$(cat <<EOT
Fixed on $BRANCH branch in $HASH, version $VERSION
EOT
)

echo $STR
}

STATUS=$(getstatus)
BUG=$(git log --oneline | head -n1 | awk '{print $2}' | sed 's/://')

#do the deed
bugzilla -l $STATUS -s MODIFIED $BUG
