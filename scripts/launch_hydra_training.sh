#!/bin/bash
# Launch all 3 Hydra brains in parallel tmux panes + merge on completion.
#
# Usage: bash scripts/launch_hydra_training.sh
#
# This creates a tmux session "hydra-train" with 4 panes:
#   Top-left:     ScalpHydra (label_12b)
#   Top-right:    DayHydra (label_72b)
#   Bottom-left:  SwingHydra (label_288b)
#   Bottom-right: Mega-merge (waits for all 3, then fuses)
#
# Attach with: tmux attach -t hydra-train

set -e

SESSION="hydra-train"
DIR="$HOME/Dominion"

# Kill existing session if present
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Create session with first pane (scalp)
tmux new-session -d -s "$SESSION" -c "$DIR" \
    "echo '=== SCALP HYDRA (label_12b) ===' && python scripts/train_brain.py scalp 2>&1 | tee output_hydra_scalp/train.log; echo 'DONE - press enter'; read"

# Split horizontally for day
tmux split-window -h -t "$SESSION" -c "$DIR" \
    "echo '=== DAY HYDRA (label_72b) ===' && python scripts/train_brain.py day 2>&1 | tee output_hydra_day/train.log; echo 'DONE - press enter'; read"

# Split bottom-left for swing
tmux split-window -v -t "$SESSION.0" -c "$DIR" \
    "echo '=== SWING HYDRA (label_288b) ===' && python scripts/train_brain.py swing 2>&1 | tee output_hydra_swing/train.log; echo 'DONE - press enter'; read"

# Split bottom-right for merge
tmux split-window -v -t "$SESSION.1" -c "$DIR" \
    "echo '=== MEGA MERGE (waiting for brains...) ===' && python scripts/merge_brains.py 2>&1 | tee output_hydra_mega/merge.log; echo 'DONE - press enter'; read"

# Set layout to tiled (equal panes)
tmux select-layout -t "$SESSION" tiled

# Set pane titles
tmux select-pane -t "$SESSION.0" -T "SCALP"
tmux select-pane -t "$SESSION.1" -T "DAY"
tmux select-pane -t "$SESSION.2" -T "SWING"
tmux select-pane -t "$SESSION.3" -T "MEGA"

echo ""
echo "=========================================="
echo "  HYDRA TRAINING LAUNCHED"
echo "=========================================="
echo ""
echo "  Session: $SESSION"
echo "  Panes:   4 (scalp | day | swing | mega)"
echo ""
echo "  Attach:  tmux attach -t $SESSION"
echo ""
echo "=========================================="
