"""Agent principal pour les tâches autonomes."""
import time
import re

class Agent:
    """Agent autonome capable d'exécuter diverses tâches."""

    def __init__(self, web_tool=None, gsheet_tool=None, llm_tool=None):
        """Initialise l'agent avec les outils disponibles."""
        self.web_tool = web_tool
        self.gsheet_tool = gsheet_tool
        self.llm_tool = llm_tool
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
            name_ent = task.split(":")[0]
            act_ent = task.split(":")[1] if len(task.split(":")) > 1 else "N/A"

            # 1. Recherche d'informations
            search_results = self.web_tool.search(name_ent)
            print(f"Résultat : {search_results[0]}...")  # Log court pour la console
            if not search_results:
                print("Aucun résultat trouvé.")
                return "Aucun résultat trouvé."
            else:
                # 2. Préparation des données pour GSheet
                first_result = search_results[0]

                link_ent = first_result["link"]
                print(f"Infos {name_ent} {link_ent} \n")  # Log court pour la console
                req_llm = f"Donne une description concise de {name_ent} , \
                    un nom de contact et un email de contact ,  \
                    Reponds avec un json \
                        'description': ajoute la description ici ,\
                        'contact_name': ajoute le nom du contact ici, \
                        'contact_email': ajoute l'email du contact ici "

                llm_response = self.llm_tool.interroge_llm(req_llm)
                print(f"LLM Response: {llm_response}")  # Log de la réponse du LLM

                if self.gsheet_tool:
                    find_row = self.gsheet_tool.find_row(name_ent)
                    # self.gsheet_tool.update_sheet(row_nb=find_row, values=[link_ent, name_ent, "", "", act_ent, "Fr", "", "TechInnov", ""])
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


class AgenticAI:
    def __init__(self, llm_tool, tools):
        self.llm = llm_tool
        self.tools = tools  # Dictionnaire de fonctions {name: function}
        self.max_steps = 5

    def run(self, goal):
        print(f"🚀 Objectif : {goal}")

        # Le prompt système qui définit les règles du jeu (ReAct)
        system_instruction = f"""
        Tu es un agent autonome. Tu as accès aux outils suivants :
        {self._render_tools_desc()}

        Pour résoudre la tâche, tu dois suivre ce format :
        Pensée : Ce que tu comptes faire.
        Action : Le nom de l'outil à utiliser (parmi {list(self.tools.keys())}).
        Entrée : L'argument pour l'outil.
        (Attends l'Observation)
        
        Quand tu as terminé, réponds par :
        Réponse Finale : Le résultat final.
        """

        history = [{"role": "system", "content": system_instruction}, {"role": "user", "content": goal}]

        for i in range(self.max_steps):
            # 1. RÉFLEXION (Reasoning)
            print(f"\n--- 🧠 Pensée de l'Agent (Etape {i + 1}) ---")
            #print(f"Historique : {[h['content'] for h in history]}")  # Log de l'historique
            print(f"Prompt envoyé au LLM : {self._format_history(history)}")  # Log du prompt
            response = self.llm.agent_plan_llm(self._format_history(history))
            print(f"\n--- 🧠 Pensée de l'Agent (Etape {i + 1}) ---")
            print(response)

            # 2. EXTRACTION DE L'ACTION
            action = self._extract_action(response)

            if not action:  # Si l'IA donne la réponse finale
                if "Réponse Finale" in response:
                    return response
                break

            # 3. EXÉCUTION DE L'OUTIL (Acting)
            tool_name, tool_input = action
            print(f"🛠️ Utilisation de {tool_name} avec : {tool_input}")

            observation = self.tools[tool_name](tool_input)
            print(f"👁️ Observation : {str(observation)[:100]}...")

            # 4. MISE À JOUR DE LA MÉMOIRE (Observing)
            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": f"Observation : {observation}"})

    def _render_tools_desc(self):
        return "\n".join([f"- {name}: {func.__doc__}" for name, func in self.tools.items()])

    def _extract_action(self, text):
        action_match = re.search(r"Action\s*:\s*(.*)", text)
        input_match = re.search(r"Entrée\s*:\s*(.*)", text)
        if action_match and input_match:
            return action_match.group(1).strip(), input_match.group(1).strip()
        return None

    def _format_history(self, history):
        # Transforme l'historique en string pour les modèles non-chat ou simplifie
        return "\n".join([f"{m['role']}: {m['content']}" for m in history])
