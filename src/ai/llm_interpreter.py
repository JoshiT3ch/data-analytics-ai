import json
import os
import re

from src.ai.chart_parser import parse_chart_request
from src.ai.formula_parser import parse_formula_request
from src.ai.intent_classifier import classify_intent
from src.core.command_registry import get_command_metadata, supported_commands
from src.core.session_memory import load_session_memory

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    from openai import OpenAI, OpenAIError
except ImportError:
    OpenAI = None
    OpenAIError = Exception


DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_COMMAND = "summarize"
DEFAULT_FILE_PATH = "data/raw/test.xlsx"
MIN_LLM_CONFIDENCE = 0.5
RAW_DATA_DIR = os.path.join("data", "raw")
SUPPORTED_COMMANDS = supported_commands()
EXCEL_PATH_PATTERN = re.compile(
    r'"([^"]+\.xlsx)"|\'([^\']+\.xlsx)\'|([^\s,;:)]+\.xlsx)',
    re.IGNORECASE,
)
COMMAND_PATTERNS = {
    "list-sheets": [
        r"\blist sheets\b",
        r"\bshow sheets\b",
        r"\blist tabs\b",
        r"\bshow tabs\b",
        r"\bworkbook tabs\b",
    ],
    "set-current-sheet": [
        r"\buse\s+(?:the\s+)?[a-z0-9 _-]+?\s+(?:sheet|tab)\b",
        r"\bset current sheet\b",
    ],
    "add-formula-column": [
        r"\badd a formula column\b",
        r"\bcreate a formula column\b",
        r"\badd calculated column\b",
        r"\bcreate calculated column\b",
        r"\bcalculate profit\b",
        r"\bcalculate margin\b",
        r"\bprofit margin\b",
        r"\bcreate a new column called\b",
        r"\badd a column called\b",
        r"\busing\s+\w+.*\b(?:minus|plus|times|multiply|divide|divided by)\b",
    ],
    "build-dashboard": [
        r"\bbuild dashboard\b",
        r"\bcreate dashboard\b",
        r"\bgenerate dashboard\b",
        r"\bauto dashboard\b",
        r"\bdashboard report\b",
        r"\bdashboard\b",
        r"\bcombine summary\b.*\bcharts\b.*\binsights\b",
    ],
    "generate-insights": [
        r"\bgive me insights\b",
        r"\bgenerate insights\b",
        r"\binsights\b",
        r"\banalyze this dataset\b",
        r"\banalyse this dataset\b",
        r"\banalyze trends\b",
        r"\banalyse trends\b",
        r"\bfind patterns\b",
        r"\bfind recommendations\b",
        r"\brecommendations\b",
        r"\bexplain this dataset\b",
        r"\bwhat does this data mean\b",
        r"\bdata analysis report\b",
        r"\bbusiness insights\b",
    ],
    "create-chart": [
        r"\bchart\b",
        r"\bgraph\b",
        r"\bvisualize\b",
        r"\bvisualise\b",
        r"\bplot\b",
        r"\bhistogram\b",
        r"\bdistribution\b",
        r"\btrend\b",
    ],
    "clean-duplicates": [
        r"\bduplicate\b",
        r"\bduplicates\b",
        r"\bduplicated\b",
        r"\bdedupe\b",
    ],
    "summarize": [
        r"\bsummarize\b",
        r"\bsummary\b",
        r"\banalyze\b",
        r"\banalyse\b",
        r"\bdescribe\b",
        r"\breport\b",
    ],
    "remove-empty-rows": [
        r"\bempty\b",
        r"\bblank\b",
        r"\bnull\b",
        r"\bmissing\b",
    ],
    "detect-columns": [
        r"\bcolumn\b",
        r"\bcolumns\b",
        r"\bdata type\b",
        r"\bdtype\b",
        r"\bschema\b",
        r"\bstructure\b",
        r"\bfields\b",
    ],
}
CHART_OPTION_FIELDS = ("chart_type", "x_column", "y_column", "title")
INSIGHT_OPTION_FIELDS = ("target_column", "group_by")
FORMULA_OPTION_FIELDS = ("new_column", "left_column", "operator", "right_column")
SHEET_OPTION_FIELDS = ("sheet_name",)
SESSION_FILE_COMMANDS = {
    "create-chart",
    "generate-insights",
    "build-dashboard",
    "add-formula-column",
    "list-sheets",
    "set-current-sheet",
}
DASHBOARD_OPTION_FIELDS = ("target_column", "group_by")
DASHBOARD_PATTERNS = COMMAND_PATTERNS["build-dashboard"]
INSIGHT_PATTERNS = COMMAND_PATTERNS["generate-insights"]


