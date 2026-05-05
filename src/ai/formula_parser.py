import re


FORMULA_KEYWORDS = (
    "formula column",
    "calculated column",
    "calculate profit",
    "calculate margin",
    "profit margin",
    "new column called",
    "column called",
)

OPERATOR_WORDS = {
    "+": "+",
    "plus": "+",
    "add": "+",
    "added to": "+",
    "-": "-",
    "minus": "-",
    "subtract": "-",
    "subtracted from": "-",
    "*": "*",
    "times": "*",
    "multiply": "*",
    "multiplied by": "*",
    "/": "/",
    "divide": "/",
    "divided by": "/",
}

TRAILING_FILE_REFERENCE = re.compile(r"\s+from\s+[^\s,;:)]+\.xlsx\b.*$", re.IGNORECASE)
TRAILING_SHEET_REFERENCE = re.compile(
    r"\s+(?:from|in|on)\s+(?:the\s+)?[A-Za-z0-9 _-]+?\s+(?:sheet|tab|worksheet)\b.*$",
    re.IGNORECASE,
)
EXCEL_PATH_PATTERN = re.compile(
    r'"([^"]+\.xlsx)"|\'([^\']+\.xlsx)\'|([^\s,;:)]+\.xlsx)',
    re.IGNORECASE,
)


def is_formula_request(user_input):
    text = str(user_input or "").lower()
    if any(keyword in text for keyword in FORMULA_KEYWORDS):
        return True

    return bool(
        re.search(
            r"\b[a-z][a-z0-9_ ]+\s+(?:minus|plus|times|multiplied by|divided by|\+|-|\*|/)\s+[a-z][a-z0-9_ ]+\b",
            text,
        )
    )


def _title_case(value):
    words = re.findall(r"[A-Za-z0-9]+", str(value or ""))
    return " ".join(word.capitalize() for word in words)


def _strip_file_reference(text):
    clean_text = TRAILING_FILE_REFERENCE.sub("", str(text or "")).strip()
    clean_text = EXCEL_PATH_PATTERN.sub("", clean_text).strip()
    clean_text = TRAILING_SHEET_REFERENCE.sub("", clean_text).strip()
    return re.sub(r"\s+", " ", clean_text).strip(" ,.;:")


def _clean_column_phrase(value):
    text = str(value or "").strip().strip(" ,.;:")
    text = re.sub(r"\b(?:a|an|the)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return _title_case(text)


def _extract_new_column(text):
    patterns = [
        r"\b(?:add|create)\s+(?:a\s+)?(?:new\s+)?(?:formula\s+|calculated\s+)?column\s+(?:called|named)\s+(?P<name>.+?)\s+(?:using|with|from)\b",
        r"\b(?:add|create)\s+(?:a\s+)?(?:formula\s+|calculated\s+)?column\s+for\s+(?P<name>.+?)\s+(?:using|with|from)\b",
        r"\b(?:add|create)\s+(?:a\s+)?(?:new\s+)?(?:formula\s+|calculated\s+)?column\s+(?P<name>.+?)\s+(?:using|with|from)\b",
        r"\bcalculate\s+(?P<name>.+?)\s+(?:using|with|from)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_column_phrase(match.group("name"))

    return None


def _extract_expression(text):
    for keyword in ("using", "with"):
        match = re.search(rf"\b{keyword}\s+(?P<expr>.+)$", text, re.IGNORECASE)
        if match:
            return match.group("expr").strip(" ,.;:")

    match = re.search(r"\bcalculate\s+.+?\s+from\s+(?P<expr>.+)$", text, re.IGNORECASE)
    if match:
        return match.group("expr").strip(" ,.;:")

    return None


def _parse_operator_expression(expression):
    if not expression:
        return None

    patterns = [
        (r"^(?P<left>.+?)\s+divided\s+by\s+(?P<right>.+)$", "/"),
        (r"^(?P<left>.+?)\s+divide\s+(?P<right>.+)$", "/"),
        (r"^(?P<left>.+?)\s*/\s*(?P<right>.+)$", "/"),
        (r"^(?P<left>.+?)\s+multiplied\s+by\s+(?P<right>.+)$", "*"),
        (r"^(?P<left>.+?)\s+multiply\s+(?P<right>.+)$", "*"),
        (r"^(?P<left>.+?)\s+times\s+(?P<right>.+)$", "*"),
        (r"^(?P<left>.+?)\s*\*\s*(?P<right>.+)$", "*"),
        (r"^subtract\s+(?P<right>.+?)\s+from\s+(?P<left>.+)$", "-"),
        (r"^(?P<left>.+?)\s+minus\s+(?P<right>.+)$", "-"),
        (r"^(?P<left>.+?)\s+subtract\s+(?P<right>.+)$", "-"),
        (r"^(?P<left>.+?)\s*-\s*(?P<right>.+)$", "-"),
        (r"^(?P<left>.+?)\s+plus\s+(?P<right>.+)$", "+"),
        (r"^(?P<left>.+?)\s+add\s+(?P<right>.+)$", "+"),
        (r"^(?P<left>.+?)\s*\+\s*(?P<right>.+)$", "+"),
    ]

    for pattern, operator in patterns:
        match = re.search(pattern, expression, re.IGNORECASE)
        if match:
            return {
                "left_column": _clean_column_phrase(match.group("left")),
                "operator": operator,
                "right_column": _clean_column_phrase(match.group("right")),
            }

    return None


def _parse_profit_margin(text):
    if "profit margin" not in text.lower():
        return None

    if re.search(r"\brevenue\b", text, re.IGNORECASE) and re.search(r"\bcost\b", text, re.IGNORECASE):
        return {
            "new_column": "Profit Margin",
            "left_column": "Profit",
            "operator": "/",
            "right_column": "Revenue",
        }

    return None


def parse_formula_request(user_input):
    if not is_formula_request(user_input):
        return None

    text = _strip_file_reference(user_input)
    profit_margin = _parse_profit_margin(text)
    if profit_margin:
        profit_margin["command"] = "add-formula-column"
        return profit_margin

    new_column = _extract_new_column(text)
    expression = _extract_expression(text)
    parsed_expression = _parse_operator_expression(expression)

    if not new_column or not parsed_expression:
        return None

    return {
        "command": "add-formula-column",
        "new_column": new_column,
        **parsed_expression,
    }
