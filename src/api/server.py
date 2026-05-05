from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.command_service import (
    execute_chat_request,
    execute_structured_command,
    get_workbook_status,
    list_workbook_sheets,
    update_workbook_context,
)
from src.api.schemas import (
    ChatRequest,
    CommandRequest,
    CommandResponse,
    WorkbookContextRequest,
    WorkbookContextResponse,
    WorkbookSheetsResponse,
    WorkbookStatusResponse,
)


LOCAL_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
]


app = FastAPI(
    title="Excel Data Analyst AI API",
    description="Local API bridge for the Excel-focused Data Analyst assistant.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_DEV_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, _exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Invalid request payload.",
            "output_text": "",
            "artifacts": [],
            "session": {},
            "error": "Validation error",
        },
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "excel-data-analyst-ai",
    }


@app.post("/chat", response_model=CommandResponse)
def chat(request: ChatRequest):
    return execute_chat_request(request)


@app.post("/command", response_model=CommandResponse)
def command(request: CommandRequest):
    return execute_structured_command(request)


@app.get("/workbook/status", response_model=WorkbookStatusResponse)
def workbook_status():
    return get_workbook_status()


@app.get("/workbook/sheets", response_model=WorkbookSheetsResponse)
def workbook_sheets(file_path: str = None):
    return list_workbook_sheets(file_path)


@app.post("/workbook/context", response_model=WorkbookContextResponse)
def workbook_context(request: WorkbookContextRequest):
    return update_workbook_context(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
