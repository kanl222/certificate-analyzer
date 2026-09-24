#!/usr/bin/env bash
set -euo pipefail
# Install a user service using the executable in the current environment.
executable="$(command -v certificate-analyzer)"
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$service_dir"
cat > "$service_dir/cert-analyzer.service" <<UNIT
[Unit]
Description=Certificate and MCHD analyzer
[Service]
Type=simple
ExecStart="$executable" worker
Restart=on-failure
RestartSec=30
[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now cert-analyzer.service
