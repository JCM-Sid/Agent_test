"""Agent principal pour les tâches autonomes."""

import time


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
            name_ent = task.split(":")[0]
            print(f"\nTraitement de : {name_ent}...")  # Log court pour la console
            _ = self.execute_task(task)
            time.sleep(5)  # Pause entre les tâches pour éviter les surcharges

        print("\n--- Toutes les tâches ont été traitées ---")

    def execute_task(self, task: str):
        """Exécute une tâche spécifique : Recherche Web + Log GSheet."""
        if not self.web_tool:
            return "Erreur : WebTool non configuré."

        try:
            # 1. Recherche d'informations
            search_results = self.web_tool.search(task)
            print(f"Résultat : {search_results[0]}...")  # Log court pour la console
            if not search_results:
                print("Aucun résultat trouvé.")
                return "Aucun résultat trouvé."
            else:
                # 2. Préparation des données pour GSheet
                first_result = search_results[0]
                name_ent = task.split(":")[0]
                act_ent = task.split(":")[1] if len(task.split(":")) > 1 else "N/A"
                link_ent = first_result["link"]
                print(f"Infos {name_ent} {link_ent} {act_ent} \n")  # Log court pour la console
                if self.gsheet_tool:
                    find_row = self.gsheet_tool.find_row(name_ent)
                    self.gsheet_tool.update_sheet(row_nb=find_row, values=[link_ent, name_ent, "", "", act_ent, "Fr", "", "TechInnov", ""])
                    if find_row:
                        print(f"Infos mises à jour pour {name_ent} dans GSheet.")
                    else:
                        print(f"Infos ajoutées pour {name_ent} dans GSheet.")
                else:
                    return "Succès (Web uniquement)"

        except Exception as e:
            error_msg = f"Erreur lors de l'exécution : {str(e)}"
            print(error_msg)
            return error_msg
