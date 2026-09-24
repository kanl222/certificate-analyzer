#!/usr/bin/env bash
set -euo pipefail
systemctl --user disable --now cert-analyzer.service
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
rm -f "$service_dir/cert-analyzer.service"
systemctl --user daemon-reload
