# Data Analytics AI (Excel Command Tool)

A modular CLI-based data analytics tool that processes Excel files using structured and natural language commands.

## Features

- Clean duplicate rows
- Remove empty rows
- Summarize datasets
- Detect column types
- Natural language command support

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
