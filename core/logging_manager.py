# -*- coding: utf-8 -*-
"""Logs centrais do motor e rotacao incremental sem perda de registros.

Regra 34: todo log novo do motor fica em ``logs/``. Os tres projetos concluidos
mais recentes permanecem descompactados; projetos mais antigos recebem um ZIP
verificado e uma copia descompactada em ``logs/archive/unpacked/``. A remocao
futura dessa copia e uma decisao manual/mensal, nunca da rotacao automatica.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from config import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
PROJECT_LOG_DIR = LOG_DIR / "projects"
ARCHIVE_LOG_DIR = LOG_DIR / "archive"
ARCHIVE_UNPACKED_DIR = ARCHIVE_LOG_DIR / "unpacked"
LEGACY_LOG_DIR = LOG_DIR / "legacy"
ROTATION_STATE_FILE = LOG_DIR / "rotation_state.json"
FLOW_EVENTS_FILE = LOG_DIR / "flow_accounts.jsonl"
FLOW_LOG_FILE = LOG_DIR / "flow_accounts.log"

KEEP_UNCOMPACTED_PROJECTS = 3
ROTATE_EVERY_PROJECTS = 3
_LOG_LOCK = threading.RLock()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "motor")).strip("._-")
    return slug[:80] or "motor"


def _now() -> datetime:
    return datetime.now().astimezone()


def _timestamp() -> str:
    return _now().strftime("%Y%m%d_%H%M%S_%f")


def ensure_log_dirs() -> None:
    for directory in (LOG_DIR, PROJECT_LOG_DIR, ARCHIVE_LOG_DIR, ARCHIVE_UNPACKED_DIR, LEGACY_LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        candidate = path.with_name(f"{stem}__{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def migrate_legacy_root_logs() -> list[Path]:
    """Move logs historicos da raiz para logs/legacy sem apagar nem sobrescrever."""
    ensure_log_dirs()
    marker = LOG_DIR / ".legacy_logs_migrated"
    if marker.exists():
        return []
    moved: list[Path] = []
    failures: list[str] = []
    for source in sorted((LOG_DIR.parent).glob("*.log")):
        if not source.is_file():
            continue
        destination = _unique_path(LEGACY_LOG_DIR / source.name)
        try:
            shutil.move(str(source), str(destination))
            moved.append(destination)
        except Exception as exc:
            # Um log ainda aberto por outro processo nao pode ser movido no
            # Windows. Preserva-o na raiz e tenta novamente na proxima execucao.
            failures.append(f"{source.name}: {exc}")
    if not failures:
        marker.write_text(_now().isoformat(timespec="seconds"), encoding="utf-8")
    return moved


def log_flow_event(event: str, account_id: str = "", **fields: Any) -> None:
    """Registra eventos de abertura/falha/ocupacao/cota/liberacao em JSONL e texto."""
    ensure_log_dirs()
    payload: dict[str, Any] = {
        "ts": _now().isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "event": str(event),
        "account_id": str(account_id or ""),
    }
    payload.update(fields)
    line = json.dumps(payload, ensure_ascii=False, default=str)
    with _LOG_LOCK:
        with FLOW_EVENTS_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        details = " | ".join(f"{key}={value}" for key, value in fields.items())
        text = f"{payload['ts']} pid={payload['pid']} {event} {account_id}"
        if details:
            text += f" | {details}"
        with FLOW_LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")


class _TeeStream(TextIO):
    def __init__(self, original: TextIO, log_handle: TextIO) -> None:
        self.original = original
        self.log_handle = log_handle

    def write(self, text: str) -> int:
        written = self.original.write(text)
        self.log_handle.write(text)
        return written

    def flush(self) -> None:
        self.original.flush()
        self.log_handle.flush()

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)

    def fileno(self) -> int:
        return self.original.fileno()

    def isatty(self) -> bool:
        try:
            return self.original.isatty()
        except Exception:
            return False

    @property
    def encoding(self) -> str:
        return getattr(self.original, "encoding", "utf-8")

    @property
    def errors(self) -> str | None:
        return getattr(self.original, "errors", None)


class RunLogSession:
    """Captura stdout/stderr de uma execucao do pipeline para logs/projects/<slug>/."""

    def __init__(self, slug: str, *, migrate_legacy: bool = True) -> None:
        ensure_log_dirs()
        if migrate_legacy:
            migrate_legacy_root_logs()
        self.slug = _safe_slug(slug)
        self.directory = PROJECT_LOG_DIR / self.slug
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / f"pipeline_{_timestamp()}.log"
        self._handle = self.path.open("a", encoding="utf-8", buffering=1)
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._stdout_tee = _TeeStream(self._stdout, self._handle)
        self._stderr_tee = _TeeStream(self._stderr, self._handle)
        self._closed = False

    def start(self) -> "RunLogSession":
        sys.stdout = self._stdout_tee
        sys.stderr = self._stderr_tee
        return self

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._handle.flush()
        finally:
            if sys.stdout is self._stdout_tee:
                sys.stdout = self._stdout
            if sys.stderr is self._stderr_tee:
                sys.stderr = self._stderr
            self._handle.close()
            self._closed = True

    def __enter__(self) -> "RunLogSession":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def begin_run_logging(slug: str, *, migrate_legacy: bool = True) -> RunLogSession:
    return RunLogSession(slug, migrate_legacy=migrate_legacy).start()


def _load_rotation_state() -> dict[str, Any]:
    if ROTATION_STATE_FILE.exists():
        try:
            data = json.loads(ROTATION_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("completed_projects", [])
                data.setdefault("archives", {})
                return data
        except Exception:
            pass
    return {
        "schema": "VIDEOMAKER_LOG_ROTATION_V1",
        "completed_projects": [],
        "archives": {},
    }


def _save_rotation_state(state: dict[str, Any]) -> None:
    ensure_log_dirs()
    temporary = ROTATION_STATE_FILE.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(temporary), str(ROTATION_STATE_FILE))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_manifest(directory: Path, slug: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        files.append({
            "path": path.relative_to(directory).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    return {"slug": slug, "files": files}


def _valid_archive(path: Path, manifest: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        with zipfile.ZipFile(path, "r") as archive:
            if archive.testzip() is not None:
                return False
            names = set(archive.namelist())
            if "manifest.json" not in names:
                return False
            stored = json.loads(archive.read("manifest.json").decode("utf-8"))
            if stored.get("slug") != manifest.get("slug"):
                return False
            stored_files = {row.get("path"): row for row in stored.get("files", []) if isinstance(row, dict)}
            for row in manifest.get("files", []):
                current = stored_files.get(row.get("path"))
                if not current or int(current.get("bytes", -1)) != int(row.get("bytes", -2)):
                    return False
                if current.get("sha256") != row.get("sha256"):
                    return False
                member = f"{manifest['slug']}/{row['path']}"
                if member not in names or int(archive.getinfo(member).file_size) != int(row["bytes"]):
                    return False
            return True
    except Exception:
        return False


def _archive_project_logs(slug: str, source: Path) -> dict[str, Any]:
    ensure_log_dirs()
    manifest = _directory_manifest(source, slug)
    canonical_archive = ARCHIVE_LOG_DIR / f"{slug}.zip"
    archive_path = canonical_archive if _valid_archive(canonical_archive, manifest) else _unique_path(canonical_archive)
    temporary = archive_path.with_name(f".{archive_path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for row in manifest["files"]:
                file_path = source / row["path"]
                archive.write(file_path, arcname=f"{slug}/{row['path']}")
        with zipfile.ZipFile(temporary, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"ZIP de logs corrompido: {temporary}")
        os.replace(str(temporary), str(archive_path))
    finally:
        temporary.unlink(missing_ok=True)

    # A rotacao NUNCA apaga registro: o ZIP e a copia descompactada ficam ambos
    # preservados. Uma limpeza mensal/manual futura pode decidir sobre a copia.
    unpacked_path = _unique_path(ARCHIVE_UNPACKED_DIR / slug)
    shutil.move(str(source), str(unpacked_path))
    return {
        "slug": slug,
        "zip": str(archive_path),
        "unpacked": str(unpacked_path),
        "archived_at": _now().isoformat(timespec="seconds"),
        "files": len(manifest["files"]),
    }


def rotate_project_logs() -> list[dict[str, Any]]:
    """Arquiva projetos fora dos tres mais recentes; incremental e idempotente."""
    ensure_log_dirs()
    with _LOG_LOCK:
        state = _load_rotation_state()
        completed = [str(row.get("slug") or row) if isinstance(row, dict) else str(row)
                     for row in state.get("completed_projects", [])]
        keep = set(completed[-KEEP_UNCOMPACTED_PROJECTS:])
        archived_now: list[dict[str, Any]] = []
        archives = state.setdefault("archives", {})

        for source in sorted(PROJECT_LOG_DIR.iterdir()):
            if not source.is_dir() or source.name in keep:
                continue
            slug = source.name
            try:
                existing = archives.get(slug)
                if isinstance(existing, dict) and Path(str(existing.get("zip") or "")).is_file():
                    existing_zip = Path(str(existing.get("zip")))
                    if _valid_archive(existing_zip, _directory_manifest(source, slug)):
                        # Retomada apos crash entre criar o ZIP e mover a pasta.
                        destination = _unique_path(ARCHIVE_UNPACKED_DIR / slug)
                        shutil.move(str(source), str(destination))
                        existing["unpacked"] = str(destination)
                        continue
                    # Reexecucao de um projeto ja arquivado: preserva o ZIP antigo e
                    # cria um novo pacote incremental, nunca sobrescrevendo historia.
                    history = list(existing.get("zip_history") or [])
                    history.append({
                        "zip": str(existing_zip),
                        "unpacked": str(existing.get("unpacked") or ""),
                        "archived_at": str(existing.get("archived_at") or ""),
                    })
                    record = _archive_project_logs(slug, source)
                    record["zip_history"] = history
                    archives[slug] = record
                    archived_now.append(record)
                    continue
                record = _archive_project_logs(slug, source)
                archives[slug] = record
                archived_now.append(record)
            except Exception as exc:
                # Falha de disco/lock nao invalida um video ja concluido; a rotacao
                # sera retomada de forma idempotente na proxima execucao.
                state.setdefault("rotation_errors", []).append({
                    "slug": slug,
                    "error": str(exc),
                    "at": _now().isoformat(timespec="seconds"),
                })

        state["last_rotation_at"] = _now().isoformat(timespec="seconds")
        state["keep_uncompacted_projects"] = KEEP_UNCOMPACTED_PROJECTS
        state["rotate_every_projects"] = ROTATE_EVERY_PROJECTS
        _save_rotation_state(state)
        return archived_now


def mark_project_completed(
    slug: str,
    *,
    project_dir: Path | None = None,
    output_path: Path | None = None,
    status: str = "approved",
) -> dict[str, Any]:
    """Conta um projeto concluido uma unica vez e dispara a rotacao incremental."""
    safe_slug = _safe_slug(slug)
    with _LOG_LOCK:
        state = _load_rotation_state()
        rows = state.setdefault("completed_projects", [])
        normalized = [str(row.get("slug") or row) if isinstance(row, dict) else str(row) for row in rows]
        now = _now().isoformat(timespec="seconds")
        if safe_slug not in normalized:
            rows.append({
                "slug": safe_slug,
                "completed_at": now,
                "status": str(status),
                "project_dir": str(project_dir or ""),
                "output_path": str(output_path or ""),
            })
        _save_rotation_state(state)
    rotated = rotate_project_logs()
    return {"slug": safe_slug, "archived": rotated, "state": _load_rotation_state()}
