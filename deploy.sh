#!/usr/bin/env bash

poetry publish \
  --username=$PYPI_USERNAME \
  --password=$PYPI_PASSWORD \
  --build \
  --no-interaction
