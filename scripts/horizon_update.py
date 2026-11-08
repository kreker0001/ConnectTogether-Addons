#!/usr/bin/env python3
"""Собирает ZIP Horizon и манифест для публикации кандидата в GitHub Releases."""

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from mirror import download, load_catalog

CATALOG = "https://connecttogether.ru"
REPOSITORY = "kreker0001/ConnectTogether-Addons"
UPSTREAM = "horizon-rust/horizon"
ASSET = "horizon-windows-x64.zip"
WRAPPER = "ConnectTogether.Horizon.exe"
WRAPPER_SHA256 = "012054c63eeb2f6441657a3118b3d1d6803d237b3aa83054430b47183288e350"
NOTICES = "connecttogether-wrapper-notices/"
REQUIRED = {"horizon-client.exe", "horizon-prepare.exe", "research-lock.json"}
BUNDLE = "horizon-windows-x64.zip"
MANIFEST = "Horizon.ctaddon"
RELEASE_URL = f"https://github.com/{REPOSITORY}/releases/download/"
RAW_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/"


def curl(url, *args):
    result = subprocess.run([
        "curl", "--silent", "--show-error", "--fail", "--location",
        "--proto", "=https", "--retry", "3", "--connect-timeout", "15",
        "--max-time", "180", *args, url,
    ], stdout=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(f"Не удалось получить {url} (curl {result.returncode}).")
    return result.stdout


def latest_asset():
    headers = ["--header", "Accept: application/vnd.github+json"]
    if token := os.getenv("GH_TOKEN"):
        headers += ["--header", f"Authorization: Bearer {token}"]
    releases = json.loads(curl(f"https://api.github.com/repos/{UPSTREAM}/releases?per_page=30", *headers))
    candidates = [
        (release, asset) for release in releases if not release["draft"] and release["published_at"]
        for asset in release["assets"] if asset["name"] == ASSET and asset["state"] == "uploaded"
    ]
    if not candidates:
        raise ValueError("В последних релизах Horizon нет ZIP для Windows x64.")
    release, asset = max(candidates, key=lambda item: item[0]["published_at"])
    return release["tag_name"], asset


def fetch_zip(url, digest, destination):
    curl(url, "--output", str(destination))
    with destination.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest and actual != digest:
        raise ValueError(f"SHA-256 архива {url} изменился. Повторите проверку.")
    return actual


def members(archive):
    files = {}
    for entry in archive.infolist():
        name = entry.filename
        parts = name.rstrip("/").split("/")
        if any(part in {"", ".", ".."} or part.endswith((" ", "."))
               or re.search(r'[\\:*?"<>|\x00-\x1f]', part)
               or PureWindowsPath(part).is_reserved() for part in parts):
            raise ValueError(f"Недопустимый путь в ZIP: {name!r}")
        if entry.external_attr >> 16 & 0o170000 == 0o120000:
            raise ValueError(f"Символьная ссылка в ZIP: {name!r}")
        if not entry.is_dir():
            key = name.casefold()
            if key in files:
                raise ValueError(f"Повторяющийся путь в ZIP: {name!r}")
            files[key] = entry
    if "research-lock.json" not in files:
        roots = {name.split("/")[0] for name in files}
        if len(roots) != 1 or any("/" not in name for name in files):
            raise ValueError("Не удалось определить корневую папку ZIP.")
        files = {name.split("/", 1)[1]: entry for name, entry in files.items()}
    return files


def write_bundle(base, base_files, upstream, upstream_files, destination):
    wrapper_key = WRAPPER.casefold()
    preserved = {name for name in base_files if name == wrapper_key or name.startswith(NOTICES)}
    if wrapper_key not in preserved or not any(name.startswith(NOTICES) for name in preserved):
        raise ValueError("В опубликованном ZIP нет обёртки или её лицензий.")
    if hashlib.sha256(base.read(base_files[wrapper_key])).hexdigest() != WRAPPER_SHA256:
        raise ValueError("В каталоге другая сборка обёртки. Проверьте её перед автоматической упаковкой.")
    if preserved.intersection(upstream_files) or "server.jar" in upstream_files:
        raise ValueError("В ZIP Horizon появились файлы, конфликтующие со схемой установки.")

    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6) as result:
        for archive, files, names in [(upstream, upstream_files, upstream_files), (base, base_files, preserved)]:
            for name in sorted(names):
                entry = files[name]
                # Убираем только общий корень, сохраняя регистр имён файлов Horizon.
                path = "/".join(entry.filename.split("/")[-len(name.split("/")):])
                result.writestr(ZipInfo(path), archive.read(entry), compress_type=ZIP_DEFLATED, compresslevel=6)


