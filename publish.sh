#!/usr/bin/env bash

toml-string () {
  grep -Po "^\s*$2\s*=\s*".+"\s*$" "$1" | sed -r 's!.*"(.+)".*!\1!'
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

publish () {
  local name="$1"
  local version="$2"

  if published "$name"; then
    echo -e "\n\033[1;36m$name v$version is already published\033[0m"
  else
    echo -e "\n\033[1;36mPublishing $name v$version\033[0m"

    poetry publish \
      --username="$PYPI_USERNAME" \
      --password="$PYPI_PASSWORD" \
      --no-interaction || return 1
  fi
}

poetry build && publish \
  "$(toml-string pyproject.toml name)" \
  "$(toml-string pyproject.toml version)" || exit 1
