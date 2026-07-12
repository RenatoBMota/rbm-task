from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.analytics import scoped_tasks_query
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])

HEADERS = ["ID", "Título", "Status", "Prioridade", "Prazo", "Concluída"]


def _rows(db: Session, current_user: User, project_id: int | None) -> list[list[str]]:
    tasks = scoped_tasks_query(db, current_user, project_id).all()
    return [
        [
            str(t.id),
            t.title,
            t.status.value,
            t.priority.value,
            t.due_date.strftime("%d/%m/%Y %H:%M") if t.due_date else "-",
            "Sim" if t.is_completed else "Não",
        ]
        for t in tasks
    ]


@router.get("/tasks.xlsx")
def export_tasks_xlsx(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wb = Workbook()
    ws = wb.active
    ws.title = "Tarefas"
    ws.append(HEADERS)
    for row in _rows(db, current_user, project_id):
        ws.append(row)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tarefas.xlsx"},
    )


@router.get("/tasks.pdf")
def export_tasks_pdf(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    data = [HEADERS] + _rows(db, current_user, project_id)
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    doc.build([table])
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tarefas.pdf"},
    )
