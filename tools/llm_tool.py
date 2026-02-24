import os

from openai import OpenAI


class LLMTool:
    # Outil pour interagir avec LLM (Kimi K2) pour obtenir des réponses à partir de questions posées.
    def __init__(self):
        """Initialise l'outil LLMTool."""
        self.name = "llm_tool"

        # Configuration des credentials
        API_KimiK2 = os.getenv("KimiK2_API_KEY")  # Pas utilisé dans la suite du code actuel

        self.client = OpenAI(
            api_key="KimiK2_API_KEY",  # Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
            base_url="https://api.moonshot.ai/v1",
        )
        print("LLM KIMI K2 initialisé avec succès.")

    def interroge_llm(self, question: str):
        """Lit les données d'une plage spécifique."""
        print(f"Interrogation du LLM avec la question : {question}")
        try:
            # Appel à l'API pour récupérer les valeurs
            completion = self.client.chat.completions.create(
                model="kimi-k2-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Kimi, an AI assistant provided by Moonshot AI. You follow strickly the user's instructions and provide helpful and accurate answers",
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.2,
            )

            # We receive a response from the Kimi large language model via the API (role=assistant)
            print("completion :", completion.choices[0].message.content)
            return completion.choices[0].message.content

        except Exception as e:
            print(f"Erreur la demande du LLM {e}")
            return []
