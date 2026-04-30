import sys
from src.core.router import route_command
from src.core.nlp_parser import parse_input

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("1. python -m src.main <command> <file>")
        print("2. python -m src.main \"natural language input\"")
        return

    # 👉 If only one argument → treat as natural language
    if len(sys.argv) == 2:
        user_input = sys.argv[1]
        command, file_path = parse_input(user_input)

        if not command or not file_path:
            print("❌ Could not understand input")
            return

        route_command(command, file_path)

    else:
        command = sys.argv[1]
        file_path = sys.argv[2]
        route_command(command, file_path)


if __name__ == "__main__":
    main()