import os,pickle,random, math
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from helper.csv_excel_loader import file_load
from email_verifier.email_verifier import verify_app
from automatic_email_format.web_email_scrapper_multiEngine import recover_with_latest, update_pickle_file,fetch_google_results
from automatic_email_format.get_best_email import run, extract_results_lists, get_final_email
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
from database_training.database_process_mutifile import process_files_and_save_output
from automatic_email_format.process_scrapped_data import process_run
import tempfile
import pandas as pd
from database_training.update_db_manually import update_pickle
from email_creation.create_emails import email_creator_app
from database_training.database_process_single_file import process_single_file
from automatic_email_format import scrapper_run
from automatic_email_format.scarpper_manager import scrapper_manager , get_email_pattern
from automatic_email_format.get_email_flags import get_flags
from flask_socketio import SocketIO
from datetime import datetime

socketio = SocketIO(app, cors_allowed_origins="*")
log_file_path = "log.txt"  # Log file to read
import logging

log = logging.getLogger("werkzeug")
handler = logging.FileHandler("flask_access.log")  # Save logs in this file
log.addHandler(handler)
log.setLevel(logging.INFO)  # You can change to ERROR if you only want errors


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
print("Tool is started")
base_path = user_path+"/files/"
Source_file_path = base_path+'database_source_files'
Output_files_path = base_path+'database_output_files'
Output_files_path_new = base_path+'database_output_files_new'
new_db_pickle_file_path = base_path+'main_database//'+'new_db.pkl'
old_db_pickle_file_path = base_path+'main_database//'+'old_db.pkl'


new_db_pickle_file_path_bckup = base_path+'main_database//'+'new_db_backup.pkl'
old_db_pickle_file_path_bckup = base_path+'main_database//'+'old_db_backup.pkl'


email_created_path = base_path+'created_emails'

scrapper_output = base_path + 'automatic_emails_format_created'
missing_data = base_path+'missing_emails'
verified_path = base_path+'verified_emails'

track_automation = "track_automation"

dirs_to_create = {
    "source_files": os.path.join(base_path, "database_source_files"),
    "output_files": os.path.join(base_path, "database_output_files"),
    "output_files_new":  os.path.join(base_path, "database_output_files_new"),
    "main_db": os.path.join(base_path, "main_database"),
    "created_emails": os.path.join(base_path, "created_emails"),
    "scraper_output": os.path.join(base_path, "automatic_emails_format_created"),
    "missing_data": os.path.join(base_path, "missing_emails"),
    "verified": os.path.join(base_path, "verified_emails"),
    "track_automation" : "track_automation"
}

# Create all directories if they don't exist
for name, path in dirs_to_create.items():
    os.makedirs(path, exist_ok=True)


# Data to initialize if files are missing
new_data = {'10th sfg': 'LastName@soc.mil'}

# Helper function to safely create pickle file if it doesn't exist
def create_pickle_if_missing(file_path, data):
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            pickle.dump(data, f)
# Check and create both files
create_pickle_if_missing(new_db_pickle_file_path, new_data)
create_pickle_if_missing(old_db_pickle_file_path, new_data)


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
            process_single_file(file_path, Output_files_path_new,new_db_pickle_file_path)
            
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

                    process_single_file(file_path, Output_files_path_new,new_db_pickle_file_path)
                   

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

                    updated_dict = update_pickle(new_db_pickle_file_path, file_path)
                    updated_dict = update_pickle(old_db_pickle_file_path, file_path)

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
    with open(new_db_pickle_file_path, 'rb') as f:
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

                    filename_csv = f"{email_created_path}//{file_name_no_ext}_new_tool_output.csv"

                    email_data.to_csv(filename_csv)

                    missing_file_name =   f"{missing_data}//{file_name_no_ext}_new_tool_missing.csv"
                    missing.to_csv(missing_file_name)
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

            filename_csv = f"{email_created_path}//{file_name_no_ext}_new_tool_output.csv"

            email_data.to_csv(filename_csv)
            missing_file_name =   f"{missing_data}//{file_name_no_ext}__new_tool_missing.csv"
            missing.to_csv(missing_file_name)
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
from datetime import datetime, timedelta

