#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SPEC_FILE="$SCRIPT_DIR/certificate-analyzer.spec"
OUTPUT_DIR="$PROJECT_ROOT/dist/linux"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$PROJECT_ROOT/.venv-linux}"

for command in uv dpkg-deb; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Не найдена команда '$command'." >&2
        exit 1
    fi
done

cd "$PROJECT_ROOT"

echo "==> Установка зависимостей сборки..."
uv sync --python 3.11 --extra gui --group packaging

PYTHON_PREFIX="$(uv run --no-sync python -c 'import sys; print(sys.base_prefix)')"
PYTHON_PREFIX="$(readlink -f "$PYTHON_PREFIX")"
export LD_LIBRARY_PATH="$PYTHON_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

BUILD_PARENT="${TMPDIR:-/tmp}"
BUILD_ROOT="$(mktemp -d "$BUILD_PARENT/certificate-analyzer-build.XXXXXX")"
PACKAGE_ROOT="$BUILD_ROOT/root"

cleanup() {
    case "$BUILD_ROOT" in
        "$BUILD_PARENT"/certificate-analyzer-build.*) rm -rf -- "$BUILD_ROOT" ;;
        *) echo "Временный каталог не удалён из-за небезопасного пути: $BUILD_ROOT" >&2 ;;
    esac
}
trap cleanup EXIT

echo "==> Сборка автономного Linux-приложения..."
uv run --no-sync pyinstaller \
    --noconfirm \
    --clean \
    --workpath "$BUILD_ROOT/pyinstaller" \
    --distpath "$BUILD_ROOT/dist" \
    "$SPEC_FILE"

BUNDLE_DIR="$BUILD_ROOT/dist/certificate-analyzer"
if [ ! -x "$BUNDLE_DIR/certificate-analyzer" ] || [ ! -x "$BUNDLE_DIR/certificate-analyzer-gui" ]; then
    echo "PyInstaller не создал ожидаемые исполняемые файлы." >&2
    exit 1
fi

VERSION="$(uv run --no-sync python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
MACHINE="$(uname -m)"
case "$MACHINE" in
    x86_64) ARCHITECTURE="amd64" ;;
    aarch64|arm64) ARCHITECTURE="arm64" ;;
    *)
        echo "Неподдерживаемая архитектура: $MACHINE" >&2
        exit 1
        ;;
esac

install -d \
    "$PACKAGE_ROOT/DEBIAN" \
    "$PACKAGE_ROOT/opt/certificate-analyzer" \
    "$PACKAGE_ROOT/usr/bin" \
    "$PACKAGE_ROOT/usr/share/doc/certificate-analyzer" \
    "$PACKAGE_ROOT/usr/share/applications" \
    "$PACKAGE_ROOT/usr/lib/systemd/user" \
    "$OUTPUT_DIR"

cp -a "$BUNDLE_DIR/." "$PACKAGE_ROOT/opt/certificate-analyzer/"
ln -s /opt/certificate-analyzer/certificate-analyzer "$PACKAGE_ROOT/usr/bin/certificate-analyzer"
install -m 0644 "$SCRIPT_DIR/certificate-analyzer.desktop" \
    "$PACKAGE_ROOT/usr/share/applications/certificate-analyzer.desktop"
install -m 0644 "$SCRIPT_DIR/certificate-analyzer.service" \
    "$PACKAGE_ROOT/usr/lib/systemd/user/certificate-analyzer.service"
install -m 0644 "$PROJECT_ROOT/LICENSE" \
    "$PACKAGE_ROOT/usr/share/doc/certificate-analyzer/copyright"
install -m 0755 "$SCRIPT_DIR/postinst" "$PACKAGE_ROOT/DEBIAN/postinst"
install -m 0755 "$SCRIPT_DIR/prerm" "$PACKAGE_ROOT/DEBIAN/prerm"
install -m 0755 "$SCRIPT_DIR/postrm" "$PACKAGE_ROOT/DEBIAN/postrm"

INSTALLED_SIZE="$(du -sk "$PACKAGE_ROOT/opt" | cut -f1)"
cat > "$PACKAGE_ROOT/DEBIAN/control" <<EOF
Package: certificate-analyzer
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCHITECTURE
Installed-Size: $INSTALLED_SIZE
Maintainer: kanl <106077541+kanl222@users.noreply.github.com>
Depends: libc6 (>= 2.28), libx11-6, libxext6, libxrender1, libxft2, libfontconfig1, libfreetype6, libnotify-bin, xdg-utils, libglib2.0-bin, fonts-dejavu-core, fonts-noto-core
Description: X.509 certificate and MChD analyzer
 Certificate storage, reporting and expiration monitoring with a desktop GUI.
EOF

PACKAGE_PATH="$OUTPUT_DIR/certificate-analyzer_${VERSION}_${ARCHITECTURE}.deb"
echo "==> Сборка DEB-пакета..."
dpkg-deb --build --root-owner-group "$PACKAGE_ROOT" "$PACKAGE_PATH"

echo "==> Проверка метаданных пакета..."
dpkg-deb --info "$PACKAGE_PATH"
echo "==> Пакет готов: $PACKAGE_PATH"
