#!/bin/sh

tito tag --accept-auto-changelog
git push --follow-tags origin
tito release $TITO_RELEASE -y
