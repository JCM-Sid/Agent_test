"""
Agent Autonome - Point d'entrée principal
"""
import pandas as pd
from agents import Agent
from tools import WebTool, GSheetTool


def main():
    """Point d'entrée de l'application agent autonome."""
    # Initialisation des outils
    web_tool = WebTool()
    gsheet_tool = GSheetTool()
    
    # Création de l'agent
    agent = Agent(web_tool=web_tool, gsheet_tool=gsheet_tool)

    file_input = pd.read_csv(r"G:\Mon Drive\DDCM\Propals\techinnovparticipants.csv", sep='§', encoding='utf-8')
    print(
        f"File read successfully. Number of rows: {len(file_input)}. Columns: {file_input.columns.tolist()}"   
    )
    #print(f"First 5 rows:\n{file_input.head()}")
    unique_entreprise = file_input['titre'].unique()
    uniq_entreprise_et_description = [] 
    for entreprise in unique_entreprise:
        description = file_input[file_input['titre'] == entreprise]['description'].iloc[0]
        uniq_entreprise_et_description.append((f"{entreprise} : {description}"))
    print(f"Unique entreprises: {len(uniq_entreprise_et_description )}")
    print(f"Unique entreprises and descriptions: {uniq_entreprise_et_description[:5]}")

    # Boucle principale de l'agent
    agent.run(uniq_entreprise_et_description)


if __name__ == "__main__":
    main()
