#!/usr/bin/env bash

# dir di questo script

here=$(dirname "$0")/

# alias path per moduli importati dallo spec (es. deep_subdict)
monitor="$here"$1".pl"
shift 1
swipl -O -p monitor="$here" "$monitor" -- "$@"
