import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class GSheetTool:
    """Outil pour interagir avec Google Sheets."""

    def __init__(self):
        """Initialise l'outil GSheet."""
        self.name = "gsheet_tool"
        # Configuration des credentials
        self.spreadsheet_id = "1_oT6ZixeVCZvEdEea9BzRngmInljuoyOXlsOnoRonlc"

        nextcloud_dir = os.getenv("NEXTCLOUD")
        credentials_path = os.path.join(nextcloud_dir, "ConfigPerso", "credentials_gsheet.json")

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        self.service = build("sheets", "v4", credentials=creds)

        # Authentification
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)

        # Construction du service
        service = build("sheets", "v4", credentials=creds)

        # Test : Lire le titre d'une feuille (remplace par ton ID de feuille)
        self.sheet = service.spreadsheets()
        result = self.sheet.get(spreadsheetId=self.spreadsheet_id).execute()
        print(f"Connecté avec succès à : {result.get('properties').get('title')}")

    def read_sheet(self, range_name: str):
        """Lit les données d'une plage spécifique."""
        try:
            # Appel à l'API pour récupérer les valeurs
            result = self.sheet.values().get(spreadsheetId=self.spreadsheet_id, range=range_name).execute()

            # 'values' est une liste de listes (chaque sous-liste est une ligne)
            return result.get("values", [])
        except Exception as e:
            print(f"Erreur lors de la lecture : {e}")
            return []

    def find_row(self, key_value: str):
        """Trouve une ligne basée sur une valeur clé dans la colonne B."""
        # On spécifie la colonne B de la première feuille (ou précise le nom : "Feuille1!B:B")
        data = self.read_sheet("B:B")

        for index, row in enumerate(data, start=1):
            # row est une liste. Si la cellule en B est remplie, row[0] existe.
            if row and len(row) > 0:
                if str(row[0]).strip() == str(key_value).strip():
                    return index  # Retourne le numéro de ligne Google Sheets (1-based)

        return None  # Si non trouvé

    def write_sheet(self, range_name: str, values: list):
        """Écrit une liste de listes dans la plage spécifiée."""
        try:
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .update(spreadsheetId=self.spreadsheet_id, range=range_name, valueInputOption="USER_ENTERED", body=body)
                .execute()
            )
            return result
        except Exception as e:
            print(f"Erreur lors de l'écriture : {e}")
            return None

    def update_sheet(self, row_nb: int = None, values: list = None):
        """Écrit des données dans une feuille : soit à une ligne précise, soit à la fin."""
        if values is None:
            return

        # S'assurer que 'values' est une liste de listes [[col1, col2, ...]]
        if not isinstance(values[0], list):
            values = [values]

        if row_nb is not None:
            # Mise à jour d'une ligne spécifique (ex: "A5")
            range_to_write = f"A{row_nb}"
            self.write_sheet(range_to_write, values)
        else:
            # Ajout à la suite (Append)
            # Note : On lit A:A pour trouver la dernière ligne
            all_rows = self.read_sheet("A:A")
            next_row = len(all_rows) + 1
            self.write_sheet(f"A{next_row}", values)
