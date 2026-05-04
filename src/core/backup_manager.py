import re
import shutil
from datetime import datetime
from pathlib import Path


BACKUP_DIR = Path("backups")
OUTPUT_DIR = Path("outputs")


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_command_name(command):
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", str(command or "command")).strip("_")
    return safe_name or "command"


def _unique_path(path):
    if not path.exists():
        return path

    timestamp = _timestamp()
    candidate = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
    counter = 1

    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{timestamp}_{counter}{path.suffix}")
        counter += 1

    return candidate


def create_backup(file_path, command):
    """Create a timestamped backup of an Excel file before a transform command runs."""
    source = Path(file_path)
    if not source.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    command_name = _safe_command_name(command)
    backup_name = f"{source.stem}_before_{command_name}_{_timestamp()}{source.suffix}"
    backup_path = _unique_path(BACKUP_DIR / backup_name)

    shutil.copy2(source, backup_path)
    return backup_path.as_posix()


def restored_output_path(original_file):
    """Build a safe output path for an undo restore without overwriting existing files."""
    source = Path(original_file or "restored.xlsx")
    suffix = source.suffix or ".xlsx"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return _unique_path(OUTPUT_DIR / f"{source.stem}_restored{suffix}").as_posix()


def restore_backup(backup_file, restored_file):
    source = Path(backup_file)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    destination = Path(restored_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

    return destination.as_posix()
