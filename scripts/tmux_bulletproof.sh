#!/bin/bash
# BULLETPROOF TMUX - NEVER DIE

SESSION="train_bulletproof"

# Kill old session if exists
tmux kill-session -t $SESSION 2>/dev/null

# System optimize
source scripts/optimize_system.sh 2>/dev/null || true

# Create unkillable tmux session
tmux new-session -d -s $SESSION

# Set aggressive keep-alive
tmux set-option -t $SESSION -g status-interval 1
tmux set-option -t $SESSION -g remain-on-exit on
tmux set-option -t $SESSION -g exit-unattached off

# Run training with auto-restart wrapper
tmux send-keys -t $SESSION "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION "while true; do python /tmp/train_unkillable.py 2>&1 | tee output_bulletproof/train.log; echo '🔄 Restarting in 3s...'; sleep 3; done" C-m

echo "✅ BULLETPROOF SESSION STARTED"
echo ""
echo "Attach:  tmux attach -t $SESSION"
echo "Detach:  Ctrl+B then D"
echo "Kill:    tmux kill-session -t $SESSION"
echo ""
echo "Session will auto-restart on any crash"
