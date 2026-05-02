from src.ai.llm_interpreter import interpret_user_request, normalize_plan
from src.core.memory import resolve_file_reference


def parse_input(user_input):
    plan = parse_plan(user_input)
    if not plan:
        return None, None

    command = plan[0].get("command")
    file_path = plan[0].get("file_path")

    return command, file_path


def parse_plan(user_input):
    interpreted_request = interpret_user_request(user_input)
    plan = normalize_plan(interpreted_request, user_input)
    return resolve_file_reference(user_input, plan)
