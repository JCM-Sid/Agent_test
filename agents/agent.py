"""Agent principal pour les tâches autonomes."""


class Agent:
    """Agent autonome capable d'exécuter diverses tâches."""
    
    def __init__(self, web_tool=None, gsheet_tool=None):
        """Initialise l'agent avec les outils disponibles."""
        self.web_tool = web_tool
        self.gsheet_tool = gsheet_tool
        self.name = "Agent Autonome"
    
    def run(self):
        """Lance la boucle principale de l'agent."""
        print(f"{self.name} - En attente de tâches...")
        # TODO: Implémenter la logique de l'agent
    
    def execute_task(self, task: str):
        """Exécute une tâche spécifique."""
        # TODO: Implémenter l'exécution de tâches
        pass
