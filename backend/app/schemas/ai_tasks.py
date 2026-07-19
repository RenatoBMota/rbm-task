from pydantic import BaseModel, Field


class ExtractTasksRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    workspace_id: int


class TaskSuggestionOut(BaseModel):
    title: str
    description: str | None
    priority: str
    due_date: str | None
    estimated_minutes: int | None
    suggested_project_id: int | None
    suggested_project_name: str | None
