#!/bin/bash

cd ~/doorpi
tmux new -d -s doorpi
tmux send-keys -t doorpi.0 ". v/bin/activate" ENTER
tmux send-keys -t doorpi.0 "while true ; do ./bot; sleep 30 ; done" ENTER
