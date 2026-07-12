import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.automation import AutomationRule, AutomationLog, TriggerEvent
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.notification import NotificationType
from app.core.email import send_email

logger = logging.getLogger("rbm.automation")


def _conditions_match(task: Task, conditions: dict) -> bool:
    for key, value in conditions.items():
        if key == "priority" and task.priority.value != value:
            return False
        if key == "status" and task.status.value != value:
            return False
        if key == "project_id" and task.project_id != value:
            return False
        if key == "assignee_id" and task.assignee_id != value:
            return False
    return True


def _run_action(db: Session, action: dict, task: Task, rule: AutomationRule) -> str:
    from app.crud.notification import create_notification

    action_type = action.get("type")

    if action_type == "change_status":
        task.status = TaskStatus(action["status"])
        db.commit()
        return f"status alterado para {action['status']}"

    if action_type == "change_priority":
        task.priority = TaskPriority(action["priority"])
        db.commit()
        return f"prioridade alterada para {action['priority']}"

    if action_type == "assign_user":
        task.assignee_id = action["user_id"]
        db.commit()
        return f"reatribuída ao usuário {action['user_id']}"

    if action_type == "notify_user":
        user_id = action.get("user_id") or task.assignee_id
        if not user_id:
            return "sem usuário para notificar"
        create_notification(
            db,
            user_id=user_id,
            type=NotificationType.NEW_COMMENT,
            message=action.get("message", f"Automação disparada na tarefa \"{task.title}\""),
            task_id=task.id,
        )
        return f"notificação enviada ao usuário {user_id}"

    if action_type == "add_comment":
        from app.models.comment import Comment

        db.add(Comment(
            content=action.get("content", ""),
            task_id=task.id,
            author_id=task.assignee_id or rule.created_by_id,
        ))
        db.commit()
        return "comentário adicionado"

    if action_type == "send_email":
        to = action.get("to")
        if not to:
            return "sem destinatário de e-mail"
        sent = send_email(
            to=to,
            subject=action.get("subject", f"RBM TASK: {task.title}"),
            body=action.get("body", f"A tarefa \"{task.title}\" disparou uma automação."),
        )
        return "e-mail enviado" if sent else "SMTP não configurado, e-mail ignorado"

    if action_type == "webhook":
        import httpx

        url = action.get("url")
        if not url:
            return "sem URL de webhook"
        try:
            httpx.post(
                url,
                json={"task_id": task.id, "title": task.title, "status": task.status.value},
                timeout=5,
            )
            return f"webhook chamado: {url}"
        except httpx.HTTPError as exc:
            return f"falha no webhook: {exc}"

    if action_type == "whatsapp":
        return "integração com WhatsApp ainda não configurada"

    return f"tipo de ação desconhecido: {action_type}"


def evaluate_and_run(db: Session, event: TriggerEvent, task: Task) -> None:
    rules = (
        db.query(AutomationRule)
        .filter(AutomationRule.trigger_event == event, AutomationRule.is_active == True)
        .all()
    )
    for rule in rules:
        if rule.project_id and rule.project_id != task.project_id:
            continue
        if not _conditions_match(task, rule.conditions or {}):
            continue

        for action in rule.actions or []:
            try:
                detail = _run_action(db, action, task, rule)
                db.add(AutomationLog(rule_id=rule.id, task_id=task.id, success=True, detail=detail))
            except Exception as exc:
                logger.exception("Falha ao executar ação da automação %s", rule.id)
                db.add(AutomationLog(rule_id=rule.id, task_id=task.id, success=False, detail=str(exc)))
        db.commit()
