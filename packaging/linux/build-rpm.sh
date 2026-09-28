#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYINSTALLER_SPEC="$SCRIPT_DIR/certificate-analyzer.spec"
RPM_SPEC_FILE="$SCRIPT_DIR/certificate-analyzer.rpm.spec"
OUTPUT_DIR="$PROJECT_ROOT/dist/linux"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$PROJECT_ROOT/.venv-linux}"

BUNDLE_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bundle-dir)
            BUNDLE_DIR="$2"
            shift 2
            ;;
        --bundle-dir=*)
            BUNDLE_DIR="${1#*=}"
            shift
            ;;
        -h|--help)
            echo "Использование: $0 [ПАРАМЕТРЫ]"
            echo "Собирает RPM-пакет для Linux."
            echo ""
            echo "Параметры:"
            echo "  --bundle-dir <путь>   Использовать уже собранную директорию приложения"
            echo "                        (пропускает этап сборки PyInstaller)"
            echo "  -h, --help            Показать эту справку"
            exit 0
            ;;
        *)
            echo "Неизвестный параметр: $1" >&2
            echo "Запустите '$0 --help' для справки." >&2
            exit 1
            ;;
    esac
done

for command in uv rpmbuild; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Не найдена команда '$command'." >&2
        if [ "$command" = "rpmbuild" ]; then
            echo "Для сборки RPM установите пакет 'rpm-build' (Fedora/RHEL/CentOS), 'rpm-tools' (Arch/Ubuntu) или 'rpm' (openSUSE)." >&2
        fi
        exit 1
    fi
done

cd "$PROJECT_ROOT"

BUILD_PARENT="${TMPDIR:-/tmp}"
BUILD_ROOT="$(mktemp -d "$BUILD_PARENT/certificate-analyzer-rpmbuild.XXXXXX")"

cleanup() {
    case "$BUILD_ROOT" in
        "$BUILD_PARENT"/certificate-analyzer-rpmbuild.*) rm -rf -- "$BUILD_ROOT" ;;
        *) echo "Временный каталог не удалён из-за небезопасного пути: $BUILD_ROOT" >&2 ;;
    esac
}
trap cleanup EXIT

if [ -z "$BUNDLE_DIR" ]; then
    echo "==> Установка зависимостей сборки..."
    uv sync --python 3.11 --extra gui --group packaging

    PYTHON_PREFIX="$(uv run --no-sync python -c 'import sys; print(sys.base_prefix)')"
    PYTHON_PREFIX="$(readlink -f "$PYTHON_PREFIX")"
    export LD_LIBRARY_PATH="$PYTHON_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

    echo "==> Сборка автономного Linux-приложения через PyInstaller..."
    uv run --no-sync pyinstaller \
        --noconfirm \
        --clean \
        --workpath "$BUILD_ROOT/pyinstaller" \
        --distpath "$BUILD_ROOT/dist" \
        "$PYINSTALLER_SPEC"

    BUNDLE_DIR="$BUILD_ROOT/dist/certificate-analyzer"
else
    BUNDLE_DIR="$(cd -- "$BUNDLE_DIR" && pwd)"
fi

if [ ! -x "$BUNDLE_DIR/certificate-analyzer" ] || [ ! -x "$BUNDLE_DIR/certificate-analyzer-gui" ]; then
    echo "В каталоге '$BUNDLE_DIR' отсутствуют исполняемые файлы certificate-analyzer или certificate-analyzer-gui." >&2
    exit 1
fi

VERSION="$(uv run --no-sync python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
MACHINE="$(uname -m)"
case "$MACHINE" in
    x86_64) ARCHITECTURE="x86_64" ;;
    aarch64|arm64) ARCHITECTURE="aarch64" ;;
    *)
        echo "Неподдерживаемая архитектура: $MACHINE" >&2
        exit 1
        ;;
esac

RPM_TOPDIR="$BUILD_ROOT/rpmbuild"
mkdir -p "$RPM_TOPDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p "$OUTPUT_DIR"

echo "==> Сборка RPM-пакета..."
rpmbuild -bb \
    --define "_topdir $RPM_TOPDIR" \
    --define "pkg_version $VERSION" \
    --define "pkg_release 1" \
    --define "bundle_dir $BUNDLE_DIR" \
    --define "project_root $PROJECT_ROOT" \
    --target "$ARCHITECTURE" \
    "$RPM_SPEC_FILE"

RPM_FILE="$(find "$RPM_TOPDIR/RPMS" -type f -name "*.rpm" | head -n 1)"
if [ -z "$RPM_FILE" ] || [ ! -f "$RPM_FILE" ]; then
    echo "Ошибка: RPM-пакет не был создан в $RPM_TOPDIR/RPMS" >&2
    exit 1
fi

RPM_FILENAME="$(basename "$RPM_FILE")"
PACKAGE_PATH="$OUTPUT_DIR/$RPM_FILENAME"
cp -f "$RPM_FILE" "$PACKAGE_PATH"

echo "==> Проверка метаданных пакета..."
if command -v rpm >/dev/null 2>&1; then
    rpm -qip "$PACKAGE_PATH"
else
    echo "(Утилита rpm для вывода метаданных не установлена)"
fi

echo "==> Пакет готов: $PACKAGE_PATH"
