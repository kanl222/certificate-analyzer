#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE="$SCRIPT_DIR/Dockerfile.alt"
IMAGE_TAG="certificate-analyzer-builder:alt"

if ! command -v docker >/dev/null 2>&1; then
    echo "Ошибка: Docker не установлен или не найден в PATH." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Ошибка: Docker daemon не запущен." >&2
    exit 1
fi

echo "==> Сборка сборочного образа ($IMAGE_TAG)..."
docker build -f "$DOCKERFILE" -t "$IMAGE_TAG" "$PROJECT_ROOT"

echo "==> Запуск сборки RPM для ALT Linux в контейнере..."
docker run --rm -v "$PROJECT_ROOT:/workspace" "$IMAGE_TAG"

echo "==> Сборка завершена. Проверьте каталог: $PROJECT_ROOT/dist/linux"
