from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

class GSheetTool:
    """Outil pour interagir avec Google Sheets."""
    
    def __init__(self):
        """Initialise l'outil GSheet."""
        self.name = "GSheetTool"
        self.spreadsheet_id = "1_oT6ZixeVCZvEdEea9BzRngmInljuoyOXlsOnoRonlc"

        nextcloud_dir = os.getenv("NEXTCLOUD")
        credentials_path = os.path.join(nextcloud_dir, "ConfigPerso", "client_secret_google_sheet.json")
        # Configuration des credentials
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        self.service = build('sheets', 'v4', credentials=creds)


    def read_sheet(self, spreadsheet_id: str, range_name: str):
        """Lit les données d'une feuille."""
        # TODO: Implémenter avec google-api-python-client   
        # Placeholder - à remplacer par l'implémentation réelle
        return gsheet_tool.read_range(spreadsheet_id, range_name)
    
    def write_sheet(self, spreadsheet_id: str, range_name: str, values: list):
        """Écrit des données dans une feuille."""
        # TODO: Implémenter avec google-api-python-client
        # Placeholder - à remplacer par l'implémentation réelle
        return gsheet_tool.write_range(spreadsheet_id, range_name, values)
    
    def find_row(self, key_value: str):
        """Trouve une ligne basée sur une valeur clé."""
        data = self.read_sheet(self.spreadsheet_id, "B:B")
        for index, row in enumerate(data, start=1):
            if row and row[0] == key_value:
                return index  # Retourne l'index de la ligne (numéro de ligne)
        return None  # Si non trouvé, retourne None
        
    def update_sheet(self, row_nb: int = None, values: list = None):
        """Écrit des données dans une feuille."""
        if row_nb is not None:
            #self.write_sheet(self.spreadsheet_id, f"A{row_nb}", [values])
            pass
        else:
            all_rows = self.read_sheet(self.spreadsheet_id, 'A:A')
            next_row = len(all_rows) + 1
            self.write_sheet(self.spreadsheet_id, f"A{next_row}", [values])