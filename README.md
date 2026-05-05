# Data Analytics AI (Excel Command Tool)

A modular CLI-based data analytics tool that processes Excel files using structured and natural language commands.

## Features

- Clean duplicate rows
- Remove empty rows
- Summarize datasets
- Detect column types
- Natural language command support
- Multi-step natural language workflows with output handoff
- Session memory with command history
- Backups before transform commands
- Preview mode for duplicate cleaning
- Undo for the latest backed-up file-changing action
- Chart generation for bar, line, pie, and histogram visualizations
- Smart insights, dashboards, formula columns, and workbook sheet awareness
- Local API bridge for a future Excel side chatbox

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
python -m src.main "create a bar chart of sales by category from data/raw/sales.xlsx"
python -m src.main "visualize revenue trend by month from data/raw/sales.xlsx"
python -m src.main "make a pie chart of product category distribution from data/raw/sales.xlsx"
python -m src.main "create a histogram of age from data/raw/test.xlsx"
```

Charts are saved under `outputs/charts/`.

### Workbook Context

```bash
python -m src.main "list sheets in data/raw/company_report.xlsx"
python -m src.main "use the Sales sheet from data/raw/company_report.xlsx"
python -m src.main "workbook status"
python -m src.main "summarize the Sales sheet from data/raw/company_report.xlsx"
```

Workbook context is stored locally in session memory so later commands can use the current workbook and sheet.

## Local API Bridge

The local API bridge lets a future Excel Add-in chatbox call the same parser, executor, workbook manager, and session memory used by the CLI. It is local-development only and does not add databases, cloud deployment, or a web dashboard.

Start the server:

```bash
python -m src.api.server
```

Alternative development command:

```bash
uvicorn src.api.server:app --reload --host 127.0.0.1 --port 8000
```

The API runs at `http://127.0.0.1:8000`.

Available endpoints:

- `GET /health`
- `POST /chat`
- `POST /command`
- `GET /workbook/status`
- `GET /workbook/sheets?file_path=data/raw/company_report.xlsx`
- `POST /workbook/context`

PowerShell examples:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/chat" -ContentType "application/json" -Body '{"message":"summarize the Sales sheet","file_path":"data/raw/company_report.xlsx","sheet_name":"Sales"}'

Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/workbook/status"
```

Structured command example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/command" -ContentType "application/json" -Body '{"command":"create-chart","file_path":"data/raw/sales.xlsx","chart_type":"bar","x_column":"Category","y_column":"Sales"}'
```

Set workbook context:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/workbook/context" -ContentType "application/json" -Body '{"file_path":"data/raw/company_report.xlsx","sheet_name":"Sales"}'
```

### Preview Mode

Preview duplicate cleaning without writing an output file:

```bash
python -m src.main "clean duplicate rows from test.xlsx" --preview
python -m src.main clean-duplicates data/raw/test.xlsx --preview
```

Commands that do not support preview yet return a friendly message instead of making changes.

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

### Undo

Transform commands create a backup under `backups/` before writing a changed Excel output. Restore the latest backed-up action into a new file under `outputs/`:

```bash
python -m src.main undo
python -m src.main "undo last action"
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
