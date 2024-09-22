from functools import lru_cache
import pickle
import gspread
from unidecode import unidecode
import pandas as pd
from src.constants import *
from src.utils import *

def get_uploaded_pdfs(name, drive_service, folder_id=None):
    """
    Retrieve the list of PDF file names from Google Drive that contain the given name.
    
    Parameters:
    name (str): The name to search for in the file names.
    drive_service (Resource): The Google Drive service object.
    folder_id (str): Optional, the ID of the folder to search in. If None, searches all files.

    Returns:
    List[str]: A list of matching PDF file names.
    """
    escaped_name = name.replace("'", "\\'")
    query = f"mimeType = 'application/pdf' and trashed = false and name contains '{escaped_name}'"
    
    if folder_id:
        query += f" and '{folder_id}' in parents"
    
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    # Return a list of file names
    return [file['name'] for file in files]

@lru_cache(maxsize=None)
def get_undertaker_data():
    with open(TOKEN_FILE, 'rb') as token:
        credentials = pickle.load(token)
    gc = gspread.authorize(credentials)
    undertaker_sheet = gc.open_by_key(UNDERTAKER_SHEET_KEY)
    undertaker_worksheet = undertaker_sheet.get_worksheet_by_id(0)
    
    sheet_data = undertaker_worksheet.get_values()
    header = sheet_data[0]
    rows = sheet_data[1:]
    result = []
    df = pd.DataFrame(rows, columns=header)
    
    for _, row in df.iterrows():
        address = unidecode(row["Adresse"]).replace(" ", "").replace("-", "").replace(",", "").lower()
        result.append((address, row["Phone"], str(row["Email"]).strip()))
    
    return result