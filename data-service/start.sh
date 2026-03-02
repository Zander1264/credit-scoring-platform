#!/bin/sh
set -ex

echo "migration"

# Запускаем миграции
alembic upgrade head

# Запускаем основное приложение
exec "$@"