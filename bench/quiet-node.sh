#!/usr/bin/env bash
# Checks that the benchmark node is quiet before a run, and saves what it found.
#
# How to use it (from the repo folder, with the VPN on):
#   SSH_USER=<your username> bench/quiet-node.sh <run_id>
#   SSH_USER=<your username> bench/quiet-node.sh <run_id> k8s-worker-02   # to check the other worker
#
# The result is saved to evidence/week5/runs/<run_id>/quiet-node.txt
set -uo pipefail

RUN_ID="${1:?Usage: SSH_USER=<you> $0 <run_id> [node]}"
NODE="${2:-k8s-worker-01}"
: "${SSH_USER:?Set SSH_USER to your cluster username, e.g. SSH_USER=gavin}"
CP=10.151.0.11

# Each worker's address
case "$NODE" in
  k8s-worker-01) IP=10.151.0.21 ;;
  k8s-worker-02) IP=10.151.0.22 ;;
  *) echo "Unknown node: $NODE"; exit 1 ;;
esac

# Where to save the result
OUT_DIR="${OUT_DIR:-evidence/week5/runs/$RUN_ID}"
mkdir -p "$OUT_DIR"

{
  echo "# Quiet-node check for run $RUN_ID on $NODE"
  echo "# run at: $(date -u +%FT%TZ) by $SSH_USER"
  echo
  echo "## How busy is the node, and what's using it?"
  ssh "$SSH_USER@$IP" 'uptime; echo; top -bn1 | head -n 15'
  echo
  echo "## What else is running on this node"
  ssh "$SSH_USER@$CP" "kubectl get pods -A -o wide --no-headers --field-selector spec.nodeName=$NODE.novalocal | awk '{print \$1, \$2, \$4}'"
  echo
  # A load under 1.0 on an 8-CPU machine means it's mostly idle
  echo "## Is it quiet enough to run?"
  LOAD1=$(ssh "$SSH_USER@$IP" "cut -d' ' -f1 /proc/loadavg")
  if awk -v l="$LOAD1" 'BEGIN { exit !(l < 1.0) }'; then
    echo "QUIET: load is $LOAD1, go ahead"
  else
    echo "BUSY: load is $LOAD1, wait a few minutes and check again"
  fi
} 2>&1 | tee "$OUT_DIR/quiet-node.txt"
