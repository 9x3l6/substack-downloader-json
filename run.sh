#!/usr/bin/env bash

trap kill_it TERM  # 15 - Termination signal
trap kill_it PIPE  # 13 - Broken pipe: write to pipe with no
trap kill_it SEGV  # 11 - Invalid memory reference
trap kill_it KILL  # 9  - Kill signal
trap kill_it FPE   # 8  - Floating point exception
trap kill_it ABRT  # 6  - Abort signal from abort(3)
trap kill_it ILL   # 4  - Illegal Instruction
trap kill_it QUIT  # 3  - Quit from keyboard
trap kill_it INT   # 2  - Interrupt from keyboard
trap kill_it HUP   # 1  - Hangup detected on controlling terminal or death of controlling process

function kill_it() {
    echo "Killed $@";
    KILLED=true;
    [ "$RUNNING" != "" ] && grep -v "$RUNNING" running.txt > running.tmp && mv running.tmp running.txt;
    deactivate;
    exit 1;
}

source .venv/bin/activate;

RUNNING="";
KILLED=false;

while [ $KILLED = false ]; do
  for l in $(cat list.txt | shuf); do
    echo ">>> $l";
    if [ "$(grep "$l" running.txt)" == "" ]; then
      echo $l >> running.txt;
      RUNNING="$l";
      ./ssjl.py "https://$l.substack.com" "$l" --archive "$l.txt";
      grep -v "$l" running.txt > running.tmp; 
      mv running.tmp running.txt;
      RUNNING="";
      echo "waiting 60 seconds";
      sleep 60
    fi
  done
done