def log_query_result(log_file, query, results, error=None):
    """Logs each query with its results or errors in a persistent text file."""
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if error:
            log_entry = f"{timestamp} | QUERY: {query} | ERROR: {error}\n"
        else:
            log_entry = f"{timestamp} | QUERY: {query} | RESULTS: {results}\n"

        f.write(log_entry)
        f.flush()  # Ensure data is written immediately

def make_backup_db(main_file_path, backup_path):
    # Step 1: Load data from main pickle file
    with open(main_file_path, 'rb') as f:
        email_patterns = pickle.load(f)

    # Step 2: Save data to backup pickle file
    with open(backup_path, 'wb') as f:
        pickle.dump(email_patterns, f)


@app.route('/automatic-email', methods=['POST'])

def automatic_email():
    # Load the pickle file
    with open(new_db_pickle_file_path, 'rb') as f:
        email_patterns = pickle.load(f)

    try:
        make_backup_db(new_db_pickle_file_path, new_db_pickle_file_path_bckup)
        make_backup_db(old_db_pickle_file_path, old_db_pickle_file_path_bckup)
        update_pickle_file(new_db_pickle_file_path, "temp_file.pkl", new_db_pickle_file_path_bckup)
        update_pickle_file(old_db_pickle_file_path, "temp_file.pkl", old_db_pickle_file_path_bckup)
    except:
        pass

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400



# =================================================================================================================================================
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        readfile_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        output_txt_file = "track_automation//"+file_name + "_Companies.txt"
        output_txt_file = output_txt_file.replace(" ","")
        checkpoint_file = "track_automation//"+file_name+"_CheckPoint.txt"

        folder_name = "track_automation"
        # Get current date and time (formatted as string)
        now = datetime.now().strftime("%Y-%m-%d")
        file_path_logs = f"logs_for_tracking{now}.txt"

                # Construct full path
        log_full_file = os.path.join(folder_name, file_path_logs)


        log_full_file_full_path = os.path.abspath(log_full_file)
        print("log_full_file_full_path", log_full_file_full_path)


        checkpoint_file = checkpoint_file.replace(" ","")
        df = pd.read_csv(file_path)
        unique_companies = df["Company"].dropna().unique()  # Assuming 'company_name' is the column name

        # Write unique company names to the output text file with index
        with open(output_txt_file, "w") as f:
            for i, company in enumerate(unique_companies, start=0):
                f.write(f"{i} {company}\n")

        with open(output_txt_file, "r" ) as file:
            company_list = [line.strip().split(maxsplit=1)[1] for line in file if line.strip()]

        # Determine the starting index from the checkpoint file
        total_results = int(0)
        total_results2 = int(0)
        if os.path.exists(checkpoint_file):

            try:

                with open(checkpoint_file, "r") as f:
                    last_index, last_file, total_results = f.readline().strip().split()
                    last_index = int(last_index)

            except:

                last_index, last_file, total_results  = recover_with_latest(log_full_file_full_path, output_txt_file, checkpoint_file)
        else:
            last_index = 0
            with open(checkpoint_file, "w") as f:
                f.write(f"{last_index} {output_txt_file} {total_results}\n")
# ================================================================================================================================
 
        # Define batch size
        Start_point = 0
        proxy1 = "http://proxyuser:emailtool@173.224.122.109:3127"  # tvllV5sSSczc  ll

        proxy2 = "http://proxyuser:emailtool@173.224.122.126:3129"

        proxy3 = "http://proxyuser:emailtool@173.224.122.123:3130"
        proxy4 = "http://proxyuser:emailtool@173.224.122.122:3128"

        flag = True


        proxy_flag = [int(x) for x in [0, 1, 2,3]]
        proxy_count = len(proxy_flag)
        FLAG = 0

        
        total_results2 = total_results
        BATCH_SIZES  = 30000 # file size
        batch_row = 2500# first batch in outer circle 
        batch_size = 45 # batch inside circle
        # Folder and file name


        all_results = []
        queries = company_list[last_index:last_index+BATCH_SIZES]
        # Get the number of full batches
        num_batches = len(queries) // batch_row  # Number of complete batches
        print ("num_batches", num_batches)
        remainder = len(queries) % BATCH_SIZES # Remaining elements in an extra batch (if any)
        # Iterate over batches
        
        final_count_emails = 0
        cnt = 0
        g = 0
