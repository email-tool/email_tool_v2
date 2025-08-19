import pandas as pd
import pickle
import os
import csv
from helper.csv_excel_loader import file_load
# Function to load and process the CSV file
def process_csv(file_path):
    # Load the CSV file
    data = file_load(file_path)

    # Convert all column names to lowercase
    data.columns = data.columns.str.lower()

    # Drop rows where "company" or "email format" are null
    data.dropna(subset=["company", 	"email pattern"], inplace=True)

    # Convert to dictionary
    new_dict = {}
    for _, row in data.iterrows():
        company = row["company"] # Normalize company name to lowercase
        email_format = row["email pattern"]
        new_dict[company] = email_format

    return new_dict

# Function to update the pickle file
def update_pickle(pickle_file, new_csv_file):
    print ("update_pickle", pickle_file)
    # Load the existing pickle file
    if os.path.exists(pickle_file):
        with open(pickle_file, "rb") as file:
            email_dict = pickle.load(file)
            print ("Shape of old data:", len(email_dict))
    else:
        email_dict = {}

    # Process the new CSV file
    new_data = process_csv(new_csv_file)

    # Update the existing dictionary with new data (replace if company already exists)
    email_dict.update(new_data)
    print ("Shape of new data:", len(email_dict))
    # Save the updated dictionary back to the pickle file
    # ensure no list item is there in pkl file

    email_dict = {key: value[0] if isinstance(value, list) and len(value) == 1 else value for key, value in email_dict.items()}



    with open(pickle_file, "wb") as file:
        pickle.dump(email_dict, file)

    print(f"****************Pickle file updated: {pickle_file}")
    return email_dict

