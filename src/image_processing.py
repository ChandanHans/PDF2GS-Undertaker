import os
import time
import platform
import subprocess
import pytesseract
from openai import OpenAI
from functools import lru_cache
from unidecode import unidecode
from googleapiclient.http import MediaFileUpload

from .undertaker_data import get_undertaker_data
from .constants import IMAGE_FOLDER, SHEET_ID, FOLDER_ID1
from .constants import *
from .utils import *

# image_processing.py


def clean_name_for_comparison(name: str):
    """Clean the name by removing spaces, commas, and dashes."""
    return unidecode(name).replace(" ", "").replace(",", "").replace("-", "").lower()


def upload_image_and_append_sheet(
    name, image_path, drive_service, sheets_service, existing_images=None
):
    """
    Upload the image to Google Drive and append its name and link to a Google Sheet.

    If the image already exists in the sheet, skip upload and append.
    """
    # Clean the name for comparison
    cleaned_name = clean_name_for_comparison(name)

    # Check if the image already exists in the sheet
    if existing_images is None:
        existing_images = []  # Ensure there's an empty list if no data is passed
    for image in existing_images:
        if cleaned_name in clean_name_for_comparison(image[0]):
            return image[1]

    # Upload the image to the folder
    file_metadata = {"name": f"Acte de décès - {name}.png", "parents": [FOLDER_ID1]}
    media = MediaFileUpload(image_path, mimetype="image/png")
    uploaded_file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )

    # Get the file ID and web link
    file_link = uploaded_file.get("webViewLink")

    # Append the image name and link to the Google Sheet
    row_data = [[f"Acte de décès - {name}.png", file_link]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="Sheet1!A:B",
        valueInputOption="RAW",
        body={"values": row_data},
    ).execute()
    return file_link


def get_existing_image_names(sheets_service, sheet_id):
    """
    Retrieve and cache the existing image names from the Google Sheet.
    This function is called once to avoid multiple requests to the sheet.
    """
    result = (
        sheets_service.spreadsheets()
        .values()
        .get(
            spreadsheetId=sheet_id,
            range="Sheet1!A:B",  # Assuming the image names are in column A
        )
        .execute()
    )
    return result.get("values", [])


openai_client = OpenAI(api_key=GPT_KEY)
my_assistant = openai_client.beta.assistants.retrieve(ASSISTANT_ID)


def get_image_result(image_path):
    text = pytesseract.image_to_string(image_path, lang="fra")
    prompt = (
        "Text:\n"
        + text
        + """

Prompt:
1. Filter unnecessary characters like (*, #, ~, etc.).

- The full name of the deceased person 
- Date of death (date in format dd/mm/yyyy).
- City associated with the declarant
- House number and street address associated with the declarant (without including the city name).

Do not change the name case first name should be in lower case and LAST NAME should be in upper case.
The declarant's information typically follows a pattern including the title 'Déclarant:' followed by their name and then their address. if there is any miss spell then correct it.

Your response must be in this JSON format:

{
    "dead person full name": "",
    "Date of death": "",
    "declarant City": "",
    "declarant street address": "",
}
"""
    )

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"},
    )
    result = eval(response.choices[0].message.content)
    return result


def get_contact_from_sheet(address: str):
    address = unidecode(address).replace(" ", "").replace("-", "").replace(",", "").lower()
    undertaker_data = get_undertaker_data()
    for row in undertaker_data:
        if address in row[0]:
            return row[1], row[2]
    return None, None


@lru_cache(maxsize=None)
def get_contact(name):
    phone, email = get_contact_from_sheet(name)
    return phone, email


def process_image(image, drive_service, sheets_service, existing_images):
    result = None
    try:
        t = time.time()
        city = street = dod = None
        image_path = f"{IMAGE_FOLDER}/{image}"
        image_result: dict[str, str] = get_image_result(image_path)
        name, dod, city, street = image_result.values()
        phone = email = None
        if street:
            phone, email = get_contact(street)
        if city and not(phone or email):
            phone, email = get_contact(city)

        print(f"     {image} in {int(time.time()-t)} sec", end="\r")

        file_link = upload_image_and_append_sheet(
            name, image_path, drive_service, sheets_service, existing_images
        )
        result = [name, dod, city, street, phone, email, "à envoyer", file_link]
    except Exception as e:
        print(e)

    return result


def check_for_tesseract():
    os_name = platform.system()
    if os_name == "Windows":
        if os.path.exists("C:/Program Files/Tesseract-OCR"):
            tesseract_path = "C:/Program Files/Tesseract-OCR/tesseract.exe"
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            if "fra" in pytesseract.get_languages():
                return
        else:
            pass
        print("!! tesseract is not installed !!")
        print(
            "Download and install tesseract : https://github.com/UB-Mannheim/tesseract/wiki"
        )
        print("Select French language during installation")
        input()
        sys.exit()
    else:
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                if "fra" in pytesseract.get_languages():
                    return
        except FileNotFoundError:
            pass
        print("!! tesseract-fra is not installed !!")
        print('Install tesseract-fra with this command : "brew install tesseract-fra"')
        input()
        sys.exit()
