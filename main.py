"""
Agent Autonome - Point d'entrée principal
"""

from agents import Agent
from tools import WebTool, GSheetTool


def main():
    """Point d'entrée de l'application agent autonome."""
    # Initialisation des outils
    web_tool = WebTool()
    gsheet_tool = GSheetTool()
    
    # Création de l'agent
    agent = Agent(web_tool=web_tool, gsheet_tool=gsheet_tool)
    
    # Boucle principale de l'agent
    agent.run()


if __name__ == "__main__":
    main()
