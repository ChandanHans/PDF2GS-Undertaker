import os
import time
import platform
import subprocess
import pytesseract
from openai import OpenAI
from unidecode import unidecode
from googleapiclient.http import MediaFileUpload

from .undertaker_data import get_undertaker_data
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
    file_name = f"Acte de décès - {name}.png"
    file_metadata = {"name": file_name, "parents": [FOLDER_ID1]}
    media = MediaFileUpload(image_path, mimetype="image/png")
    request = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink")
    uploaded_file = execute_with_retry(request)
    # Get the file ID and web link
    file_link = uploaded_file.get("webViewLink")

    # Append the image name and link to the Google Sheet
    row_data = [file_name, file_link]
    request = sheets_service.spreadsheets().values().append(
        spreadsheetId=IMAGE_SHEET_ID,
        range="Sheet1!A:B",
        valueInputOption="RAW",
        body={"values": [row_data]},
    )
    execute_with_retry(request)
    existing_images.append(row_data)
    return file_link


def get_existing_image_names(sheets_service, sheet_id):
    """
    Retrieve and cache the existing image names from the Google Sheet.
    This function is called once to avoid multiple requests to the sheet.
    """
    request = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="Sheet1!A:B", 
        )
    result = execute_with_retry(request)
    return result.get("values", [])


openai_client = OpenAI(api_key=GPT_KEY)
my_assistant = openai_client.beta.assistants.retrieve(ASSISTANT_ID)


def get_image_result(image_path):
    text = pytesseract.image_to_string(image_path, lang="fra")
    prompt = (
        "Text:\n"
        + text
        + """


1. Filter out unnecessary characters like (*, #, ~, etc.).
2. If any information is missing or if you believe the text is incomplete or not a valid death certificate, return an empty string ("") for the respective fields.
3. The declarant's information typically follows a pattern including the title 'Déclarant:' followed by their name and address. Correct any misspellings found in the text.
4. Ensure the following:
    - If any of the fields are not present, leave them as an empty string ("").
    - Correct obvious misspellings in address where applicable.
    - Return the result in the exact JSON format.

Please format the output as a JSON object, following this structure exactly:

{
    "Dead person full name": "" (Extract from the beginning of the text. Do not change any Upper Case or Lower Case),
    "Date of death": "" (The date should be in the format dd/mm/yyyy),
    "Declarant Name": "" (Declarant full name),
    "Declarant City": "" (Extract the city where the declarant is located),
    "Declarant Street": "" (House number and street address associated with the declarant. Include only the house number and street address, excluding the city name.)
}
"""
    )

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
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


def get_contact(address: str):
    address = unidecode(address).replace(" ", "").replace("-", "").replace(",", "").lower()
    undertaker_data = get_undertaker_data()
    for row in undertaker_data:
        if address in row[1]:
            return row[2], row[3]
    return None, None

def get_declarant_contact(name : str):
    name = unidecode(name).replace(" ", "").replace("-", "").replace(",", "").lower()
    undertaker_data = get_undertaker_data()
    for row in undertaker_data:
        if name in row[0]:
            return row[2], row[3]
    return None, None

def process_image(image, drive_service, sheets_service, existing_images):
    result = None
    try:
        t = time.time()
        city = street = dod = None
        image_path = f"{IMAGE_FOLDER}/{image}"
        image_result: dict[str, str] = get_image_result(image_path)
        name, dod, declarant_name, city, street = image_result.values()
        phone = email = None
        if declarant_name:
            phone, email = get_declarant_contact(declarant_name)
        if not(phone or email):
            if street:
                phone, email = get_contact(street)
            if city and not(phone or email):
                phone, email = get_contact(city)

        print(f"     {image} in {int(time.time()-t)} sec", end="\r")

        file_link = upload_image_and_append_sheet(
            name, image_path, drive_service, sheets_service, existing_images
        )
        result = [name, dod, declarant_name, city, street, phone, email, "à envoyer", file_link]
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
