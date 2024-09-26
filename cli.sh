#!/usr/bin/env bash

WORKING_DIR="$(pwd)"

unalias lwe > /dev/null 2>&1
LWE_CONFIG_DIR="${WORKING_DIR}/lwe/config" LWE_DATA_DIR="${WORKING_DIR}/lwe/storage" lwe "$@"
