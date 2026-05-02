# Data Analytics AI (Excel Command Tool)

A modular CLI-based data analytics tool that processes Excel files using structured and natural language commands.

## Features

- Clean duplicate rows
- Remove empty rows
- Summarize datasets
- Detect column types
- Natural language command support
- Multi-step natural language workflows with output handoff

## Example Usage

### CLI Commands

```bash
python -m src.main clean-duplicates data/raw/test.xlsx
python -m src.main summarize data/raw/test.xlsx
python -m src.main remove-empty-rows data/raw/test.xlsx
python -m src.main detect-columns data/raw/test.xlsx
```

### Natural Language Commands

```bash
python -m src.main "clean duplicate rows from test.xlsx"
python -m src.main "summarize test.xlsx"
python -m src.main "remove all blank rows from test.xlsx"
python -m src.main "what columns are inside test.xlsx"
```

### Multi-Step Natural Language Commands

Transform commands can feed their output into the next step:

```bash
python -m src.main "clean duplicate rows and then summarize test.xlsx"
python -m src.main "remove empty rows, clean duplicates, and summarize test.xlsx"
```

For example, cleaning `data/raw/test.xlsx` creates `outputs/test_cleaned.xlsx`, and the summarize step uses that cleaned workbook automatically.

### Session Memory

The CLI keeps a small local memory file with the latest input file, latest output file, latest command, and latest plan. It stores only paths and command metadata.

```bash
python -m src.main "clean duplicates from test.xlsx"
python -m src.main "now summarize it"
```

The second command resolves `it` to the most recent Excel output, such as `outputs/test_cleaned.xlsx`.

```bash
python -m src.main memory
python -m src.main memory-clear
```

Use `memory` to show the current session memory and `memory-clear` to reset it.

## LLM Upgrade

The natural language parser can use the OpenAI API to convert user requests into supported CLI commands.

### 1. Create `.env`

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Then replace `your_api_key_here` with your real OpenAI API key:

```env
OPENAI_API_KEY=your_api_key_here
```

Never commit `.env` or any real API key. The `.env` file is intentionally ignored by git.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run examples

```bash
python -m src.main "please clean the duplicate rows in test.xlsx"
python -m src.main "can you analyze this Excel file test.xlsx"
python -m src.main "remove all blank rows from test.xlsx"
python -m src.main "show me the structure of test.xlsx"
python -m src.main "what columns are inside test.xlsx"
```

If `OPENAI_API_KEY` exists, natural language input uses LLM mode. If it is missing, the app prints `No API key found. Using rule-based fallback.` and falls back to the existing rule-based classifier.
