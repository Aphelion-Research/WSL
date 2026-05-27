#!/bin/bash
# Launch Hydra 3-brain training SEQUENTIALLY to avoid OOM.
# Still in tmux so you can watch progress live.
#
# Usage: bash scripts/launch_hydra_sequential.sh
# Attach: tmux attach -t hydra-train
#
# Layout: 2 panes
#   Left:  Sequential training (scalp → day → swing → merge)
#   Right: Live progress monitor (watches output files)

set -e

SESSION="hydra-train"
DIR="$HOME/Dominion"

# Kill existing
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Clean old outputs
rm -f output_hydra_scalp/*.npy output_hydra_scalp/*.json output_hydra_scalp/model_*
rm -f output_hydra_day/*.npy output_hydra_day/*.json output_hydra_day/model_*
rm -f output_hydra_swing/*.npy output_hydra_swing/*.json output_hydra_swing/model_*
rm -f output_hydra_mega/*.json output_hydra_mega/*.pkl

# Create session — main training pane
tmux new-session -d -s "$SESSION" -c "$DIR" \
    'echo "════════════════════════════════════════════════════════════"
     echo "  HYDRA 3-BRAIN TRAINING PIPELINE"
     echo "  scalp (label_12b) → day (label_72b) → swing (label_288b)"
     echo "════════════════════════════════════════════════════════════"
     echo ""
     echo ">>> PHASE 1/4: SCALP BRAIN"
     echo "─────────────────────────────────────────"
     python scripts/train_brain.py scalp
     echo ""
     echo ">>> PHASE 2/4: DAY BRAIN"
     echo "─────────────────────────────────────────"
     python scripts/train_brain.py day
     echo ""
     echo ">>> PHASE 3/4: SWING BRAIN"
     echo "─────────────────────────────────────────"
     python scripts/train_brain.py swing
     echo ""
     echo ">>> PHASE 4/4: MEGA MERGE"
     echo "─────────────────────────────────────────"
     python scripts/merge_brains.py
     echo ""
     echo "════════════════════════════════════════════════════════════"
     echo "  ALL COMPLETE"
     echo "════════════════════════════════════════════════════════════"
     echo "Press enter to exit"
     read'

# Right pane: monitor
tmux split-window -h -t "$SESSION" -c "$DIR" \
    'while true; do
       clear
       echo "═══ HYDRA TRAINING MONITOR ═══"
       echo ""
       echo "Time: $(date +%H:%M:%S)"
       echo ""
       for brain in scalp day swing; do
         dir="output_hydra_${brain}"
         if [ -f "$dir/results_${brain}.json" ]; then
           acc=$(python3 -c "import json; r=json.load(open(\"$dir/results_${brain}.json\")); print(f\"{r[\"oos_metrics\"][\"accuracy\"]:.4f}\")" 2>/dev/null || echo "?")
           auc=$(python3 -c "import json; r=json.load(open(\"$dir/results_${brain}.json\")); print(f\"{r[\"oos_metrics\"][\"auc_roc\"]:.4f}\")" 2>/dev/null || echo "?")
           echo "  ✅ $brain: acc=$acc auc=$auc"
         elif [ -f "$dir/train.log" ]; then
           last=$(tail -1 "$dir/train.log" 2>/dev/null | head -c 60)
           echo "  ⏳ $brain: training... $last"
         else
           echo "  ⏸  $brain: waiting"
         fi
       done
       echo ""
       if [ -f "output_hydra_mega/mega_results.json" ]; then
         echo "═══ MEGA RESULTS ═══"
         python3 -c "
import json
r = json.load(open(\"output_hydra_mega/mega_results.json\"))
print(f\"  Best: {r[\"best_strategy\"]} (AUC={r[\"best_metrics\"][\"auc_roc\"]:.4f})\")
for k,v in r[\"mega_strategies\"].items():
    print(f\"    {k}: acc={v[\"accuracy\"]:.4f} auc={v[\"auc_roc\"]:.4f}\")
" 2>/dev/null
       fi
       echo ""
       echo "Memory: $(free -h | grep Mem | awk \"{print \\\$3\\\"/\\\"\\\$2}\")"
       sleep 10
     done'

tmux select-pane -t "$SESSION.0"

echo ""
echo "════════════════════════════════════════"
echo "  HYDRA TRAINING LAUNCHED (sequential)"
echo "════════════════════════════════════════"
echo ""
echo "  Session: $SESSION"
echo "  Left:    Training pipeline"
echo "  Right:   Progress monitor"
echo ""
echo "  Attach:  tmux attach -t $SESSION"
echo ""
echo "════════════════════════════════════════"
