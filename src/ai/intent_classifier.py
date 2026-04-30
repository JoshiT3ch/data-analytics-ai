def classify_intent(user_input):
    text = user_input.lower()

    if "duplicate" in text or "duplicates" in text or "duplicated" in text:
        return "clean-duplicates"

    if "empty" in text or "blank" in text or "null" in text:
        return "remove-empty-rows"

    if "summary" in text or "summarize" in text or "describe" in text:
        return "summarize"

    if "column" in text or "columns" in text or "data type" in text or "dtype" in text:
        return "detect-columns"

    return None