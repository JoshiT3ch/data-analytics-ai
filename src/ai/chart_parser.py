import re


CHART_KEYWORDS = (
    "chart",
    "graph",
    "visualize",
    "visualise",
    "plot",
    "histogram",
    "distribution",
    "trend",
)

TRAILING_FILE_PATTERN = re.compile(r"\s+from\s+.+?\.xlsx\b.*$", re.IGNORECASE)
FILLER_WORDS = {
    "a",
    "an",
    "the",
    "total",
    "sum",
    "count",
    "number",
    "chart",
    "graph",
    "plot",
    "visualize",
    "visualise",
    "create",
    "make",
    "show",
}


def is_chart_request(user_input):
    text = str(user_input or "").lower()
    return any(keyword in text for keyword in CHART_KEYWORDS)


def _strip_file_reference(text):
    return TRAILING_FILE_PATTERN.sub("", text).strip()


def _title_case(value):
    words = re.findall(r"[A-Za-z0-9]+", str(value or ""))
    return " ".join(word.capitalize() for word in words)


def _clean_column_phrase(value):
    words = re.findall(r"[A-Za-z0-9]+", str(value or "").lower())
    useful_words = [word for word in words if word not in FILLER_WORDS]
    if not useful_words:
        return None
    return _title_case(" ".join(useful_words))


def _last_column_word(value):
    words = re.findall(r"[A-Za-z0-9]+", str(value or "").lower())
    useful_words = [
        word
        for word in words
        if word not in FILLER_WORDS and word not in {"distribution", "breakdown"}
    ]
    if not useful_words:
        return None
    return _title_case(useful_words[-1])


def _chart_type(text):
    lowered = text.lower()

    if "pie" in lowered:
        return "pie"
    if "bar" in lowered:
        return "bar"
    if "line" in lowered or "trend" in lowered:
        return "line"
    if "histogram" in lowered or "distribution" in lowered:
        return "histogram"

    return "bar"


def _match_of_by(text):
    match = re.search(
        r"\bof\s+(?P<y>[A-Za-z0-9_ ]+?)\s+by\s+(?P<x>[A-Za-z0-9_ ]+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None

    return (
        _clean_column_phrase(match.group("x")),
        _clean_column_phrase(match.group("y")),
    )


def _match_trend(text):
    match = re.search(
        r"\b(?P<y>[A-Za-z0-9_ ]+?)\s+trend\s+by\s+(?P<x>[A-Za-z0-9_ ]+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None

    return (
        _clean_column_phrase(match.group("x")),
        _clean_column_phrase(match.group("y")),
    )


def _match_histogram(text):
    match = re.search(
        r"\b(?:histogram|distribution)\s+of\s+(?P<x>[A-Za-z0-9_ ]+)$|\bof\s+(?P<x2>[A-Za-z0-9_ ]+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    return _clean_column_phrase(match.group("x") or match.group("x2"))


def _match_pie(text):
    match = re.search(r"\bof\s+(?P<x>[A-Za-z0-9_ ]+)$", text, re.IGNORECASE)
    if not match:
        return None, None

    phrase = match.group("x").strip()
    title = _title_case(phrase)
    x_column = _last_column_word(phrase)
    if "distribution" not in phrase.lower() and "breakdown" not in phrase.lower():
        title = f"{_title_case(phrase)} Distribution"

    return x_column, title


def parse_chart_request(user_input):
    if not is_chart_request(user_input):
        return None

    text = _strip_file_reference(str(user_input or ""))
    chart_type = _chart_type(text)
    x_column = None
    y_column = None
    title = None

    if chart_type == "histogram":
        x_column = _match_histogram(text)
        if x_column:
            title = f"{x_column} Distribution"
    elif chart_type == "pie":
        x_column, title = _match_pie(text)
    elif chart_type == "line":
        x_column, y_column = _match_trend(text)
        if not x_column or not y_column:
            x_column, y_column = _match_of_by(text)
        if x_column and y_column:
            title = f"{y_column} Trend by {x_column}" if "trend" in text.lower() else f"{y_column} by {x_column}"
    else:
        x_column, y_column = _match_of_by(text)
        if x_column and y_column:
            title = f"{y_column} by {x_column}"

    return {
        "command": "create-chart",
        "chart_type": chart_type,
        "x_column": x_column,
        "y_column": y_column,
        "title": title,
    }
