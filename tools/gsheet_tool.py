"""Outil pour les interactions Google Sheets."""


class GSheetTool:
    """Outil pour interagir avec Google Sheets."""
    
    def __init__(self):
        """Initialise l'outil GSheet."""
        self.name = "GSheetTool"
    
    def read_sheet(self, spreadsheet_id: str, range: str):
        """Lit les données d'une feuille."""
        # TODO: Implémenter avec google-api-python-client
        pass
    
    def write_sheet(self, spreadsheet_id: str, range: str, values: list):
        """Écrit des données dans une feuille."""
        # TODO: Implémenter l'écriture
        pass
