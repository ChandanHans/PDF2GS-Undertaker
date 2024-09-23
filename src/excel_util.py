import xlsxwriter

def save_table(df, file_path):
    # Create a workbook and add a worksheet
    workbook = xlsxwriter.Workbook(file_path, {"nan_inf_to_errors": True})
    worksheet = workbook.add_worksheet()

    # Write column headers
    worksheet.write_row(0, 0, df.columns)

    # Write data rows
    for idx, row in df.iterrows():
        worksheet.write_row(idx + 1, 0, row)

    # Get the correct table reference (adjust to 1-based indexing)
    max_row = len(df)  # Number of rows in the dataframe
    max_col = len(df.columns)  # Number of columns in the dataframe

    # Create the correct reference for the table (Excel range)
    table_ref = f"A1:{xlsxwriter.utility.xl_col_to_name(max_col - 1)}{max_row + 1}"

    # Add a table to the worksheet
    worksheet.add_table(table_ref, {
        'name': 'MyTable',
        'columns': [{'header': col} for col in df.columns],
        'style': 'Table Style Medium 6',
    })

    # Adjust column widths
    for col_num, _ in enumerate(df.columns, start=0):
        worksheet.set_column(col_num, col_num, 30)

    # Close the workbook
    workbook.close()