def build(published, upstream_tag, asset, output, scratch):
    server = next(item for item in published["install"] if item["id"] == "server")
    server_jar = next(item for item in published["install"] if item["id"] == "minecraft-server")
    if {item["id"] for item in published["install"]} != {"server", "minecraft-server"}:
        raise ValueError("Изменилась схема установки Horizon из каталога.")
    raw_bundle = re.escape(RAW_URL) + r"[0-9a-f]{40}/ct-horizon-server-[0-9.]+-win-x64\.zip"
    release_bundle = re.escape(RELEASE_URL) + r"horizon-addon-[0-9.]+-[0-9a-f]{20}/" + re.escape(BUNDLE)
    if not re.fullmatch(f"(?:{raw_bundle}|{release_bundle})", server["url"]) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", server.get("sha256", "")
    ):
        raise ValueError("Неизвестный источник опубликованного ZIP с обёрткой.")

    asset_url = f"https://github.com/{UPSTREAM}/releases/download/{quote(upstream_tag, safe='')}/{ASSET}"
    digest = asset.get("digest")
    if digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("GitHub вернул неподдерживаемый формат хэша архива Horizon.")
    upstream_path = scratch / "upstream.zip"
    upstream_sha = fetch_zip(asset_url, digest[7:] if digest else None, upstream_path)
    if upstream_path.stat().st_size != asset["size"]:
        raise ValueError("Размер скачанного ZIP не совпадает с данными GitHub.")
    base_path = scratch / "published.zip"
    fetch_zip(server["url"], server["sha256"].lower(), base_path)

    with ZipFile(base_path) as base, ZipFile(upstream_path) as upstream:
        base_files = members(base)
        upstream_files = members(upstream)
        if not REQUIRED.issubset(upstream_files):
            raise ValueError("В новом ZIP нет файлов для запуска или подготовки Horizon.")
        lock = json.loads(upstream.read(upstream_files["research-lock.json"]))["minecraft"]
        if (lock["version"], lock["java_major"], lock["server_sha1"]) != ("26.3", 25, server_jar["sha1"]):
            raise ValueError("Новый релиз требует другую версию Minecraft, Java или server.jar. Проверьте обёртку.")
        installed = {name for name in base_files if name != WRAPPER.casefold() and not name.startswith(NOTICES)}
        if installed == upstream_files.keys() and all(
            base_files[name].CRC == entry.CRC and base_files[name].file_size == entry.file_size
            for name, entry in upstream_files.items()
        ):
            print("Опубликованный аддон уже содержит эту сборку Horizon.")
            return

        manifest_dir = output / "check" / "horizon"
        manifest_dir.mkdir(parents=True)
        bundle_path = output / BUNDLE
        write_bundle(base, base_files, upstream, upstream_files, bundle_path)

    with bundle_path.open("rb") as stream:
        bundle_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = copy.deepcopy(published)
    major, minor, patch = map(int, manifest["version"].split("."))
    manifest["version"] = f"{major}.{minor}.{patch + 1}"
    key = hashlib.sha256(json.dumps([published, upstream_sha, bundle_sha], sort_keys=True).encode()).hexdigest()[:20]
    tag = f"horizon-addon-{manifest['version']}-{key}"
    candidate = next(item for item in manifest["install"] if item["id"] == "server")
    candidate.update(url=f"{RELEASE_URL}{tag}/{BUNDLE}", sha256=bundle_sha, extract=True)
    candidate.pop("stripRoot", None)
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if len(data) > 10 * 1024:
        raise ValueError("Манифест превышает 10 КБ.")
    (manifest_dir / "addon.json").write_bytes(data)
    (output / MANIFEST).write_bytes(data)
    (output / "release-tag").write_text(tag, encoding="ascii")
    (output / "release-notes.md").write_text(
        f"Сборка Horizon из [релиза upstream](https://github.com/{UPSTREAM}/releases/tag/{quote(upstream_tag, safe='')}).\n\n"
        "Скачайте Horizon.ctaddon и проверьте установку, первый запуск на Windows и вход второго игрока. "
        "После проверки отправьте файл на рассмотрение через ConnectTogether.\n",
        encoding="utf-8",
    )


def main(output):
    entry = next(entry for entry in load_catalog(CATALOG) if entry["id"] == "horizon")
    published = json.loads(download(CATALOG, entry))
    tag, asset = latest_asset()
    with tempfile.TemporaryDirectory() as directory:
        build(published, tag, asset, output, Path(directory))


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]))
    except (ValueError, KeyError) as error:
        raise SystemExit(str(error)) from None
