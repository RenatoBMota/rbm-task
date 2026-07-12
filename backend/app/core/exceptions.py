class TaskBlockedError(Exception):
    def __init__(self, blocking_titles: list[str]):
        self.blocking_titles = blocking_titles
        super().__init__(
            "Tarefa bloqueada por dependências não concluídas: " + ", ".join(blocking_titles)
        )
