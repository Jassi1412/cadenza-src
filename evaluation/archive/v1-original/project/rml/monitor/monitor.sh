#!/usr/bin/env bash

# dir di questo script (stackoverflow.com/a/246128)
# here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
here=/home/davide/git/RMLatDIBRIS/monitor

# alias path per moduli importati dallo spec (es. deep_subdict)
swipl -O -p monitor="$here" "$here"/monitor.pl -- "$@"
