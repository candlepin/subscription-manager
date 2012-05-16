#!/bin/bash

# run git-checkcommits against known branches and look
# for commits that haven't been merged to master
# add a branch name to ".branches" file to have
# it checked by the script
#
#  get git-checkcommits from https://github.com/alikins/gitconfig
#
#
if [ -z "${ORIGIN}" ] ; then
    ORIGIN="origin"
fi
FAIL=""
BRANCHFILE=".branches"

while read branch;
do
    echo "Checking branch: ${branch}"
    KNOWNFILE="scripts/.known.${branch}"
    if [ -f ${KNOWNFILE} ] ; then
        RES=$(git checkcommits master "${ORIGIN}/${branch}" | grep -v -f "${KNOWNFILE}")
    else
        RES=$(git checkcommits master "${ORIGIN}/${branch}")
    fi
    if [ -n "${RES}" ] ; then
        FAIL="failed"
        echo "** WARNING: Unmerged commits from ${branch}"
        echo "** If these are known exceptions, add to ${KNOWNFILE}"
        echo "${RES}"
        echo
    fi
done < ${BRANCHFILE}


if [ -n "${FAIL}" ] ; then
    exit 1
fi
exit 0
