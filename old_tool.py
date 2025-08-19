import os,pickle
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from helper.csv_excel_loader import file_load
from email_verifier.email_verifier import verify_app
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
from database_training.database_process_mutifile import process_files_and_save_output

import pandas as pd
from database_training.update_db_manually import update_pickle
from email_creation.create_emails import email_creator_app
from database_training.database_process_single_file import process_single_file
from automatic_email_format import scrapper_run

'''
----------------------------------------------------------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------
'''
@app.route('/')
def dashboard():
    return render_template('dashboard.html')


'''
------------------------------------------------------------Database-----------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------
'''


import os

# Get the full path of the script
script_path = os.path.abspath('appy.py')

# Get the directory containing the script
user_path = os.path.dirname(script_path)
print("Base directory:", user_path)
base_path = user_path+"/files/"
print("Base directory:", base_path)
Source_file_path = base_path+'database_source_files'
Output_files_path = base_path+'database_output_files'
new_db_pickle_file_path = base_path+'main_database//'+'new_db.pkl'
old_db_pickle_file_path = base_path+'main_database//'+'old_db.pkl'
email_created_path = base_path+'created_emails'

scrapper_output = base_path + 'automatic_emails_format_created'
missing_data = base_path+'missing_emails'
verified_path = base_path+'verified_emails'


