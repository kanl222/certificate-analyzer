#!/usr/bin/env bash
set -euo pipefail

# Флаги
INSTALL_DEPS=1
INSTALL_SERVICE=1
INSTALL_DESKTOP=1

for arg in "$@"; do
    case "$arg" in
        --deps-only)
            INSTALL_SERVICE=0
            INSTALL_DESKTOP=0
            ;;
        --no-deps)
            INSTALL_DEPS=0
            ;;
        --service-only)
            INSTALL_DEPS=0
            INSTALL_DESKTOP=0
            ;;
        --desktop-only)
            INSTALL_DEPS=0
            INSTALL_SERVICE=0
            ;;
        --no-service)
            INSTALL_SERVICE=0
            ;;
        --no-desktop)
            INSTALL_DESKTOP=0
            ;;
        -h|--help)
            echo "Использование: $0 [ПАРАМЕТРЫ]"
            echo "Устанавливает необходимые системные пакеты (notify-send, Tkinter, xdg-utils и др.),"
            echo "ярлык рабочего стола (.desktop) и пользовательский systemd-сервис для Certificate Analyzer."
            echo ""
            echo "Параметры:"
            echo "  --deps-only       Установить только системные зависимости без настройки службы и ярлыка"
            echo "  --no-deps         Пропустить установку системных пакетов"
            echo "  --service-only    Настроить только службу systemd"
            echo "  --desktop-only    Создать только ярлык приложения (.desktop)"
            echo "  --no-service      Не настраивать службу systemd"
            echo "  --no-desktop      Не создавать ярлык приложения"
            echo "  -h, --help        Показать эту справку"
            exit 0
            ;;
        *)
            echo "Неизвестный параметр: $arg" >&2
            echo "Запустите '$0 --help' для справки." >&2
            exit 1
            ;;
    esac
done

run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        echo "Запрос привилегий sudo для установки системных пакетов..."
        sudo "$@"
    elif command -v doas >/dev/null 2>&1; then
        echo "Запрос привилегий doas для установки системных пакетов..."
        doas "$@"
    else
        echo "Внимание: для установки системных пакетов требуются права root (sudo/doas не найден)." >&2
        return 1
    fi
}

