import pandas as pd
import os
import re

def process_file(file_path):
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
    
    # Strip spaces from column names
    try:
        data.columns = data.columns.str.strip()

        # Define the required columns
        required_columns = ["Company", "Contact Name"]
        all_columns = ["Srl No", "Company", "Contact Name", "First Name", "Last Name",
                    "Designation", "Location", "Industry", "Mailer_Status"]

        # Check for missing required columns
        missing_required_columns = [col for col in required_columns if col not in data.columns]
        if missing_required_columns:
            raise ValueError(f"Missing mandatory columns: {', '.join(missing_required_columns)}")
        
        # If "First Name" and "Last Name" are missing, create them by splitting "Contact Name"
        if "First Name" not in data.columns or "Last Name" not in data.columns:
            print ("Missing columns First Name or Last Name")
            if "Contact Name" in data.columns:
                # Split the "Contact Name" into "First Name" and "Last Name"
                split_names = data["Contact Name"].str.split(" ", n=1, expand=True)
                data["First Name"] = split_names[0].apply(lambda x: re.sub(r'^[^a-zA-Z]+', '', str(x).strip()))
                data["Last Name"] = data["Contact Name"].apply(lambda x: str(x).split()[-1].strip() if isinstance(x, str) else "NA")
        
        # Add any missing non-mandatory columns and fill with "NA"
        for col in all_columns:
            if col not in data.columns:
                data[col] = "NA"
        
        # Ensure all column values are stripped of leading/trailing spaces
        for col in data.columns:
            if data[col].dtype == "object":  # Only process string columns
                data[col] = data[col].astype(str).str.strip()
    except ValueError as e:
        print(f"Error: {e}") 
    return data

def reader(file_path):
    try:
        processed_data = process_file(file_path)
        processed_data = processed_data[["Srl No", "Company", "Contact Name", "First Name", "Last Name",
                                         "Designation", "Location", "Industry", "Mailer_Status"]]
        processed_data.dropna(subset=["Company", "Contact Name", "First Name", "Last Name"], inplace=True)
        

        
        return processed_data
    except ValueError as e:
        print(f"Error: {e}")
        return e
