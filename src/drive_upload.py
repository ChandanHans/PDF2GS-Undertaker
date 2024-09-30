# drive_upload.py

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
import requests

from .utils import execute_with_retry
from .constants import CREDS_JSON, TOKEN_FILE

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_user_profile(creds):
    """Retrieve the user's profile information including their name."""
    profile_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(profile_info_url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        user_name = user_info.get("name", "Unknown")
        return user_name
    else:
        return "Unknown"


def authenticate_google_drive():
    """Authenticate and return the Google Drive service instance."""
    creds = None

    # Load token from file if it exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # Check if the credentials are valid
    if creds and creds.valid:
        # Get the current user email from the creds
        current_user = get_user_profile(creds)
        print(f"Current logged-in user: {current_user}")

        # Ask the user if they want to use the current account or log in with a different one
        choice = (
            input("Do you want to use the current account? (y/n): ").strip().lower()
        )

        if choice != "n":
            return creds  # Return the current credentials if the user chooses "current"

    # Run OAuth flow to get new credentials
    flow = InstalledAppFlow.from_client_config(CREDS_JSON, SCOPES)
    creds = flow.run_local_server()

    # Save the new credentials to the token file
    with open(TOKEN_FILE, "wb") as token:
        pickle.dump(creds, token)
    
    return creds


def upload_to_drive(service, file_path, folder_id):
    """Upload a file to Google Drive."""
    file_metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields="id")
    uploaded_file = execute_with_retry(request)
    file_id = uploaded_file.get("id")
    return file_id


def delete_file_from_drive(service, file_id):
    """Delete a file from Google Drive by its file ID."""
    request = service.files().delete(fileId=file_id)
    execute_with_retry(request)
    print(f"Deleted file with ID {file_id} from Google Drive")


def get_sheet_id_by_name(sheets_service, spreadsheet_id, sheet_name):
    """
    Retrieve the sheetId of a specific sheet by its name.

    :param sheets_service: The Google Sheets API service object.
    :param spreadsheet_id: The ID of the spreadsheet.
    :param sheet_name: The name of the sheet (e.g., "Sheet1").
    :return: The sheetId as an integer.
    """
    request = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id)
    spreadsheet = execute_with_retry(request)
    for sheet in spreadsheet.get("sheets", []):
        if sheet["properties"]["title"] == sheet_name:
            return sheet["properties"]["sheetId"]
    return None  # Return None if the sheet with the given name is not found


def apply_sheet_customizations(sheets_service, spreadsheet_id, validation_column = 6):
    """
    Apply dropdown, conditional formatting, and cell color verification to a Google Sheet.

    :param sheets_service: The Google Sheets API service object.
    :param spreadsheet_id: The ID of the spreadsheet where the Google Sheet is located.
    """

    # Fetch sheet data to determine number of rows
    sheet_id = get_sheet_id_by_name(sheets_service, spreadsheet_id, "Sheet1")
    if sheet_id is None:
        print("Sheet not found!")
        return

    sheet_data = get_sheet_data(sheets_service, spreadsheet_id)

    # Get the number of rows (excluding header) and columns
    rows = len(sheet_data) - 1  # excluding the header

    # Apply dropdown (data validation) to column F (zero-based, so col 5 means column F)
    color_options = ["à envoyer", "draft", "envoyé", "pas trouvé"]
    apply_data_validation(
        sheets_service, spreadsheet_id, sheet_id, validation_column, rows, color_options
    )

    # Apply conditional formatting to column F (zero-based, so col 5 means column F)
    color_codes = ["#ff8e8e", "#ffeeb0", "#b2ffaf", "#daeef3"]
    apply_conditional_formatting(
        sheets_service, spreadsheet_id, sheet_id, validation_column, rows, color_options, color_codes
    )

    # Apply cell verification and color to columns A and C, skip column D
    apply_cell_color_verification(sheets_service, spreadsheet_id, sheet_id, rows)


