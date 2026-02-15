"""Agent principal pour les tâches autonomes."""
import datetime

class Agent:
    """Agent autonome capable d'exécuter diverses tâches."""
    
    def __init__(self, web_tool=None, gsheet_tool=None):
        """Initialise l'agent avec les outils disponibles."""
        self.web_tool = web_tool
        self.gsheet_tool = gsheet_tool
        self.name = "Agent Autonome"
    
    def run(self, task_list: list):
        """Lance la boucle principale de l'agent sur une liste de tâches."""
        print(f"--- Démarrage de {self.name} ---")
        for task in task_list:
            print(f"\nTraitement de : {task}")
            result = self.execute_task(task)
            print(f"Résultat : {result[:100]}...") # Log court pour la console
        print("\n--- Toutes les tâches ont été traitées ---")

    def execute_task(self, task: str):
        """Exécute une tâche spécifique : Recherche Web + Log GSheet."""
        if not self.web_tool:
            return "Erreur : WebTool non configuré."
        
        try:
            # 1. Recherche d'informations
            search_results = self.web_tool.search(task)
            
            # 2. Préparation des données pour GSheet
            # Format : [Date, Tâche, Résultat (tronqué si trop long)]
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_data = [timestamp, task, str(search_results)[:500]] 
            print(f"res: {search_results}...") # Log court pour la console
            # 3. Enregistrement dans Google Sheets
            if self.gsheet_tool:
                self.gsheet_tool.write_sheet(log_data)
                return f"Succès : Recherche effectuée et loggée dans GSheet."
            else:
                return f"Succès (Web uniquement) : {search_results[:50]}"
                
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution : {str(e)}"
            print(error_msg)
            return error_msg