# main.py
from src.vcs import check_for_updates

check_for_updates()

import os
import time
import shutil
import pandas as pd
from tqdm import tqdm
from googleapiclient.discovery import build

from src.pdf_processing import pdf_to_images
from src.excel_util import save_table
from src.image_processing import *
from src.utils import *
from src.constants import *
from src.drive_upload import *
from src.undertaker_data import get_uploaded_sheets


def main():
    # Authenticate Google Drive once and get the service instances
    creds = authenticate_google_drive()
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)


    existing_images = get_existing_image_names(sheets_service, SHEET_ID)


    check_for_tesseract()

    pdf_files = [
        file for file in os.listdir(INPUT_FOLDER) if file.lower().endswith(".pdf")
    ]

    for pdf in pdf_files:
        pdf_name = os.path.basename(pdf)
        pdf_path = f"{INPUT_FOLDER}/{pdf}"
        excel_path = pdf_path.replace(".pdf", ".xlsx").replace(INPUT_FOLDER, OUTPUT_FOLDER)

        # Check if the Excel file already exists locally; if it does, skip processing
        if os.path.exists(excel_path):
            print(f"Skipping {pdf_name}, corresponding Excel file already exists locally.")
            continue

        time_start = time.time()
        print(f"\nProcess Started For {pdf_name}\n")
        if pdf_name.replace(".pdf", "") not in get_uploaded_sheets(drive_service, pdf_name, FOLDER_ID2):

            # Convert PDF to images
            pdf_to_images(pdf_path, IMAGE_FOLDER, 200, 3)

            images = [
                file for file in os.listdir(IMAGE_FOLDER) if file.lower().endswith(".png")
            ]
            images = sorted(images, key=extract_number)
            data = []

            print("\nSTART :\n")
            progress_bar = tqdm(images, ncols=60, bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}")
            for image in progress_bar:
                sleep(1)
                result = process_image(image, drive_service, sheets_service,existing_images)  # Pass services
                if result:
                    data.append(result)

            print()
            df = pd.DataFrame(data)
            df.columns = [
                "Name",
                "Date Of Death", 
                "Declarant Name", 
                "City", 
                "Street",
                "Phone",            
                "Email",
                "Status",
                "Image"
            ]
            save_table(df, excel_path)
        
            # Upload Excel to Google Drive and convert it to Google Sheet
            upload_to_drive(drive_service, pdf_path, FOLDER_ID2)
            excel_drive_id = upload_to_drive(drive_service, excel_path, FOLDER_ID2)

            sheet_id = convert_excel_to_google_sheet(drive_service, excel_drive_id)
            
            apply_sheet_customizations(sheets_service, sheet_id, 7)
            # After conversion, delete the Excel file from Google Drive
            delete_file_from_drive(drive_service, excel_drive_id)
        else:
            print('Already uploaded')
           # Move the processed PDF file to the completed folder
        shutil.move(pdf_path, f"{COMPLETED_FOLDER}/{pdf}")
        
        print(f"Completed processing for {pdf_name} in {int(time.time() - time_start)} sec")

    print("\n\nAll Files Completed")
    countdown("Exit", 3)


if __name__ == "__main__":
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)
    if not os.path.exists(COMPLETED_FOLDER):
        os.makedirs(COMPLETED_FOLDER)
    main()