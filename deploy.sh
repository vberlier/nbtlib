#!/usr/bin/env bash

published () {
  echo -e "\nComparing built distributions with published releases"

  local releases=$(curl -sSL "https://pypi.org/simple/nbtlib/")

  for build in $(ls dist); do
    echo "Checking $build"

    if ! echo "$releases" | grep -Fq "$build"; then
      echo -e "\n\033[1;31mCouldn't find build $build in the published releases\033[0m"
      return 1
    fi
  done

  return 0
}

deploy () {
  local username=$1
  local password=$2

  poetry publish --username="$username" --password="$password" || return 1
}

if published; then
  echo -e "\n\033[1;36m$TRAVIS_TAG is already published\033[0m"
else
  echo -e "\n\033[1;36mPublishing $TRAVIS_TAG\033[0m"
  deploy $PYPI_USERNAME $PYPI_PASSWORD || exit 1
fi
