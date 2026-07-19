import json
from datetime import datetime, timezone
import httpx
from app.core.config import settings
from app.core.timezone import BUSINESS_TZ

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

VALID_PRIORITIES = {"P1", "P2", "P3", "P4"}


class GeminiNotConfiguredError(Exception):
    pass


class GeminiRequestError(Exception):
    pass


def _build_prompt(text: str, project_names: list[str], now_local: datetime) -> str:
    today_str = now_local.strftime("%Y-%m-%d (%A)")
    projects_block = "\n".join(f"- {name}" for name in project_names) if project_names else "(nenhum projeto cadastrado)"
    return f"""Você é um assistente que extrai tarefas acionáveis de um texto de reunião ou anotação em português.

Data de hoje: {today_str}

Projetos existentes nesta área de trabalho:
{projects_block}

Analise o texto abaixo e extraia uma lista de tarefas acionáveis e concretas. Ignore trechos que sejam apenas contexto, decisões já tomadas sem ação pendente, ou observações gerais. Para cada tarefa, retorne um objeto com:
- title: título curto e claro da tarefa (obrigatório)
- description: detalhes adicionais relevantes mencionados no texto, ou null
- priority: "P1" (urgente/bloqueante), "P2" (alta), "P3" (média) ou "P4" (baixa) — inferida pelo tom e urgência do texto
- due_date: data no formato YYYY-MM-DD se houver menção de prazo (ex: "até sexta", "semana que vem", "amanhã"), resolvida com base na data de hoje informada acima, ou null se não houver menção de prazo
- estimated_minutes: estimativa de duração em minutos se for possível inferir do texto, ou null
- project_name: o nome EXATO de um dos projetos listados acima, apenas se a tarefa claramente pertencer a um deles, ou null caso contrário

Responda APENAS com um JSON válido, sem texto adicional, no formato:
{{"tasks": [{{"title": "...", "description": null, "priority": "P3", "due_date": null, "estimated_minutes": null, "project_name": null}}]}}

Se não houver nenhuma tarefa acionável no texto, retorne {{"tasks": []}}.

Texto:
\"\"\"
{text}
\"\"\"
"""


def extract_task_suggestions(
    text: str, project_names: list[str], now: datetime | None = None
) -> list[dict]:
    if not settings.GEMINI_API_KEY:
        raise GeminiNotConfiguredError("GEMINI_API_KEY não configurada no servidor.")

    now_local = (now or datetime.now(timezone.utc)).astimezone(BUSINESS_TZ)
    prompt = _build_prompt(text, project_names, now_local)

    url = GEMINI_ENDPOINT.format(model=settings.GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    try:
        response = httpx.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GeminiRequestError(f"Falha ao chamar a API do Gemini: {exc}") from exc

    data = response.json()
    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw_text)
        tasks = parsed.get("tasks", [])
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise GeminiRequestError(f"Resposta da IA em formato inesperado: {exc}") from exc

    if not isinstance(tasks, list):
        raise GeminiRequestError("Resposta da IA em formato inesperado: 'tasks' não é uma lista.")

    return tasks


def normalize_suggestion(item: dict) -> dict | None:
    title = item.get("title")
    if not title or not isinstance(title, str):
        return None

    priority = item.get("priority")
    if priority not in VALID_PRIORITIES:
        priority = "P4"

    estimated_minutes = item.get("estimated_minutes")
    if not isinstance(estimated_minutes, int):
        estimated_minutes = None

    due_date = item.get("due_date")
    if not isinstance(due_date, str):
        due_date = None

    description = item.get("description")
    if not isinstance(description, str):
        description = None

    project_name = item.get("project_name")
    if not isinstance(project_name, str):
        project_name = None

    return {
        "title": title.strip(),
        "description": description,
        "priority": priority,
        "due_date": due_date,
        "estimated_minutes": estimated_minutes,
        "project_name": project_name,
    }
