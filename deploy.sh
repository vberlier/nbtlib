#!/usr/bin/env bash

package-name () {
  grep -Po '^\s*name\s*=\s*".+"\s*$' pyproject.toml | sed -r 's!.*"(.+)".*!\1!'
}

published () {
  local package="$1"

  echo -e "\nComparing built distributions with published releases\n"

  local releases=$(curl -sSL "https://pypi.org/simple/$package/")

  for dist in $(ls dist); do
    echo -e "Checking \033[1;33m$dist\033[0m"

    if ! echo "$releases" | grep -Fq "$dist"; then
      echo -e "\n\033[1;31mCouldn't find distribution $dist in the published releases\033[0m"
      return 1
    fi
  done

  return 0
}

deploy () {
  local username="$1"
  local password="$2"

  poetry publish \
    --username="$username" \
    --password="$password" \
    --no-interaction || return 1
}

if published $(package-name); then
  echo -e "\n\033[1;36m$TRAVIS_TAG is already published\033[0m\n"
else
  echo -e "\n\033[1;36mPublishing $TRAVIS_TAG\033[0m"
  deploy $PYPI_USERNAME $PYPI_PASSWORD || exit 1
fi
