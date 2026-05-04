from src.commands.undo import undo_last_action
from src.core.command_registry import COMMANDS, get_command_metadata


def _command_options(metadata, options):
    option_fields = metadata.get("option_fields") or ()
    return {
        field: options.get(field)
        for field in option_fields
        if field in options
    }


def route_command(command, file_path=None, preview=False, **options):
    if command == "undo":
        return undo_last_action(file_path)

    func = COMMANDS.get(command)

    if func:
        metadata = get_command_metadata(command) or {}
        if preview and not metadata.get("supports_preview"):
            message = "Preview mode is not yet available for this command."
            print(message)
            return {
                "status": "success",
                "output_file": None,
                "message": message,
                "preview": True,
            }

        if preview:
            return func(file_path, preview=True)

        command_options = _command_options(metadata, options)
        if command_options:
            return func(file_path, **command_options)

        return func(file_path)

    message = f"Unknown command: {command}"
    print(message)
    print(f"Available commands: {list(COMMANDS.keys())}")
    return {
        "status": "error",
        "output_file": None,
        "message": message,
    }