@app.route('/upload', methods=['POST'])
def upload_file():
    print("Received request...")
    log_message = "Tool"

    if 'file' not in request.files:
        print("Error: No file in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file:
        print("Processing single file...")

        # Ensure UPLOAD_FOLDER exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        # Save the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        print(f"File saved at: {file_path}")

        try:
            process_single_file(file_path, Output_files_path,old_db_pickle_file_path)
            
            log_message = "File processed successfully!"
        except Exception as e:
            log_message = f"Error processing file: {str(e)}"

        

    
    if 'folder' in request.files:

        print ("folder is selected")
        
        files = request.files.getlist('folder')  # Get all files in the folder
        filenames = [file.filename for file in files if file.filename != '']
        for i in filenames:
            print ("filenames ",i)
            try:
                if i.endswith('.csv') or i.endswith('.xlsx'):
                    file_path = f"{base_path}//{i}"

                    process_single_file(file_path, Output_files_path,old_db_pickle_file_path)

            except Exception as e:
                log_message = f"Error processing file: {str(e)}"
      
        log_message = "File processed successfully!"

        return jsonify({"log": log_message})




@app.route('/update-database-manually', methods=['POST'])
def update_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']


    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            # data = pd.read_excel(file_path) if file.filename.endswith('.xlsx') else pd.read_csv(file_path)
            updated_dictd = update_pickle(new_db_pickle_file_path, file_path)
            from pathlib import Path
            import csv

            file_paths = Path(new_db_pickle_file_path)
            folder_path = file_paths.parent
            #create csv out of dictionary
            if isinstance(updated_dictd, dict):
                # Write to CSV with UTF-8 encoding
                print (folder_path / "new_database.csv")
                with open(folder_path / "new_database.csv", "w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(["Key", "Value"])  # Header
                    for key, value in updated_dictd.items():
                        writer.writerow([key, value])
            updated_dict = update_pickle(old_db_pickle_file_path, file_path)
        
            if isinstance(updated_dict, dict):
                # Write to CSV with UTF-8 encoding
                print (folder_path / "old_database.csv")
                with open(folder_path / "old_database.csv", "w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(["Key", "Value"])  # Header
                    for key, value in updated_dict.items():
                        writer.writerow([key, value])

            log_message = "File processed successfully! Rows:, Columns:"
        except Exception as e:
            log_message = f"Error processing file: {str(e)}"
        return jsonify({"log": log_message})


    if 'folder' in request.files:

        print ("folder is selected")
        
        files = request.files.getlist('folder')  # Get all files in the folder
        filenames = [file.filename for file in files if file.filename != '']
        for i in filenames:
            print ("filenames ",i)
            try:
                if i.endswith('.csv') or i.endswith('.xlsx'):
                    file_path = f"{base_path}//{i}"

                    updated_dict = update_pickle(old_db_pickle_file_path, file_path)
                    updated_dict = update_pickle(new_db_pickle_file_path, file_path)

                    log_message = "File processed successfully! Rows:, Columns:"
                    log_message = "File processed successfully!"
            except Exception as e:
                log_message = f"Error processing file: {str(e)}"
        print("log", log_message)
    

        return jsonify({"log": log_message})





'''
-------------------------------------------------------------Email-------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------
'''

@app.route('/email', methods=['POST'])
def create_email():

    # Load the pickle file
    with open(old_db_pickle_file_path, 'rb') as f:
        email_patterns = pickle.load(f)

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    if 'folder' in request.files:

        print ("folder is selected")
        
        files = request.files.getlist('folder')  # Get all files in the folder
        filenames = [file.filename for file in files if file.filename != '']
        combined_email_data = pd.DataFrame()
        for i in filenames:
            print ("filenames ",i)

            try:
                if i.endswith('.csv') or i.endswith('.xlsx'):
                    dir_file = f"{base_path}/{i}"
                    print (f"file names {dir_file}")
                    df = email_creator_app(dir_file,email_patterns)

                    missing = df[df["Email"].isna() | (df["Email"].str.strip() == "")]

                    email_data = df[df["Email"].notna() & (df["Email"].str.strip() != "")]

                    combined_email_data = pd.concat([combined_email_data, email_data], ignore_index=True)

                                        # Get file name without extension
                    file_name_no_ext = os.path.splitext(os.path.basename(i))[0]

                    filename_csv = f"{email_created_path}//{file_name_no_ext}_old_tool_output.csv"

                    email_data.to_csv(filename_csv)
                    missing_file_name =   f"{missing_data}//{file_name_no_ext}_missing.csv"
                    missing.to_csv(missing_file_name)

                    print (df.head(1))
                    rows, columns = df.shape
                    log_message = f"File processed successfully! Rows: {rows}, Columns: {columns}"


                   
            except Exception as e:
             print(f"Error processing {i}: {str(e)}")

                # Save the final combined DataFrames after the loop
        final_email_file = f"{email_created_path}/combined_email_output.csv"

        combined_email_data.to_csv(final_email_file, index=False)


    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        print ("file is selected")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Process the file
        try:

            df = email_creator_app(file_path,email_patterns)
            
            missing = df[df["Email"].isna() | (df["Email"].str.strip() == "")]

            email_data = df[df["Email"].notna() & (df["Email"].str.strip() != "")]

                                # Get file name without extension
            file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]

            filename_csv = f"{email_created_path}//{file_name_no_ext}_old_tool_output.csv"

            email_data.to_csv(filename_csv)
            missing_file_name =   f"{missing_data}//{file_name_no_ext}_missing.csv"
            missing.to_csv(missing_file_name)

            print (df.head(1))
            rows, columns = df.shape
            log_message = f"File processed successfully! Rows: {rows}, Columns: {columns}"
        except Exception as e:
            log_message = f"Error processing file: {str(e)}"

        return jsonify({"log": log_message})


'''
--------------------------------------------------------------Verify-------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------
'''

@app.route('/email-verify', methods=['POST'])
def verify_email():

    # Load the pickle file
    with open(old_db_pickle_file_path, 'rb') as f:
        email_patterns = pickle.load(f)

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400


    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Process the file
        try:
                                            # Get file name without extension
            api_key = '748ad80421514463bb9099b85004b0dd'
            url = 'https://api.zerobounce.net/v2/validate'
            df= verify_app(file_path, api_key)
            file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]

            filename_csv = f"{verified_path}//{file_name_no_ext}_Verified.csv"

            df.to_csv(filename_csv)

            rows, columns = df.shape
            log_message = f"File processed successfully! Rows: {rows}, Columns: {columns}"
        except Exception as e:
            log_message = f"Error processing file: {str(e)}"

        return jsonify({"log": log_message})


'''
--------------------------------------------------------automatic email formats------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------
'''


import time


@app.route('/automatic-email', methods=['POST'])
def automatic_email():


    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        print (file_path)

        scrapper_run.app_run(file_path,old_db_pickle_file_path,new_db_pickle_file_path,scrapper_output)


        #     log_message = f"File processed successfully! Rows: {file_path}"
        # except Exception as e:
        #     log_message = f"Error processing file: {str(e)}"

        return jsonify({"log": "log_message"})







'''
--------------------------------------------------------Split File------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------
'''

@app.route('/split-file', methods=['POST'])
def split_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Read the file and print first 5 rows
        try:
            if file.filename.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)

            print(df.head())  # Print first 5 rows

            log_message = f"File uploaded successfully! Showing first 5 rows:\n{df.head().to_string()}"
        except Exception as e:
            log_message = f"Error processing file: {str(e)}"

        return jsonify({"log": log_message})





@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    # Clear log functionality (optional if needed)
    return jsonify({"log": "Logs cleared!"})

if __name__ == '__main__':
    app.run(host ='old-tool', port=4000, debug=True)
