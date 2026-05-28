# Dominion V2 VM Recovery Config
**Created:** 2026-05-28 (before Windows reset)
**Target:** Fresh WSL2 Ubuntu on new Windows install

---

## WSL2 Setup

### Install WSL2
```powershell
# Windows PowerShell (admin)
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

### Ubuntu packages
```bash
sudo apt update && sudo apt install -y \
  git curl wget build-essential python3.11 python3.11-venv python3-pip \
  tmux vim neovim ripgrep fd-find bat htop iotop ncdu tree \
  postgresql-client redis-tools jq yq
```

---

## Claude Code Setup

### Install Claude Code
```bash
# Install Anthropic's Claude Code CLI
curl -fsSL https://claude.ai/install.sh | bash
```

### Global config
```bash
mkdir -p ~/.claude
cd ~/.claude

# CLAUDE.md (global instructions)
cat > CLAUDE.md << 'EOF'
# graphify
- **graphify** (~/.claude/skills/graphify/SKILL.md) - any input to knowledge graph. Trigger: /graphify
When the user types /graphify, invoke the Skill tool with skill: "graphify" before doing anything else.
EOF

# Keybindings
cat > keybindings.json << 'EOF'
{
  "submit": ["ctrl+enter"],
  "newline": ["enter"],
  "cancel": ["ctrl+c"]
}
EOF

# Settings
cat > settings.json << 'EOF'
{
  "model": "sonnet",
  "hooks": {
    "on_prompt_submit": "~/.claude/hooks/caveman_hook.sh"
  },
  "permissions": {
    "allow": ["bash", "read", "write", "edit"]
  }
}
EOF
```

### Caveman hook
```bash
mkdir -p ~/.claude/hooks
cat > ~/.claude/hooks/caveman_hook.sh << 'EOF'
#!/bin/bash
echo "CAVEMAN MODE ACTIVE (full). Drop articles/filler/pleasantries/hedging. Fragments OK. Code/commits/security: write normal."
EOF
chmod +x ~/.claude/hooks/caveman_hook.sh
```

### Install plugins/skills
```bash
# Official plugins
claude plugin add claude-plugins-official
claude plugin add claude-code-plugins-plus
claude plugin add claude-equity-research-marketplace
claude plugin add claude-for-financial-services

# Caveman skills
claude plugin add caveman

# Skills via npm
npm install -g @anthropic/skills
npx skills install statsmodels pymc scikit-learn polars shap
```

---

## Tmux Setup

### Install tmux plugin manager
```bash
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

### .tmux.conf
```bash
cat > ~/.tmux.conf << 'EOF'
# Prefix key
set -g prefix C-a
unbind C-b
bind C-a send-prefix

# Split panes
bind | split-window -h
bind - split-window -v
unbind '"'
unbind %

# Reload config
bind r source-file ~/.tmux.conf \; display "Reloaded!"

# Mouse mode
set -g mouse on

# Copy mode vi keys
setw -g mode-keys vi
bind -T copy-mode-vi v send -X begin-selection
bind -T copy-mode-vi y send -X copy-pipe-and-cancel "xclip -in -selection clipboard"

# Pane navigation
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# Status bar
set -g status-bg black
set -g status-fg white
set -g status-left '#[fg=green][#S] '
set -g status-right '#[fg=yellow]%Y-%m-%d %H:%M'

# Plugins
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-sensible'
set -g @plugin 'tmux-plugins/tmux-resurrect'
set -g @plugin 'tmux-plugins/tmux-continuum'

# Auto-save sessions
set -g @continuum-restore 'on'
set -g @continuum-save-interval '15'

# Initialize TPM
run '~/.tmux/plugins/tpm/tpm'
EOF
```

### Install plugins
```bash
tmux source ~/.tmux.conf
~/.tmux/plugins/tpm/bin/install_plugins
```

---

## Python Setup

### Install uv (fast package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create venv for Dominion
```bash
cd ~/Dominion
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## Git Setup

### Config
```bash
git config --global user.name "MatinDeevv"
git config --global user.email "matin@example.com"
git config --global core.editor "nvim"
git config --global init.defaultBranch "main"
```

### SSH key for GitHub
```bash
ssh-keygen -t ed25519 -C "matin@example.com" -f ~/.ssh/id_ed25519
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub  # Add to GitHub
```

---

## Dominion Project Clone

```bash
cd ~
git clone git@github.com:MatinDeevv/Dominion.git
cd Dominion
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt

# Create CLAUDE.md project config
cat > CLAUDE.md << 'EOF'
# Claude Code Configuration for Dominion
[See current CLAUDE.md in repo]
EOF
```

---

## MT5 + Wine Setup

### Install Wine (if running MT5 via Wine)
```bash
sudo dpkg --add-architecture i386
wget -nc https://dl.winehq.org/wine-builds/winehq.key
sudo apt-key add winehq.key
sudo add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ jammy main'
sudo apt update
sudo apt install -y --install-recommends winehq-stable winetricks

# Install MT5 dependencies
winetricks vcrun2019 dotnet48
```

### MT5 data bridge config
```bash
cd ~/Dominion
cat > domdata/config.yaml << 'EOF'
mt5:
  login: XXXXX
  server: "XXXXX"
  password: "XXXXX"
  path: "/path/to/mt5/terminal64.exe"

safety:
  read_only: true
  forbidden_tokens:
    - order_send
    - order_check
    - TRADE_ACTION_DEAL
EOF
```

---

## Tailscale Setup (optional, for SSH)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

---

## Common tmux sessions

```bash
# Create sessions
tmux new-session -d -s dominion 'cd ~/Dominion && source .venv/bin/activate && bash'
tmux new-session -d -s ragd 'cd ~/Dominion && source .venv/bin/activate && bash'
tmux new-session -d -s ssh

# Attach
tmux attach -t dominion
```

---

## Verification Checklist

- [ ] WSL2 Ubuntu installed
- [ ] Claude Code CLI installed + plugins
- [ ] tmux + TPM configured
- [ ] Python 3.11 + uv installed
- [ ] Git config + SSH key added to GitHub
- [ ] Dominion repo cloned + venv created
- [ ] MT5 Wine setup (if applicable)
- [ ] Tailscale installed (if needed)
- [ ] tmux sessions created (dominion, ragd)

---

## Quick Start After Restore

```bash
# Start tmux session
tmux attach -t dominion

# Activate venv
cd ~/Dominion
source .venv/bin/activate

# Run safety checks
python domdata/check_no_trading.py
domdata doctor

# Start working
claude  # Launch Claude Code CLI
```

---

## Backup Files to Save

Before Windows reset, copy these to cloud storage:

1. `~/.ssh/id_ed25519` + `~/.ssh/id_ed25519.pub` (SSH keys)
2. `~/.claude/` (Claude config)
3. `~/.tmux.conf` (tmux config)
4. `~/Dominion/` (entire project, or push to GitHub)
5. `domdata/config.yaml` (MT5 credentials)
6. Any custom scripts in `~/bin/`

