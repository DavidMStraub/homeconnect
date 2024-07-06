#!/usr/bin/env bash

set -x 

python3 -m venv .venv

. .venv/bin/activate

pip3 install -r requirements_test.txt

pytest --cov=homeconnect/ --cov-report term-missing -vv ./tests/homeconnect

rm -rf .venv
