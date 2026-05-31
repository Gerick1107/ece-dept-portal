import os
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


def course_slug(course_title: str) -> str:
    """Short filesystem-safe token from course name (e.g. ADC, BE_FW)."""
    if not course_title:
        return "course"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", course_title.strip())
    slug = slug.strip("_")[:48]
    return slug or "course"


def result_filename(course_title: str) -> str:
    return f"{course_slug(course_title)}_CO_PO_Percentage_Results.xlsx"


def ensure_storage_dirs() -> None:
    for path in (settings.upload_dir, settings.results_dir, settings.archive_dir):
        Path(path).mkdir(parents=True, exist_ok=True)


def allowed_file(filename: str | None) -> bool:
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[-1].lower() in {"xlsx"}


def _build_stored_name(prefix: str, original: str, course_title: str | None = None) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (original or "upload.xlsx"))
    if course_title:
        slug = course_slug(course_title)
        short_id = uuid.uuid4().hex[:8]
        return f"{slug}_{prefix}_{short_id}.xlsx"
    return f"{prefix}_{uuid.uuid4().hex}_{safe}"


async def save_upload(
    upload: UploadFile,
    prefix: str,
    course_title: str | None = None,
) -> str:
    ensure_storage_dirs()
    unique_name = _build_stored_name(prefix, upload.filename or "upload.xlsx", course_title)
    dest = Path(settings.upload_dir) / unique_name
    content = await upload.read()
    dest.write_bytes(content)
    return str(dest)


def save_bytes_to_uploads(
    content: bytes,
    prefix: str,
    filename: str,
    course_title: str | None = None,
) -> str:
    ensure_storage_dirs()
    unique_name = _build_stored_name(prefix, filename, course_title)
    dest = Path(settings.upload_dir) / unique_name
    dest.write_bytes(content)
    return str(dest)


def finalize_result_workbook(generated_path: str, course_title: str) -> str:
    """
    Move engine output into storage/results/ with a course-based filename.
    """
    ensure_storage_dirs()
    if not generated_path or not os.path.exists(generated_path):
        return generated_path
    unique_name = f"{course_slug(course_title)}_{uuid.uuid4().hex[:10]}_CO_PO_Percentage_Results.xlsx"
    dest = Path(settings.results_dir) / unique_name
    if os.path.abspath(generated_path) != os.path.abspath(dest):
        shutil.move(generated_path, dest)
    return str(dest)


def remove_file_if_exists(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def cleanup_upload_directory() -> int:
    ensure_storage_dirs()
    removed = 0
    now = time.time()
    upload_root = Path(settings.upload_dir)
    for item in upload_root.iterdir():
        if item.is_file() and (
            item.name.startswith("normalized_")
            or (now - item.stat().st_mtime) > settings.file_max_age_seconds
        ):
            try:
                item.unlink()
                removed += 1
            except OSError:
                pass
    normalized_temp = Path(settings.upload_dir).parent / "temp" / "normalized"
    if normalized_temp.exists():
        for item in normalized_temp.iterdir():
            if item.is_file() and (now - item.stat().st_mtime) > settings.file_max_age_seconds:
                try:
                    item.unlink()
                    removed += 1
                except OSError:
                    pass
    results_root = Path(settings.results_dir)
    if results_root.exists():
        for item in results_root.iterdir():
            if item.is_file() and item.suffix.lower() == ".xlsx":
                if (now - item.stat().st_mtime) > settings.file_max_age_seconds:
                    try:
                        item.unlink()
                        removed += 1
                    except OSError:
                        pass
    return removed


def archive_result_file(source_path: str, evaluation_public_id: str, course_title: str | None = None) -> str:
    ensure_storage_dirs()
    if not source_path or not os.path.exists(source_path):
        raise FileNotFoundError("Result file not found for archiving")
    if course_title:
        name = f"{course_slug(course_title)}_{Path(source_path).name}"
    else:
        name = f"{evaluation_public_id}_{Path(source_path).name}"
    dest = Path(settings.archive_dir) / name
    shutil.copy2(source_path, dest)
    return str(dest)
