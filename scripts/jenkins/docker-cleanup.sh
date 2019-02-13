#!/bin/bash -x

function jssh(){
  ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no jenkins@${1} "${2}"
}

for HOST in $(echo $DOCKER_HOSTS | sed "s/,/ /g"); do
	# jssh ${HOST} "docker images | grep '<none>' | awk '{print \$3}' | xargs -r docker rmi"
  # more agressive
  jssh ${HOST} "docker images -q | xargs -r docker rmi -f"
  jssh ${HOST} "docker ps -aq | xargs -r docker rm -f"
  jssh ${HOST} "docker volume ls -q | xargs -r docker volume rm"
  jssh ${HOST} 'docker network rm $(docker network ls | awk '"'"'$3 == "bridge" && $2 != "bridge" { print $1 }'"'"')'
  if [ "$RESTART_DOCKER" = 'true' ]; then
    jssh ${HOST} "sudo systemctl restart docker"
  fi
done