def get_sheet_data(sheets_service, spreadsheet_id):
    """
    Get all the data from a specific Google Sheet.

    :param sheets_service: The Google Sheets API service object.
    :param spreadsheet_id: The ID of the spreadsheet where the sheet is located.
    :param sheet_id: The ID of the sheet to fetch data from.
    :return: A list of rows containing cell data.
    """
    request = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"Sheet1!A:Z")
    result = execute_with_retry(request)
    return result.get("values", [])


def apply_data_validation(sheets_service, spreadsheet_id, sheet_id, col, rows, options):
    requests = []
    for row in range(2, rows + 2):  # rows are 1-based, skip the header (row 1)
        requests.append(
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,  # Use the integer sheet_id here
                        "startRowIndex": row - 1,
                        "endRowIndex": row,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1,
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [
                                {"userEnteredValue": option} for option in options
                            ],
                        },
                        "showCustomUi": True,
                    },
                }
            }
        )

    body = {"requests": requests}
    request = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    )
    execute_with_retry(request)


def apply_conditional_formatting(
    sheets_service, spreadsheet_id, sheet_id, col, rows, options, colors
):
    requests = []
    for i, option in enumerate(options):
        color = colors[i]
        requests.append(
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": sheet_id,  # Use the integer sheet_id here
                                "startRowIndex": 1,
                                "endRowIndex": rows + 1,
                                "startColumnIndex": col,
                                "endColumnIndex": col + 1,
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": option}],
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": int(color[1:3], 16) / 255.0,
                                    "green": int(color[3:5], 16) / 255.0,
                                    "blue": int(color[5:7], 16) / 255.0,
                                }
                            },
                        },
                    },
                    "index": 0,
                }
            }
        )

    body = {"requests": requests}
    request = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    )
    execute_with_retry(request)


def apply_cell_color_verification(sheets_service, spreadsheet_id, sheet_id, rows):
    """
    1. If a cell is empty, turn it red.
    2. If column A doesn't have at least one uppercase word, turn it red.

    :param sheets_service: The Google Sheets API service object.
    :param spreadsheet_id: The ID of the spreadsheet where the sheet is located.
    :param sheet_id: The ID of the sheet.
    :param rows: The number of rows in the sheet.
    """
    requests = []
    # For both columns A and C
    for col_letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
        for row in range(2, rows + 2):  # skipping header, rows are 1-based
            if col_letter == "A":
                # Check if at least one word is uppercase in column A
                condition_formula = (
                    f'=OR(EXACT(A{row}, UPPER(A{row})), NOT(REGEXMATCH(A{row}, "\\b[A-Z]+\\b")))'
                )
            else:
                # Check if the cell is empty for column C
                condition_formula = f"=ISBLANK({col_letter}{row})"

            # Create a conditional formatting rule
            requests.append(
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": sheet_id,
                                    "startRowIndex": row - 1,
                                    "endRowIndex": row,
                                    "startColumnIndex": ord(col_letter) - ord("A"),
                                    "endColumnIndex": ord(col_letter) - ord("A") + 1,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": "CUSTOM_FORMULA",
                                    "values": [{"userEnteredValue": condition_formula}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 1.0,
                                        "green": 0.376 if col_letter == "A" else 0.788,
                                        "blue": 0.376 if col_letter == "A" else 0.486,
                                    }
                                },
                            },
                        },
                        "index": 0,
                    }
                }
            )

    # Batch update the conditional formatting rules
    body = {"requests": requests}
    request = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    )
    execute_with_retry(request)


def convert_excel_to_google_sheet(drive_service, file_id):
    """Convert an uploaded Excel file to a Google Sheet with exponential backoff."""
    file_metadata = {"mimeType": "application/vnd.google-apps.spreadsheet"}
    request = drive_service.files().copy(fileId=file_id, body=file_metadata, fields="id, webViewLink")
    converted_file = execute_with_retry(request)
    print(f"Google Sheet : {converted_file.get('webViewLink')}")
    file_id = converted_file.get("id")
    return file_id
