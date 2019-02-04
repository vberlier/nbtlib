#!/usr/bin/env bash

published () {
  local releases=$(curl -sSL "https://pypi.org/simple/${PWD##*/}/")

  for build in $(ls dist); do
    if ! echo $releases | grep -Fq "$build"; then
      return 1
    fi
  done

  return 0
}

deploy () {
  local username=$1
  local password=$2

  poetry publish \
    --username="$username" \
    --password="$password" \
    --no-interaction
}

if published; then
  echo -e "\n$TRAVIS_TAG already published\n"
else
  echo -e "\nPublishing $TRAVIS_TAG\n"
  deploy $PYPI_USERNAME $PYPI_PASSWORD
fi
