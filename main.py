"""
Agent Autonome - Point d'entrée principal
"""

import pandas as pd
#from Agent_test.agents import agent
#from Agent_test.tools import llm_tool
from agents import Agent, AgenticAI
from tools import GSheetTool, LLMTool, WebTool

def main_agent_simple():
    """Point d'entrée de l'application agent autonome."""
    # Initialisation des outils
    web_tool = WebTool()
    gsheet_tool = GSheetTool()
    llm_tool = LLMTool(model_name="gemma3:4b")

    # Création de l'agent
    agent = Agent(web_tool=web_tool, gsheet_tool=gsheet_tool, llm_tool=llm_tool)

    file_input = pd.read_csv(r"G:\Mon Drive\DDCM\Propals\tech_participants.csv", sep="§", encoding="utf-8")
    print(f"File read successfully. Number of rows: {len(file_input)}. Columns: {file_input.columns.tolist()}")
    # print(f"First 5 rows:\n{file_input.head()}")
    unique_entreprise = file_input["titre"].unique()
    uniq_entreprise_et_description = []
    for entreprise in unique_entreprise:
        description = file_input[file_input["titre"] == entreprise]["description"].iloc[0]
        uniq_entreprise_et_description.append((f"{entreprise} : {description}"))
    print(f"Unique entreprises: {len(uniq_entreprise_et_description)}")
    print(f"Unique entreprises and descriptions: {uniq_entreprise_et_description[:5]}")

    # Boucle principale de l'agent
    agent.run(uniq_entreprise_et_description)


def  main_agent_advanced():
    """Point d'entrée de l'application agent autonome avec une approche plus avancée."""
    # Initialisation des outils
    web_tool = WebTool()
    gsheet_tool = GSheetTool()
    llm_tool = LLMTool(model_name="gemma3:4b")

    # 2. Lancement de l'agent
    tools_map = {
        "recherche": web_tool.search, 
        "fetch": web_tool.fetch,         
        "read_gsheet": gsheet_tool.read_sheet, 
        "find_row": gsheet_tool.find_row, 
        "write_gsheet": gsheet_tool.write_sheet,  
    }

    # Création de l'agent
    agent = AgenticAI(llm_tool=llm_tool, tools=tools_map)

    # Initialisaiton des taches à traiter
    file_input = pd.read_csv(r"G:\Mon Drive\DDCM\Propals\tech_participants.csv", sep="§", encoding="utf-8")
    print(f"File read successfully. Number of rows: {len(file_input)}. Columns: {file_input.columns.tolist()}")
    
    unique_entreprise = file_input["titre"].unique()
    uniq_entreprise_et_description = []
    for entreprise in unique_entreprise:
        description = file_input[file_input["titre"] == entreprise]["description"].iloc[0]
        uniq_entreprise_et_description.append((f"{entreprise} : {description}"))
    print(f"Unique entreprises: {len(uniq_entreprise_et_description)}")
    print(f"Unique entreprises and descriptions: {uniq_entreprise_et_description[:5]}")


    # Boucle principale de l'agent
    #agent.run(uniq_entreprise_et_description)
    agent.run(f"Trouve les infos sur TechCorp et enregistre-les dans le sheet.")


if __name__ == "__main__":
    #main_agent_simple()
    main_agent_advanced()
