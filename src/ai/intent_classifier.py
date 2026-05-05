def classify_intent(user_input):
    text = user_input.lower()

    if (
        "workbook status" in text
        or "current workbook" in text
        or "current sheet" in text
        or "what workbook am i using" in text
        or "what sheet am i using" in text
        or "show current excel context" in text
        or "show excel context" in text
        or "show workbook context" in text
        or "active workbook" in text
        or "active sheet" in text
    ):
        return "workbook-status"

    if (
        "list sheets" in text
        or "show sheets" in text
        or "list tabs" in text
        or "show tabs" in text
        or "workbook tabs" in text
    ):
        return "list-sheets"

    if "set current sheet" in text or ("use" in text and ("sheet" in text or "tab" in text)):
        return "set-current-sheet"

    if (
        "formula column" in text
        or "calculated column" in text
        or "calculate profit" in text
        or "calculate margin" in text
        or "profit margin" in text
        or "new column called" in text
        or "column called" in text
    ):
        return "add-formula-column"

    if (
        "dashboard" in text
        or "dashboard report" in text
        or "auto dashboard" in text
    ):
        return "build-dashboard"

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
