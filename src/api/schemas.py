from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: Optional[str] = None
    file_path: Optional[str] = None
    sheet_name: Optional[str] = None
    preview: bool = False


class CommandRequest(BaseModel):
    command: Optional[str] = None
    file_path: Optional[str] = None
    sheet_name: Optional[str] = None
    preview: bool = False
    chart_type: Optional[str] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    title: Optional[str] = None
    target_column: Optional[str] = None
    group_by: Optional[str] = None
    new_column: Optional[str] = None
    left_column: Optional[str] = None
    operator: Optional[str] = None
    right_column: Optional[str] = None

    class Config:
        extra = "allow"


class WorkbookContextRequest(BaseModel):
    file_path: Optional[str] = None
    sheet_name: Optional[str] = None


class Artifact(BaseModel):
    type: str = "file"
    path: str


class CommandResponse(BaseModel):
    success: bool
    message: str
    command: Optional[str] = None
    file_path: Optional[str] = None
    sheet_name: Optional[str] = None
    output_text: str = ""
    artifacts: List[Artifact] = Field(default_factory=list)
    session: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkbookStatusResponse(BaseModel):
    success: bool
    message: str
    current_file: Optional[str] = None
    current_sheet: Optional[str] = None
    sheets: List[str] = Field(default_factory=list)
    sheet_summary: Dict[str, Dict[str, Optional[int]]] = Field(default_factory=dict)
    last_command: Optional[str] = None
    last_output_file: Optional[str] = None
    last_result_summary: Optional[str] = None
    recent_commands: List[str] = Field(default_factory=list)
    current_sheet_valid: Optional[bool] = None


class WorkbookSheetsResponse(BaseModel):
    success: bool
    file_path: Optional[str] = None
    sheets: List[str] = Field(default_factory=list)
    message: Optional[str] = None


class WorkbookContextResponse(BaseModel):
    success: bool
    current_file: Optional[str] = None
    current_sheet: Optional[str] = None
    message: str

