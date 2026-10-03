#!/usr/bin/env bash
set -euo pipefail

PURGE_DATA=0

for arg in "$@"; do
    case "$arg" in
        --purge)
            PURGE_DATA=1
            ;;
        -h|--help)
            echo "Использование: $0 [ПАРАМЕТРЫ]"
            echo "Удаляет пользовательский systemd-сервис и ярлык приложения Certificate Analyzer."
            echo ""
            echo "Параметры:"
            echo "  --purge       Также удалить пользовательские данные и настройки (~/.certificate-analyzer)"
            echo "  -h, --help    Показать эту справку"
            exit 0
            ;;
        *)
            echo "Неизвестный параметр: $arg" >&2
            echo "Запустите '$0 --help' для справки." >&2
            exit 1
            ;;
    esac
done

echo "==> Удаление Certificate Analyzer для Linux..."

# Остановить и удалить текущую службу и совместимый старый вариант.
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
for unit in certificate-analyzer.service cert-analyzer.service; do
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user stop "$unit" || true
        systemctl --user disable "$unit" || true
    fi
    # Удаляем только файл/символическую ссылку конкретной службы, без рекурсии.
    if [ -f "$service_dir/$unit" ] || [ -L "$service_dir/$unit" ]; then
        rm -f -- "$service_dir/$unit"
    fi
done
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
fi

# 3. Удаление ярлыка приложения (.desktop)
apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
desktop_file="$apps_dir/certificate-analyzer.desktop"
if [ -f "$desktop_file" ]; then
    rm -f "$desktop_file"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$apps_dir" 2>/dev/null || true
    fi
    echo "Ярлык приложения $desktop_file удален."
fi

# 4. Опциональная очистка данных
rm -f -- "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps/certificate-analyzer.png"

if [ "$PURGE_DATA" -eq 1 ]; then
    echo "Удаление данных и конфигурации (~/.certificate-analyzer)..."
    rm -rf "$HOME/.certificate-analyzer"
    echo "Данные успешно удалены."
fi

echo "==> Удаление завершено!"
