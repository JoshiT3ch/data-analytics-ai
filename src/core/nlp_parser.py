def parse_input(user_input):
    user_input = user_input.lower()

    if "duplicate" in user_input:
        command = "clean-duplicates"
    elif "empty" in user_input:
        command = "remove-empty-rows"
    elif "summarize" in user_input or "summary" in user_input:
        command = "summarize"
    elif "column" in user_input:
        command = "detect-columns"
    else:
        command = None

    # simple file detection
    words = user_input.split()
    file_path = None
    for word in words:
        if word.endswith(".xlsx"):
            file_path = f"data/raw/{word}"

    return command, file_path