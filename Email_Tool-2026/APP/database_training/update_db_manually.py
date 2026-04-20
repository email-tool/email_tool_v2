import pandas as pd
import pickle
import os
import csv
from helper.csv_excel_loader import file_load


# Function to load and process the CSV file
def process_csv(file_path):
    # Load the file
    data = file_load(file_path)

    # Normalize column names
    data.columns = data.columns.str.lower().str.strip()

    # Handle new file format:
    # "mail patterns" -> "email pattern"
    if "mail patterns" in data.columns and "email pattern" not in data.columns:
        data.rename(columns={"mail patterns": "email pattern"}, inplace=True)

    # Validate required base column
    if "company" not in data.columns:
        raise KeyError("Required column 'company' not found")

    if "email pattern" not in data.columns:
        raise KeyError("Required column 'email pattern' not found")

    # Fill NaN to avoid errors during string operations
    data["company"] = data["company"].fillna("").astype(str).str.strip()
    data["email pattern"] = data["email pattern"].fillna("").astype(str).str.strip()

    

    # If new file has separate domain column, combine it
    if "add domain" in data.columns:
        data["add domain"] = data["add domain"].fillna("").astype(str).str.strip()

        def combine_pattern_domain(row):
            pattern = row["email pattern"]
            domain = row["add domain"]

            # If already full pattern like FirstName.LastName@abc.com, keep as is
            if "@" in pattern:
                return pattern

            # If pattern exists and domain exists, combine them
            if pattern and domain:
                return f"{pattern}@{domain}"

            return pattern

        data["email pattern"] = data.apply(combine_pattern_domain, axis=1)

    # Drop rows where required columns are missing/blank
    data = data[
        (data["company"] != "") &
        (data["email pattern"] != "")
    ]

    # Always remove invalid email patterns
    invalid_patterns = ["no valid pattern found", "unknown pattern"]

    data = data[
        ~data["email pattern"].str.lower().isin(invalid_patterns)
    ]
    
    # Convert to dictionary
    new_dict = {}
    for _, row in data.iterrows():
        company = row["company"].strip().lower()
        email_format = row["email pattern"].strip()
        new_dict[company] = email_format

    return new_dict


# Function to update the pickle file
def update_pickle(pickle_file, new_csv_file):


    # Load existing pickle
    if os.path.exists(pickle_file):
        with open(pickle_file, "rb") as file:
            email_dict = pickle.load(file)
        print("Shape of old data:", len(email_dict))
    else:
        email_dict = {}

    # Process new CSV


    new_data = process_csv(new_csv_file)
    email_dict.update(new_data)
    print("Shape of new data:", len(email_dict))

    # Ensure no list items in pickle
    email_dict = {
        key: value[0] if isinstance(value, list) and len(value) == 1 else value
        for key, value in email_dict.items()
    }

    # Save updated pickle
    with open(pickle_file, "wb") as file:
        pickle.dump(email_dict, file)

    print(f"**************** Pickle file updated: {pickle_file}")
    return email_dict