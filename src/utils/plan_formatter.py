from src.core.command_registry import get_command_metadata


SEPARATOR = "-" * 34


def _expected_chain_output(command, input_file):
    metadata = get_command_metadata(command) or {}
    output_path_builder = metadata.get("output_path")

    if metadata.get("chainable_output") and callable(output_path_builder) and input_file:
        return output_path_builder(input_file)

    return None


def _plan_rows(plan):
    rows = []
    current_file = None

    for index, step in enumerate(plan, start=1):
        if not isinstance(step, dict):
            rows.append(
                {
                    "step": index,
                    "command": "unknown",
                    "input_file": None,
                    "output_file": None,
                    "warning": "Malformed step.",
                }
            )
            continue

        command = step.get("command") or "unknown"
        requested_file = step.get("file_path")
        warning = None

        if current_file and not requested_file:
            input_file = current_file
            warning = "uses previous output"
        elif current_file and requested_file and requested_file != current_file:
            input_file = current_file
            warning = f"uses chained output instead of {requested_file}"
        else:
            input_file = requested_file or current_file

        output_file = _expected_chain_output(command, input_file)
        if output_file:
            current_file = output_file
        elif input_file:
            current_file = input_file

        rows.append(
            {
                "step": index,
                "command": command,
                "input_file": input_file,
                "output_file": output_file,
                "warning": warning,
            }
        )

    return rows


def format_execution_plan(plan):
    lines = ["Execution Plan:", SEPARATOR]

    for row in _plan_rows(plan):
        lines.append(f"Step {row['step']}: {row['command']}")
        lines.append(f"Input: {row['input_file'] or 'not provided'}")

        if row["output_file"]:
            lines.append(f"Output: {row['output_file']}")

        if row["warning"]:
            lines.append(f"Note: {row['warning']}")

        lines.append("")

    if lines[-1] == "":
        lines.pop()

    lines.append(SEPARATOR)
    return "\n".join(lines)


def format_execution_summary(result, plan=None):
    if not isinstance(result, dict):
        return "\n".join(
            [
                "Execution Summary:",
                SEPARATOR,
                "Execution failed",
                "Reason: Unknown executor response",
                SEPARATOR,
            ]
        )

    if result.get("status") != "success":
        return format_execution_error(result, plan)

    title = "Dry Run Summary:" if result.get("message", "").lower().startswith("dry run") else "Execution Summary:"
    lines = [title, SEPARATOR]

    for index, step_result in enumerate(result.get("results", []), start=1):
        command = step_result.get("command", "unknown")
        output_file = step_result.get("output_file")

        if isinstance(output_file, str) and output_file.lower().endswith(".xlsx"):
            outcome = output_file
        else:
            outcome = "success"

        lines.append(f"OK Step {index}: {command} -> {outcome}")

    lines.append(SEPARATOR)
    return "\n".join(lines)


def format_execution_error(result, plan=None):
    failed_step = result.get("failed_step")
    results = result.get("results") or []
    command = "unknown"

    if failed_step and failed_step <= len(results):
        command = results[failed_step - 1].get("command", "unknown")
    elif failed_step and isinstance(plan, list) and failed_step <= len(plan):
        step = plan[failed_step - 1]
        if isinstance(step, dict):
            command = step.get("command", "unknown")
    elif results:
        command = results[-1].get("command", "unknown")

    message = result.get("message") or "Unknown error"

    return "\n".join(
        [
            "Execution Summary:",
            SEPARATOR,
            f"FAILED Step {failed_step or '?'}: {command}",
            f"Reason: {message}",
            SEPARATOR,
        ]
    )
