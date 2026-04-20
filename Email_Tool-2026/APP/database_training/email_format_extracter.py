import pandas as pd
import re
import os
from database_training.reader import reader
import time
from datetime import datetime
def get_domain(row):
    try:
        email = row['email'].split("@")[1].strip().lower()
        return email
    except:
        return "unknown"  # In case no pattern is matched

def identify_email_pattern(row):
    first_name = row['first name'].strip().lower()
    last_name = row['last name'].strip().lower()
    email = row['email'].split("@")[0].strip().lower()

    # Ensure first_name and last_name are not empty before indexing
    first_initial = first_name[0] if first_name else ""
    last_initial = last_name[0] if last_name else ""


    # Define patterns for generating emails
    patterns = {
    "FirstName": first_name,
    "LastName": last_name,

    "FirstInitial": f"{first_name[0]}", 
    "LastInitial": f"{last_name[0]}", 

    "FirstName.LastName": f"{first_name}.{last_name}",
    "FirstName_LastName": f"{first_name}_{last_name}",
    "FirstName-LastName": f"{first_name}-{last_name}",
    "FirstNameLastName": f"{first_name}{last_name}",

    "LastName.FirstName": f"{last_name}.{first_name}",
    "LastName_FirstName": f"{last_name}_{first_name}",
    "LastName-FirstName": f"{last_name}-{first_name}",
    "LastNameFirstName": f"{last_name}{first_name}",

    "FirstName.LastInitial": f"{first_name}.{last_name[0]}",

    "FirstInitial.LastName": f"{first_name[0]}.{last_name}",

    "FirstInitialLastName": f"{first_name[0]}{last_name}",
    "FirstName1.LastName": f"{first_name[0]}.{last_name}",
    "FirstInitial_LastName": f"{first_name[0]}_{last_name}",
    "FirstInitial-LastName": f"{first_name[0]}-{last_name}",

    "FirstInitialLastInitial": f"{first_name[0]}{last_name[0]}",
    "FirstInitial.LastInitial": f"{first_name[0]}.{last_name[0]}",
    "FirstInitial_LastInitial": f"{first_name[0]}_{last_name[0]}",
    "FirstInitial-LastInitial": f"{first_name[0]}-{last_name[0]}",

    "FirstName.LastName1": f"{first_name}.{last_name[0]}",
    "FirstName_LastInitial": f"{first_name}_{last_name[0]}",
    "FirstName-LastInitial": f"{first_name}-{last_name[0]}",
    "FirstNameLastInitial": f"{first_name}{last_name[0]}",

    "LastName.FirstInitial": f"{last_name}.{first_name[0]}",
    "LastName_FirstInitial": f"{last_name}_{first_name[0]}",
    "LastName-FirstInitial": f"{last_name}-{first_name[0]}",
    "LastNameFirstInitial": f"{last_name}{first_name[0]}",

    "FirstInitialLastNameLastInitial": f"{first_name[0]}{last_name}{last_name[0]}",  # Fixed from FirstInitialLastName1
    "FirstName1LastName": f"{first_name[0]}{last_name}",  # Fixed from FirstName1LastName
    "FirstNameLastName1": f"{first_name}{last_name[0]}",  # Fixed from FirstNameLastName1
    "LastInitialFirstName": f"{last_name[0]}{first_name}",  # Fixed from LastName1FirstName  FirstName1LastName
    "LastNameFirstName1": f"{last_name}{first_name[0]}",  # Fixed from LastNameFirstName1

    "LastInitial.FirstInitial": f"{last_name[0]}.{first_name[0]}",
    "LastInitial-FirstInitial": f"{last_name[0]}-{first_name[0]}",
    "LastInitial_FirstInitial": f"{last_name[0]}_{first_name[0]}",
    "LastInitialFirstInitial": f"{last_name[0]}{first_name[0]}",

    "LastInitial.FirstName": f"{last_name[0]}.{first_name}",
    "LastInitial-FirstName": f"{last_name[0]}-{first_name}",
    "LastInitial_FirstName": f"{last_name[0]}_{first_name}",
    "LastInitialFirstName": f"{last_name[0]}{first_name}",
    }

    # Check each pattern and return the matching pattern
    for pattern_name, pattern in patterns.items():
        if pattern == email:
            return pattern_name

    return "unknown"  # No match found

def db_email_extracter(file_path):
    try:
        processed_data = reader(file_path)
        print (processed_data.head())
        processed_data['email pattern'] = processed_data.apply(identify_email_pattern, axis=1) + '@' + processed_data.apply(get_domain, axis=1)

        print("Processed DataFrame with Email Patterns:")
        
        # Select only the required columns
        processed_data = processed_data[['company', 'email pattern']]
        
        # **Filter out rows where email pattern contains "unknown"**
        processed_data = processed_data[~processed_data['email pattern'].str.contains("unknown@", na=False)]

        return processed_data
    except ValueError as e:
        print(f"Error: {e}")
        return None

def get_email_formats(file_path):
    start_time = time.time()  # Start time tracking

    try:
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)

        elif file_path.endswith(('.xls', '.xlsx')):
            # Load first 5 sheets and combine them
            excel_data = pd.ExcelFile(file_path, engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd')
            sheets = excel_data.sheet_names[:5]
            data = pd.concat([excel_data.parse(sheet) for sheet in sheets], ignore_index=True)

        else:
            print("❌ Unsupported file format. Please provide a CSV or Excel file.")
            return None
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

    processed_data = db_email_extracter(file_path)  # Pass DataFrame, not file_path

    end_time = time.time()  # End time tracking
    time_taken = end_time - start_time

    print(f"Processing completed in {time_taken:.2f} seconds")  # Print execution time

    return processed_data





def process_single_file(input_file, output_folder):
    try:
        # Get the current date for the output filename
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Check if the output folder exists; if not, create it
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Get the file name without the extension
        file_name_only, file_extension = os.path.splitext(os.path.basename(input_file))

        print("Processing file:", file_name_only)

        # Check if the file is a supported format (CSV or Excel)
        if file_extension.lower() in ['.csv', '.xls', '.xlsx']:
            try:
        
                processed_data = get_email_formats(input_file)
                print ("get_email_formats")
                # Get the number of rows in processed data
                num_rows = len(processed_data)
                print(f"Number of rows processed: {num_rows}")

                # Save output file
                output_file_name = f"{file_name_only}_{current_date}_output.csv"
                output_file_path = os.path.join(output_folder, output_file_name)
                processed_data.to_csv(output_file_path, index=False)

                print(f"Processed data saved to: {output_file_path}")

            except Exception as e:
                print(f"Error processing file {input_file}: {e}")
        else:
            print(f"Unsupported file type: {file_extension}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