# ================================================================================================================================
        total_rows = 0
        for batch_idx in range(num_batches + (1 if remainder > 0 else 0)):  # Include remainder batch            

            start_index = batch_idx * batch_row
            end_index = min(start_index + batch_row, len(queries))  # Avoid exceeding list size
            batch = queries[start_index:end_index]
            print ("\n", f"**************************  Batch:: {start_index}_{end_index}  *********************************")
            print (f"starting from {last_index} row")

            # Print batch details
            namefile = f"{scrapper_output}/Batch_{start_index}_{end_index}_google_"
            df_raw=0
            num_batches2 = math.ceil(len(batch) / batch_size)
            # df_raw= scrapper_manager(queries[start_index:end_index],namefile, last_index, output_txt_file,old_db_pickle_file_path,new_db_pickle_file_path,checkpoint_file,batch_sizes) 
            print ("Number of batch:", num_batches2, " and each batch have ", batch_size, " rows ")

 # ============*********************************************************************************************************============
            
            start_time = time.time()   # record loop start
            for batch_index in range(num_batches2):
                    

                    FLAG = proxy_flag[batch_index % proxy_count]
                    
                    
                    if FLAG == int(0):
                         proxy = proxy4 # 122
                    if FLAG == int(1):

                        proxy = proxy2  # 123

                    if FLAG == int(2):
                         proxy = proxy3  # 126

                    
                    if FLAG == int(3):
                         proxy = proxy1  # 126

                    
                    print (f"--------Flag: {FLAG} ----proxy {proxy}--------------Start Batch--------------------------------------", batch_index)
                    start_idx = batch_index * batch_size
                    end_idx = start_idx + batch_size
                    current_queries = batch[start_idx:end_idx]
                    
                    

 # ============*********************************************************************************************************============

                    batch_email = {}
                    result_count = 0
                    time_p = 0
                    for query in current_queries:
                        Start_point = Start_point +1
                        last_index = last_index+1
                        final_cnt = int(result_count) + int(g)
                        print(f"time: {time_p} _ last_index:{last_index}  {total_results2}", end="\r") 

                        socketio.emit("log_update", {"logs": f"Total results: {last_index}/{len(unique_companies)} Emails : {total_results2}"})  # Send logs
    
                        try:
                                res = fetch_google_results(query ,proxy,  num_results=5)
                                time.sleep(3)
                                final_result = []
                                links = [item['link'] for item in res if item.get('link')]
                                q = f"email format for {links[0]}"
                                results = process_run(query , q, proxy)
                                log_query_result(log_full_file, proxy,results[:20])

                                try:
                                    final_email =  get_final_email(results, query)
                                    result_count += len(final_email)
                                    company_names = list(final_email.keys())[0]  
                                    final_email = list(final_email.values())[0]  
                                    batch_email[str.lower(company_names)] =  final_email
                                    ll = len(batch_email)
                                    g = g+ll
                                    final_count_emails = final_count_emails+g
                                    total_results2 = int(total_results) + int(result_count)

                                    log_query_result(log_full_file, query, f"-------> {total_results2} --------{final_email}")
                                    # Convert to DataFrame
                                except Exception as e:
                                   
                                    pass    
                        except Exception as e:
                            print(f" Failed to fetch results  '{query}': {e}") 
                            log_query_result(log_full_file, query,e) 
                        time.sleep(1)

                        time_p = time_p+1

                        import tempfile

                        # Step 1: Create a temp file and write the new checkpoint data
                        with tempfile.NamedTemporaryFile('w', delete=False, dir='.', suffix='.tmp') as tmp_file:
                            tmp_file.write(f"{last_index} {output_txt_file} {total_results2}\n")
                            tmp_file.flush()
                            os.fsync(tmp_file.fileno())  # ensure flushed to disk
                            temp_file_name = tmp_file.name

                        # Step 2: Atomically replace the old file
                        os.replace(temp_file_name, checkpoint_file)


                        with open(checkpoint_file, "w") as f:
                            f.write(f"{last_index} {output_txt_file} {total_results2}\n")
                            f.flush() 
                        
                    ####################### Inside Loop End 
                    total_results = int(total_results) + int(result_count)
                    
                    flag = not flag  # Flip the flag after each batch

                    
                    end_time = time.time()
                    elapsed = end_time - start_time
                    
                    print (f"--------------------------End Batch-------took {elapsed:.2f} seconds---------------", batch_index,"\n")

                    try:
                        
                        with open("temp_file.pkl", 'wb') as f:
                         pickle.dump(batch_email, f)
                        try:
                            update_pickle_file(new_db_pickle_file_path, "temp_file.pkl", new_db_pickle_file_path_bckup)
                            update_pickle_file(old_db_pickle_file_path, "temp_file.pkl", old_db_pickle_file_path_bckup)
                            make_backup_db(new_db_pickle_file_path, new_db_pickle_file_path_bckup)
                            make_backup_db(old_db_pickle_file_path, old_db_pickle_file_path_bckup)
                        except:
                            continue

                        df = pd.DataFrame(batch_email.items(), columns=['company', 'email pattern'])
                        # CSV file path
                        csv_path = os.path.join(scrapper_output, f"{file_name}_file.csv")

                        # Append if file exists, else create new with header
                        if os.path.exists(csv_path):
                            df.to_csv(csv_path, mode='a', header=False, index=False)
                        else:
                            df.to_csv(csv_path, index=False)

                    except Exception as e:
                        print(f" Failed to fetch results  '{e}")
                    
                    print ("sleeping for  20 secs")
                    time.sleep(20)
            ####################### Outer Loop End  
            time.sleep(1)
            print ("sleeping for 1sec")
            print ("\n", f"**************************  END Batch:: {start_index}_{end_index}  *********************************")
            
            df = email_creator_app(readfile_path,email_patterns)
            
            missing = df[df["Email"].isna() | (df["Email"].str.strip() == "")]

            email_data = df[df["Email"].notna() & (df["Email"].str.strip() != "")]
            file_name_no_ext = os.path.splitext(os.path.basename(readfile_path))[0]

            filename_csv = f"{email_created_path}//{file_name_no_ext}_new_tool_output.csv"

            email_data.to_csv(filename_csv)

            missing_file_name =   f"{missing_data}//{file_name_no_ext}_new_tool_missing.csv"
            missing.to_csv(missing_file_name)
            rows, columns = df.shape


            total_rows =  batch_row*  (batch_idx+1)
            print ("last_index", last_index)

            

    ####################### Batch finished 
    log_message = f"File processed successfully!"    
    df = pd.DataFrame(batch_email.items(), columns=['company', 'email pattern'])
    df.to_csv(file_name+"_scrapped.csv")
    print (log_message)         
    return jsonify({"log": log_message})


          
            # socketio.emit("log_update", {"logs": f"Total results: {start}/{total_rows}"})  # Send logs

            # print (f"{total_rows} rows completed")

            # df = email_creator_app(file_path,email_patterns)
            # print ("emails created")

            # email_data = df[df["Email"].notna() & (df["Email"].str.strip() != "")]

            #                     # Get file name without extension
            # file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]

            # filename_csv = f"{scrapper_output}//{file_name_no_ext}_generated_emails_output.csv"

            # email_data.to_csv(filename_csv)


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
    app.run(host ='new-tool', port=3000, debug=True)


    