def _safe_print(*values):
    try:
        print(*values)
    except UnicodeEncodeError:
        safe_values = [
            str(value).encode("ascii", errors="replace").decode("ascii")
            for value in values
        ]
        print(*safe_values)


def _normalize_file_path(file_path):
    if file_path is None:
        return None

    clean_path = str(file_path).strip().strip('"').strip("'").strip(",.;:)")

    if not clean_path or clean_path.lower() == "null":
        return None

    if not clean_path.lower().endswith(".xlsx"):
        return None

    if "/" in clean_path or "\\" in clean_path:
        return clean_path

    return f"data/raw/{clean_path}"


def _title_case(value):
    words = re.findall(r"[A-Za-z0-9_-]+", str(value or ""))
    return " ".join(word.capitalize() for word in words)


def _extract_file_path(user_input):
    if not isinstance(user_input, str):
        return None

    match = EXCEL_PATH_PATTERN.search(user_input)
    if not match:
        return None

    raw_path = next((group for group in match.groups() if group), None)
    return _normalize_file_path(raw_path)


def _extract_sheet_name(user_input):
    if not isinstance(user_input, str):
        return None

    text = EXCEL_PATH_PATTERN.sub("", user_input).strip()
    patterns = [
        r"\bset current sheet to\s+(?:the\s+)?(?P<sheet>[A-Za-z0-9 _-]+?)(?:\s+(?:sheet|tab))?(?:\s+(?:from|in|on)\b|$)",
        r"\buse\s+(?:the\s+)?(?P<sheet>[A-Za-z0-9 _-]+?)\s+(?:sheet|tab)\b",
        r"\b(?:summarize|summarise|describe|analyze|analyse)\s+(?:the\s+)?(?P<sheet>[A-Za-z0-9 _-]+?)\s+(?:sheet|tab)\b",
        r"\b(?:from|in|on)\s+(?:the\s+)?(?P<sheet>[A-Za-z0-9 _-]+?)\s+(?:sheet|tab)\b",
        r"\b(?:from|in|on)\s+(?:the\s+)?(?P<sheet>[A-Za-z0-9 _-]+?)\s+(?:worksheet)\b",
        r"\b(?:the\s+)?(?P<sheet>[A-Za-z0-9 _-]+?)\s+(?:sheet|tab)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _title_case(match.group("sheet").strip())

    return None


def _default_file_path():
    try:
        if os.path.isdir(RAW_DATA_DIR):
            excel_files = sorted(
                file_name
                for file_name in os.listdir(RAW_DATA_DIR)
                if file_name.lower().endswith(".xlsx")
            )
            if excel_files:
                return f"data/raw/{excel_files[0]}"
    except OSError:
        pass

    return DEFAULT_FILE_PATH


def _current_session_file():
    current_file = load_session_memory().get("current_file")
    if isinstance(current_file, str) and current_file.lower().endswith(".xlsx"):
        return current_file
    return None


def _plan_response(plan):
    return {"steps": plan}


def _get_confidence(value, default=0.65):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = default

    return max(0.0, min(confidence, 1.0))


def _predict_output_file(command, file_path):
    metadata = get_command_metadata(command) or {}
    output_path_builder = metadata.get("output_path")

    if callable(output_path_builder) and metadata.get("chainable_output") and file_path:
        return output_path_builder(file_path)

    return None


def _find_command_mentions(user_input):
    text = user_input.lower()
    mentions = []

    for command, patterns in COMMAND_PATTERNS.items():
        positions = []
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                positions.append(match.start())

        if positions:
            mentions.append((min(positions), command))

    mentions.sort(key=lambda item: item[0])

    return [command for _, command in mentions]


def _is_insight_request(user_input):
    text = str(user_input or "").lower()
    return any(re.search(pattern, text) for pattern in INSIGHT_PATTERNS)


def _is_dashboard_request(user_input):
    text = str(user_input or "").lower()
    return any(re.search(pattern, text) for pattern in DASHBOARD_PATTERNS)


def _file_path_for_command(command, user_input):
    explicit_file = _extract_file_path(user_input)

    if command in SESSION_FILE_COMMANDS:
        return explicit_file or _current_session_file()

    return explicit_file or _default_file_path()


def _fallback_plan(user_input, reason):
    safe_input = user_input if isinstance(user_input, str) else ""
    requested_sheet = _extract_sheet_name(safe_input)
    dashboard_request = _is_dashboard_request(safe_input)
    insight_request = _is_insight_request(safe_input)
    formula_request = parse_formula_request(safe_input)
    chart_request = (
        None
        if dashboard_request or insight_request or formula_request
        else parse_chart_request(safe_input)
    )
    if formula_request:
        file_path = _file_path_for_command("add-formula-column", safe_input)
        formula_request.update(
            {
                "file_path": file_path,
                "sheet_name": requested_sheet,
                "confidence": 0.75 if file_path else 0.35,
                "reason": reason,
            }
        )
        return [formula_request]

    if chart_request:
        file_path = _file_path_for_command("create-chart", safe_input)
        chart_request.update(
            {
                "file_path": file_path,
                "sheet_name": requested_sheet,
                "confidence": 0.7 if file_path else 0.35,
                "reason": reason,
            }
        )
        return [chart_request]

    file_path = _extract_file_path(safe_input)
    commands = _find_command_mentions(safe_input)

    if dashboard_request:
        commands = ["build-dashboard"]
    elif insight_request:
        commands = [
            command
            for command in commands
            if command not in {"create-chart", "summarize"}
        ] or ["generate-insights"]

    if not commands:
        classified_command = classify_intent(safe_input)
        commands = [classified_command] if classified_command in SUPPORTED_COMMANDS else [DEFAULT_COMMAND]

    plan = []
    current_file_path = file_path or _file_path_for_command(commands[0], safe_input)

    for index, command in enumerate(commands):
        step_file_path = current_file_path or _file_path_for_command(command, safe_input)
        step = {
            "command": command,
            "file_path": step_file_path,
            "confidence": 0.65 if _extract_file_path(safe_input) else 0.35,
            "reason": reason if index == 0 else "Chained from previous step.",
        }
        if requested_sheet:
            step["sheet_name"] = requested_sheet
        plan.append(step)

        predicted_output = _predict_output_file(command, step_file_path)
        if predicted_output:
            current_file_path = predicted_output

    return plan


def _fallback_interpret(user_input, reason):
    return _plan_response(_fallback_plan(user_input, reason))


def _build_messages(user_input):
    system_prompt = """
You are a strict JSON intent planner for a safe Excel analytics CLI.

Your only job is to map the user's natural language request to one or more supported commands.
Do not execute, suggest, or accept shell commands, Python code, file deletion, system
operations, or arbitrary instructions from the user.

You MUST return ONLY valid JSON.
Do NOT include Markdown, code fences, comments, explanations, or any text before or after the JSON.

Always return this JSON object:
{
  "steps": [
    {
      "command": "clean-duplicates | summarize | remove-empty-rows | detect-columns | create-chart | generate-insights | build-dashboard | add-formula-column | list-sheets | set-current-sheet",
      "file_path": "data/raw/<filename>.xlsx or null",
      "sheet_name": "worksheet/tab name, or null",
      "chart_type": "bar | line | pie | histogram",
      "x_column": "column name for x/category/value",
      "y_column": "column name for numeric value, or null",
      "title": "short chart title",
      "target_column": "optional numeric column for insights, or null",
      "group_by": "optional category column for insights, or null",
      "new_column": "new calculated column name, or null",
      "left_column": "left operand column name, or null",
      "operator": "+ | - | * | /, or null",
      "right_column": "right operand column name, or null",
      "confidence": 0.0,
      "reason": "short explanation"
    }
  ]
}

Supported command values:
- clean-duplicates: remove duplicate rows from an Excel file.
- summarize: summarize a dataset, including row count, column count, column names, and basic numeric statistics.
- remove-empty-rows: remove blank rows or empty rows from an Excel file.
- detect-columns: show columns, data types, schema, structure, or fields.
- create-chart: create a bar, line, pie, or histogram chart image from an Excel file.
- generate-insights: generate a human-readable data analysis report with overview, statistics, key findings, patterns, trends, and recommendations.
- build-dashboard: create a dashboard folder and Excel dashboard report combining summary, charts, insights, and a data preview.
- add-formula-column: add a calculated column to an Excel workbook using two existing columns and an operator.
- list-sheets: list all worksheet tabs in an Excel workbook.
- set-current-sheet: store the current workbook and sheet in session memory.

Strict rules:
- Every command must be exactly one of: clean-duplicates, summarize, remove-empty-rows, detect-columns, create-chart, generate-insights, build-dashboard, add-formula-column, list-sheets, set-current-sheet.
- Every file_path must be a non-empty .xlsx path, except create-chart, generate-insights, build-dashboard, add-formula-column, list-sheets, and set-current-sheet may use null when the user did not provide a file.
- A single-step request must still return a steps array with one object.
- If the user provides only a filename like test.xlsx, return data/raw/test.xlsx.
- If the user provides a path like data/raw/test.xlsx or C:\\data\\test.xlsx, keep that path.
- If no .xlsx file is mentioned for create-chart, generate-insights, build-dashboard, add-formula-column, list-sheets, or set-current-sheet, use null.
- If no .xlsx file is mentioned for any other command, use data/raw/test.xlsx.
- Preserve the requested order of operations.
- If one step creates a cleaned Excel output, use that output file for the next step.
- clean-duplicates writes outputs/<name>_cleaned.xlsx.
- remove-empty-rows writes outputs/<name>_no_empty.xlsx.
- For bar and line charts, set chart_type, x_column, y_column, and title.
- For pie charts, set chart_type, x_column, y_column as null unless the user asks for a numeric value, and title.
- For histograms, set chart_type, x_column, y_column as null, and title.
- For "sales by category", use x_column "Category" and y_column "Sales".
- For "revenue trend by month", use chart_type "line", x_column "Month", y_column "Revenue", and title "Revenue Trend by Month".
- For "give me insights", "analyze trends", "find patterns", "find recommendations", "explain this dataset", "what does this data mean", "data analysis report", or "business insights", use command "generate-insights".
- For "dashboard", "build dashboard", "create dashboard", "auto dashboard", or "dashboard report", use command "build-dashboard".
- For formula requests, use command "add-formula-column" and set new_column, left_column, operator, and right_column.
- Map plus/add/+ to "+", minus/subtract/- to "-", times/multiply/* to "*", and divided by/divide// to "/".
- For "profit using revenue minus cost", set new_column "Profit", left_column "Revenue", operator "-", and right_column "Cost".
- For "total with quantity times price", set new_column "Total", left_column "Quantity", operator "*", and right_column "Price".
- For "profit margin from revenue and cost", set new_column "Profit Margin", left_column "Profit", operator "/", and right_column "Revenue".
- For "list sheets", "show sheets", "list tabs", "show tabs", or "workbook tabs", use command "list-sheets".
- For "use the Sales sheet" or "set current sheet to Sales", use command "set-current-sheet" and set sheet_name "Sales".
- If the user mentions "from the Sales sheet", "in the Sales tab", or similar, set sheet_name to that sheet for the command.
- confidence must be a number between 0 and 1.
- reason must be short and must not contain Markdown.
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]


def _response_format():
    return {"type": "json_object"}


def _plan_meets_confidence(plan, threshold=MIN_LLM_CONFIDENCE):
    return all(step.get("confidence", 0.0) >= threshold for step in plan)


def _create_completion(client, user_input):
    return client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        messages=_build_messages(user_input),
        response_format=_response_format(),
        temperature=0,
    )


def _load_llm_json(client, user_input):
    last_response_text = ""

    for attempt in range(1, 3):
        response = _create_completion(client, user_input)
        response_text = response.choices[0].message.content or ""
        last_response_text = response_text
        _safe_print("LLM RAW RESPONSE:", response_text)

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            if attempt == 1:
                print("LLM returned invalid JSON. Retrying once.")

    raise json.JSONDecodeError("Invalid LLM JSON after retry.", last_response_text, 0)


def _extract_steps(interpreted_request):
    if isinstance(interpreted_request, list):
        return interpreted_request

    if not isinstance(interpreted_request, dict):
        return []

    steps = interpreted_request.get("steps")
    if isinstance(steps, list):
        return steps

    return [interpreted_request]


def normalize_plan(interpreted_request, user_input=None):
    steps = _extract_steps(interpreted_request)
    if not steps:
        return []

    source_file_path = _extract_file_path(user_input)
    source_sheet_name = _extract_sheet_name(user_input)
    parsed_chart_request = parse_chart_request(user_input)
    plan = []
    current_file_path = None

    for index, raw_step in enumerate(steps):
        if not isinstance(raw_step, dict):
            return []

        command = str(raw_step.get("command") or "").strip()
        if command not in SUPPORTED_COMMANDS:
            return []

        raw_file_path = _normalize_file_path(raw_step.get("file_path"))
        if index == 0:
            if command in SESSION_FILE_COMMANDS:
                file_path = raw_file_path or source_file_path or _current_session_file()
            else:
                file_path = raw_file_path or source_file_path or _default_file_path()
        elif current_file_path:
            file_path = current_file_path
        else:
            if command in SESSION_FILE_COMMANDS:
                file_path = source_file_path or _current_session_file()
            else:
                file_path = source_file_path or _default_file_path()

        if not file_path and command not in SESSION_FILE_COMMANDS:
            return []

        step = {
            "command": command,
            "file_path": file_path,
            "confidence": _get_confidence(raw_step.get("confidence")),
            "reason": str(raw_step.get("reason") or "Parsed request.").strip(),
        }

        raw_sheet_name = raw_step.get("sheet_name") or source_sheet_name
        if raw_sheet_name:
            step["sheet_name"] = str(raw_sheet_name).strip()

        if command == "create-chart":
            chart_defaults = parsed_chart_request or {}
            for field in CHART_OPTION_FIELDS:
                value = raw_step.get(field)
                if value in (None, ""):
                    value = chart_defaults.get(field)
                step[field] = value
        elif command == "generate-insights":
            for field in INSIGHT_OPTION_FIELDS:
                value = raw_step.get(field)
                if value not in (None, ""):
                    step[field] = value
        elif command == "build-dashboard":
            for field in DASHBOARD_OPTION_FIELDS:
                value = raw_step.get(field)
                if value not in (None, ""):
                    step[field] = value
        elif command == "add-formula-column":
            formula_defaults = parse_formula_request(user_input) or {}
            for field in FORMULA_OPTION_FIELDS:
                value = raw_step.get(field)
                if value in (None, ""):
                    value = formula_defaults.get(field)
                if value not in (None, ""):
                    step[field] = value

        plan.append(step)

        predicted_output = _predict_output_file(command, file_path)
        current_file_path = predicted_output or file_path

    return plan


def interpret_user_request(user_input: str):
    if not isinstance(user_input, str) or not user_input.strip():
        return _fallback_interpret(
            user_input,
            "User input was empty; used rule-based fallback.",
        )

    load_dotenv(dotenv_path=".env")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("No API key found. Using rule-based fallback.")
        return _fallback_interpret(
            user_input,
            "OPENAI_API_KEY is missing; used rule-based fallback.",
        )

    if OpenAI is None:
        return _fallback_interpret(
            user_input,
            "OpenAI SDK is not installed; used rule-based fallback.",
        )

    try:
        client = OpenAI(api_key=api_key)
        try:
            data = _load_llm_json(client, user_input)
        except json.JSONDecodeError:
            return _fallback_interpret(
                user_input,
                "LLM response was not valid JSON after retry; used rule-based fallback.",
            )

        plan = normalize_plan(data, user_input)
        if not plan:
            return _fallback_interpret(
                user_input,
                "LLM response was missing a supported command or file path; used rule-based fallback.",
            )

        if not _plan_meets_confidence(plan):
            return _fallback_interpret(
                user_input,
                "LLM confidence was below threshold; used rule-based fallback.",
            )

        return _plan_response(plan)

    except OpenAIError as error:
        return _fallback_interpret(
            user_input,
            f"OpenAI API request failed; used rule-based fallback. {error}",
        )
    except Exception as error:
        return _fallback_interpret(
            user_input,
            f"Interpreter error; used rule-based fallback. {error}",
        )
