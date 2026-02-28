from openai import OpenAI

class LLMTool:
    """Outil LLM optimisé pour un Agent (Génération de texte)."""

    def __init__(self, model_name="gemma3:4b"):
        """
        Initialise l'outil avec un focus sur la précision des instructions.
        Modèles recommandés pour un agent : 'qwen3:8b' ou 'gemma3:4b'.
        """
        self.name = "llm_tool"
        self.model_name = model_name

        # Connexion à Ollama via l'interface compatible OpenAI
        self.client = OpenAI(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )
        print(f"Outil Agent initialisé avec le modèle : {self.model_name}")

    def interroge_llm(self, prompt: str, system_instruction: str = "Tu es un agent expert en génération de texte."):
        """
        Génère du texte en suivant les instructions de l'agent.
        """
        print(f"L'agent sollicite le modèle {self.model_name}...")

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                # On baisse la température pour que l'agent reste fiable et cohérent
                temperature=0.3,
                max_tokens=1000,
            )

            resultat = completion.choices[0].message.content
            return resultat
        except Exception as e:
            print(f"Erreur lors de la interroge_llm : {e}")
            return None

    def agent_plan_llm(self, prompt: str, system_instruction: str = "Tu es un agent pour la plannification des taches."):
        """
        Génère du texte en suivant les instructions de l'agent.
        """
        print(f"L'agent sollicite le modèle {self.model_name}...")

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                # On baisse la température pour que l'agent reste fiable et cohérent
                temperature=0.3,
                max_tokens=1000,
            )

            resultat = completion.choices[0].message.content
            return resultat

        except Exception as e:
            print(f"Erreur lors de la génération : {e}")
            return None

# --- Exemple d'intégration dans un workflow d'agent ---
if __name__ == "__main__":
    # On utilise Qwen3 8B car c'est le plus robuste pour suivre des consignes d'agent
    mon_outil = LLMTool(model_name="gemma3:4b")

    consigne = "Rédige un court article de blog sur les bienfaits de l'IA locale."
    reponse = mon_outil.interroge_llm(consigne)

    print("\n--- TEXTE GÉNÉRÉ PAR L'AGENT ---\n")
    print(reponse)
