from src.commands.clean_excel import clean_duplicates
from src.commands.summarize import summarize
from src.commands.remove_empty_rows import remove_empty_rows
from src.commands.detect_columns import detect_columns

COMMANDS = {
    "clean-duplicates": clean_duplicates,
    "summarize": summarize,
    "remove-empty-rows": remove_empty_rows,
    "detect-columns": detect_columns,
}

def route_command(command, file_path):
    func = COMMANDS.get(command)

    if func:
        return func(file_path)
    else:
        print(f"❌ Unknown command: {command}")
        print(f"Available commands: {list(COMMANDS.keys())}")