install_system_packages() {
    echo "==> Проверка и установка системных зависимостей для Linux..."

    local missing_tools=()
    if ! command -v notify-send >/dev/null 2>&1; then
        missing_tools+=("notify-send")
    fi
    if ! command -v xdg-open >/dev/null 2>&1; then
        missing_tools+=("xdg-open")
    fi
    if ! command -v gio >/dev/null 2>&1 && ! command -v trash-put >/dev/null 2>&1; then
        missing_tools+=("gio/trash-put")
    fi
    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c "import tkinter" >/dev/null 2>&1; then
            missing_tools+=("python3-tkinter")
        fi
    fi
    if ! command -v fc-match >/dev/null 2>&1 || \
        ! fc-match -f '%{family}\n' "Noto Sans" 2>/dev/null | grep -Fqi "Noto Sans"; then
        missing_tools+=("Noto Sans")
    fi

    if [ ${#missing_tools[@]} -eq 0 ]; then
        echo "Все основные утилиты и шрифт Noto Sans уже установлены."
        return 0
    fi

    echo "Обнаружены отсутствующие компоненты: ${missing_tools[*]}"

    if command -v apt-get >/dev/null 2>&1; then
        echo "Обнаружен пакетный менеджер apt. Установка пакетов..."
        run_privileged apt-get update -y || true
        run_privileged apt-get install -y \
            libnotify-bin \
            python3-tk \
            xdg-utils \
            libglib2.0-bin \
            fonts-dejavu-core \
            fonts-noto-core
    elif command -v dnf >/dev/null 2>&1; then
        echo "Обнаружен пакетный менеджер dnf. Установка пакетов..."
        run_privileged dnf install -y \
            libnotify \
            python3-tkinter \
            xdg-utils \
            glib2 \
            dejavu-sans-fonts
    elif command -v pacman >/dev/null 2>&1; then
        echo "Обнаружен пакетный менеджер pacman. Установка пакетов..."
        run_privileged pacman -Sy --noconfirm --needed \
            libnotify \
            tk \
            xdg-utils \
            glib2 \
            ttf-dejavu
    elif command -v zypper >/dev/null 2>&1; then
        echo "Обнаружен пакетный менеджер zypper. Установка пакетов..."
        run_privileged zypper install -y \
            libnotify-tools \
            python3-tk \
            xdg-utils \
            glib2-tools \
            dejavu-fonts
    elif command -v apk >/dev/null 2>&1; then
        echo "Обнаружен пакетный менеджер apk. Установка пакетов..."
        run_privileged apk add --no-cache \
            libnotify \
            python3-tkinter \
            xdg-utils \
            glib \
            ttf-dejavu
    else
        echo "Не удалось автоматически определить пакетный менеджер." >&2
        echo "Пожалуйста, установите вручную:" >&2
        echo "  - notify-send (пакет libnotify / libnotify-bin)" >&2
        echo "  - Python Tkinter (пакет python3-tk / python3-tkinter / tk)" >&2
        echo "  - xdg-utils" >&2
        echo "  - glib2 / trash-cli (для работы с корзиной)" >&2
        echo "  - Noto Sans (пакет fonts-noto-core / noto-fonts)" >&2
        return 1
    fi

    echo "Установка системных зависимостей завершена."
}

find_executable() {
    if command -v certificate-analyzer >/dev/null 2>&1; then
        command -v certificate-analyzer
    elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/certificate-analyzer" ]; then
        echo "$VIRTUAL_ENV/bin/certificate-analyzer"
    elif [ -x "$PWD/.venv/bin/certificate-analyzer" ]; then
        echo "$PWD/.venv/bin/certificate-analyzer"
    elif [ -x "$(dirname "$0")/../../.venv/bin/certificate-analyzer" ]; then
        realpath "$(dirname "$0")/../../.venv/bin/certificate-analyzer"
    elif [ -x "$HOME/.local/bin/certificate-analyzer" ]; then
        echo "$HOME/.local/bin/certificate-analyzer"
    else
        return 1
    fi
}

install_systemd_service() {
    echo "==> Настройка пользовательской службы systemd..."
    local executable
    if ! executable="$(find_executable)"; then
        echo "Ошибка: исполняемый файл certificate-analyzer не найден в PATH или .venv." >&2
        echo "Убедитесь, что приложение установлено (например: 'uv sync --extra gui' или 'pip install .')." >&2
        exit 1
    fi

    echo "Используется исполняемый файл: $executable"
    local service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    mkdir -p "$service_dir"

    cat > "$service_dir/cert-analyzer.service" <<UNIT
[Unit]
Description=Certificate and MCHD analyzer
After=network.target

[Service]
Type=simple
ExecStart="$executable" worker
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
UNIT

    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload
        systemctl --user enable --now cert-analyzer.service
        echo "Служба cert-analyzer.service успешно включена и запущена."
    else
        echo "Внимание: systemctl не найден. Служба сохранена в $service_dir/cert-analyzer.service"
    fi
}

install_desktop_entry() {
    echo "==> Создание ярлыка приложения (.desktop)..."
    local executable
    if ! executable="$(find_executable)"; then
        echo "Предупреждение: исполняемый файл certificate-analyzer не найден, пропускаем создание ярлыка." >&2
        return 0
    fi

    local apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$apps_dir"
    local desktop_file="$apps_dir/certificate-analyzer.desktop"

    cat > "$desktop_file" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Certificate Analyzer
Comment=Анализатор сертификатов X.509 и машиночитаемых доверенностей
Exec=$executable gui
Icon=security-high
Terminal=false
Categories=Office;Security;Utility;
Keywords=certificate;mchd;x509;сертификат;мчд;
DESKTOP

    chmod +x "$desktop_file"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$apps_dir" 2>/dev/null || true
    fi
    echo "Ярлык приложения создан: $desktop_file"
}

if [ "$INSTALL_DEPS" -eq 1 ]; then
    install_system_packages || true
fi

if [ "$INSTALL_SERVICE" -eq 1 ]; then
    install_systemd_service
fi

if [ "$INSTALL_DESKTOP" -eq 1 ]; then
    install_desktop_entry
fi

echo "==> Установка для Linux успешно завершена!"
