#!/usr/bin/env python3
"""Зеркало каталога дополнений сообщества: addons/<id>/addon.json и таблица в README.md.

Каталог ведёт сервер ConnectTogether: авторы публикуют дополнения из приложения, команда проверяет их в админке.
Скрипт берёт одобренные (GET /api/addons), скачивает каждый addon.json, сверяет его sha256 с каталогом и id в тексте —
с id в каталоге, раскладывает по папкам, удаляет снятые с каталога и переписывает таблицу между метками в README.md.
Только стандартная библиотека Python 3.

    python3 scripts/mirror.py [--server https://connecttogether.ru] [--root .]
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

START = "<!-- addons:start -->"
END = "<!-- addons:end -->"
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
# Больше сервер не принимает (10 КБ); с запасом
MAX_BYTES = 64 * 1024
USER_AGENT = "ConnectTogether-Addons-mirror"


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=30) as reply:
        data = reply.read(MAX_BYTES * 16 + 1)
    return data


def markdown(text: str) -> str:
    """Текст от автора — в ячейку таблицы как есть: без переводов строк, разметки и HTML."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return re.sub(r"([\\`*_{}\[\]<>()#+!|~])", r"\\\1", text)


def load_catalog(server: str) -> list:
    catalog = json.loads(get(server.rstrip("/") + "/api/addons"))
    addons = catalog.get("addons")
    if not isinstance(addons, list):
        raise SystemExit("Сервер прислал не каталог: нет списка addons")
    return addons


def download(server: str, entry: dict) -> bytes:
    addon_id = entry.get("id", "")
    if not isinstance(addon_id, str) or not ID.match(addon_id):
        raise SystemExit(f"Недопустимый id в каталоге: {addon_id!r}")
    data = get(f"{server.rstrip('/')}/api/addons/{urllib.parse.quote(addon_id)}/addon.json")
    if len(data) > MAX_BYTES:
        raise SystemExit(f"{addon_id}: addon.json больше {MAX_BYTES // 1024} КБ")
    sha = hashlib.sha256(data).hexdigest()
    if sha != str(entry.get("sha256", "")).lower():
        raise SystemExit(f"{addon_id}: sha256 текста {sha} не совпадает с каталогом — каталог сменился или ответ подменён")
    manifest = json.loads(data.decode("utf-8"))
    if manifest.get("id") != addon_id:
        raise SystemExit(f"{addon_id}: в тексте id {manifest.get('id')!r}")
    return data


def table(addons: list) -> str:
    if not addons:
        return "Пока пусто — опубликуйте первое из приложения."
    rows = ["| Игра | Папка | Вид | Версия | Автор |", "|---|---|---|---|---|"]
    for entry in sorted(addons, key=lambda a: str(a.get("name", "")).lower()):
        kind = "ставит сервер" if entry.get("runsServer") else "сервер с инструкцией"
        rows.append(f"| {markdown(entry.get('name', ''))} | [`{entry['id']}`](addons/{entry['id']}/addon.json) | {kind} | "
                    f"{markdown(entry.get('version', ''))} | {markdown(entry.get('author', ''))} |")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", default="https://connecttogether.ru")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root)
    folder = root / "addons"

    addons = load_catalog(args.server)
    texts = {entry["id"]: download(args.server, entry) for entry in addons}

    folder.mkdir(exist_ok=True)
    for path in folder.iterdir():
        # addons/ ведёт каталог: снятые с него и чужие папки уходят, README папки остаётся
        if path.is_dir() and path.name not in texts:
            shutil.rmtree(path)
            print(f"Удалено: {path.name}")
    for addon_id, data in texts.items():
        target = folder / addon_id / "addon.json"
        target.parent.mkdir(exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
            print(f"Обновлено: {addon_id}")

    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"В README.md нет меток {START} и {END}")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    readme.write_text(f"{head}{START}\n{table(addons)}\n{END}{tail}", encoding="utf-8", newline="\n")
    print(f"В каталоге: {len(addons)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
