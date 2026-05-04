from src.core.backup_manager import restore_backup, restored_output_path
from src.core.memory import update_memory_after_step
from src.core.session_memory import (
    latest_backup_entry,
    load_session_memory_with_error,
    record_result,
)


def undo_last_action(file_path=None):
    """Restore the latest backed-up Excel file into a new output workbook."""
    memory, memory_error = load_session_memory_with_error()
    if memory_error:
        message = memory_error
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    backup_entry = latest_backup_entry(memory)
    if not backup_entry:
        message = "No previous file-changing command with a backup was found."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    backup_file = backup_entry.get("backup_file")
    original_file = backup_entry.get("input_file") or file_path
    restored_file = restored_output_path(original_file or backup_file)

    try:
        output_file = restore_backup(backup_file, restored_file)
    except FileNotFoundError:
        message = f"Backup file not found: {backup_file}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }
    except OSError as error:
        message = f"Undo failed: {error}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    message = f"Undo completed. Restored file saved to {output_file}"
    print(message)
    result = {
        "status": "success",
        "command": "undo",
        "input_file": backup_file,
        "output_file": output_file,
        "message": message,
        "result_summary": message,
        "restored_from": backup_file,
        "undone_command": backup_entry.get("command"),
    }

    record_result("undo", backup_file, result)
    update_memory_after_step({"command": "undo", "file_path": backup_file}, result)
    return result
