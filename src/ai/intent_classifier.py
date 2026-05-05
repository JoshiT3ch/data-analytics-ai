def classify_intent(user_input):
    text = user_input.lower()

    if (
        "insight" in text
        or "analyze trends" in text
        or "analyse trends" in text
        or "analyze this dataset" in text
        or "analyse this dataset" in text
        or "find patterns" in text
        or "find recommendations" in text
        or "recommendations" in text
        or "explain this dataset" in text
        or "what does this data mean" in text
        or "data analysis report" in text
        or "business insights" in text
    ):
        return "generate-insights"

    if (
        "chart" in text
        or "graph" in text
        or "visualize" in text
        or "visualise" in text
        or "plot" in text
        or "histogram" in text
        or "distribution" in text
        or "trend" in text
    ):
        return "create-chart"

    if "duplicate" in text or "duplicates" in text or "duplicated" in text:
        return "clean-duplicates"

    if "empty" in text or "blank" in text or "null" in text:
        return "remove-empty-rows"

    if "summary" in text or "summarize" in text or "describe" in text:
        return "summarize"

    if "column" in text or "columns" in text or "data type" in text or "dtype" in text:
        return "detect-columns"

    return None
