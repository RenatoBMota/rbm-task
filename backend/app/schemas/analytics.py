from pydantic import BaseModel


class CompletionTrendPoint(BaseModel):
    date: str
    completed: int


class StatusBreakdownItem(BaseModel):
    status: str
    count: int


class SLACompliance(BaseModel):
    total: int
    on_time: int
    breached: int
    at_risk: int
    compliance_pct: float
