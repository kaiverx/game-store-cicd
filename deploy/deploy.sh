#!/usr/bin/env bash
# Деплой game-store на сервер. Вызывается из стадии Deploy (только ветка main).
# Структура на сервере (создаётся deploy/setup-server.sh):
#   /opt/game-store/app     — код текущего релиза
#   /opt/game-store/venv    — виртуальное окружение
#   /opt/game-store/shared  — БД и статика (переживают деплой)
#   /opt/game-store/env     — переменные окружения Django
set -euo pipefail

APP_ROOT=/opt/game-store
APP_DIR="$APP_ROOT/app"
VENV="$APP_ROOT/venv"
PORT=8000

echo "==> 1/6 Копирование кода в $APP_DIR"
rsync -a --delete \
    --exclude '.git' --exclude '.venv' --exclude 'node_modules' --exclude 'client' \
    --exclude '__pycache__' --exclude 'db.sqlite3' --exclude 'TEST-*.xml' \
    ./ "$APP_DIR/"

echo "==> 2/6 База данных"
if [ ! -f "$APP_ROOT/shared/db.sqlite3" ]; then
    # первый деплой: берём БД с демо-данными из репозитория
    cp db.sqlite3 "$APP_ROOT/shared/db.sqlite3"
    echo "    создана из db.sqlite3 репозитория"
else
    echo "    используется существующая $APP_ROOT/shared/db.sqlite3"
fi

echo "==> 3/6 Зависимости"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --disable-pip-version-check -r "$APP_DIR/requirements.txt"

echo "==> 4/6 Миграции и статика"
set -a; . "$APP_ROOT/env"; set +a
cd "$APP_DIR"
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput -v 0

echo "==> 5/6 Перезапуск сервиса game-store"
sudo -n /usr/bin/systemctl restart game-store

echo "==> 6/6 Smoke-тест"
for i in $(seq 1 15); do
    if code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/games/") && [ "$code" = "200" ]; then
        echo "    GET /api/games/ -> 200, приложение работает"
        exit 0
    fi
    sleep 2
done
echo "    приложение не ответило 200 за 30 секунд" >&2
sudo -n /usr/bin/systemctl status game-store --no-pager || true
exit 1
