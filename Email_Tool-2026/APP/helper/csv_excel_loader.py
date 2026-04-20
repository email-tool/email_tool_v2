
import os
import pandas as pd
def file_load(file_path):
    # Determine file extension
    _, file_extension = os.path.splitext(file_path)
    
    # Load the data
    if file_extension == ".csv":
        data = pd.read_csv(file_path)
    elif file_extension in [".xls", ".xlsx"]:
        # Read up to 5 sheets and append data into one DataFrame
        excel_data = pd.ExcelFile(file_path)
        sheets = excel_data.sheet_names[:5]  # Get the first 5 sheets
        data = pd.concat([excel_data.parse(sheet) for sheet in sheets], ignore_index=True)
    else:
        raise ValueError("Unsupported file format. Only CSV and Excel files are allowed.")
    
    return data