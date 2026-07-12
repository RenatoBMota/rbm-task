from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.access import require_project_member, require_workspace_member
from app.crud.analytics import scoped_tasks_query
from app.crud.project import get_project
from app.crud.report import build_executive_report, build_recap
from app.models.user import User
from app.schemas.report import ExecutiveReportOut, RecapOut

router = APIRouter(prefix="/reports", tags=["reports"])

STATUS_LABELS = {
    "todo": "A Fazer",
    "in_progress": "Em Progresso",
    "in_review": "Em Revisão",
    "done": "Concluído",
    "cancelled": "Cancelado",
}

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


def _get_project_or_404(db: Session, project_id: int, current_user: User):
    require_project_member(db, project_id, current_user.id)
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado")
    return project


@router.get("/projects/{project_id}/executive", response_model=ExecutiveReportOut)
def executive_report(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id, current_user)
    return build_executive_report(db, project)


@router.get("/projects/{project_id}/executive.pdf")
def executive_report_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id, current_user)
    report = build_executive_report(db, project)
    styles = getSampleStyleSheet()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = [
        Paragraph(f"Relatório Executivo — {report['project_name']}", styles["Title"]),
        Paragraph(
            f"Período: {report['start_date'].strftime('%d/%m/%Y')} a {report['end_date'].strftime('%d/%m/%Y')} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; Gerado em {report['generated_at'].strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        ),
        Spacer(1, 16),
    ]

    kpi_data = [
        ["Progresso", "Prazo esperado", "Custo total", "Risco", "Atrasadas", "Caminho crítico"],
        [
            f"{report['progress_percent']}%",
            f"{report['expected_progress_percent']}%",
            f"R$ {report['total_cost']:.2f}",
            f"{report['risk_level'].upper()} ({report['risk_score']})",
            str(report["overdue_tasks"]),
            f"{report['critical_task_count']} tarefas",
        ],
    ]
    kpi_table = Table(kpi_data, repeatRows=1)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements += [kpi_table, Spacer(1, 20)]

    elements.append(Paragraph("Tarefas por status", styles["Heading2"]))
    status_data = [["Status", "Quantidade"]] + [
        [STATUS_LABELS.get(row["status"], row["status"]), str(row["count"])]
        for row in report["status_breakdown"]
    ]
    status_table = Table(status_data, repeatRows=1)
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements += [status_table, Spacer(1, 20)]

    if report["team"]:
        elements.append(Paragraph("Carga da equipe", styles["Heading2"]))
        team_data = [["Membro", "Ativas", "Concluídas"]] + [
            [m["full_name"], str(m["active_task_count"]), str(m["completed_task_count"])]
            for m in report["team"]
        ]
        team_table = Table(team_data, repeatRows=1)
        team_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elements.append(team_table)

    doc.build(elements)
    buffer.seek(0)
    filename = f"relatorio-executivo-{report['project_name']}.pdf".replace(" ", "-")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/workspaces/{workspace_id}/recap", response_model=RecapOut)
def workspace_recap(
    workspace_id: int,
    period: str = "weekly",
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if period == "custom":
        if not start or not end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe 'start' e 'end' para um período personalizado.",
            )
        if end < start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A data final não pode ser anterior à data inicial.",
            )
    elif period not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Período inválido")
    require_workspace_member(db, workspace_id, current_user.id)
    return build_recap(db, workspace_id, period, start, end)
