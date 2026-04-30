from src.core.command_registry import COMMANDS


def route_command(command, file_path):
    func = COMMANDS.get(command)

    if func:
        return func(file_path)

    message = f"Unknown command: {command}"
    print(message)
    print(f"Available commands: {list(COMMANDS.keys())}")
    return {
        "status": "error",
        "output_file": None,
        "message": message,
    }
