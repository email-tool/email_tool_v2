from database_training.database_process_mutifile import process_files_and_save_output
from database_training.database_process_single_file import process_single_file
from database_training.merger_for_pckl import update_pkl_with_csv
import pandas as pd
from database_training.update_db_manually import update_pickle
from email_creation.create_emails import email_creator_app
import pickle
# Load the pickle file
import os
from pathlib import Path
# Get the current working directory
current_dir = Path.cwd()
print (current_dir)
# Define the folder path relative to the base directory
data_folder = current_dir / "email_creator_app" / "files" / "database_output_files"
# Define the full path to the CSV file

csv_file_path =current_dir  / "email_creator_app" / "open icert 3.78L.xlsx"
base_path =current_dir  / "email_creator_app" / "files"
Source_file_path =current_dir / "database_source_files"
Output_files_path = base_path / "database_output_files"
db_pickle_file_path = base_path / "main_database" / "email_patterns.pkl"

# process_single_file(csv_file_path, Output_files_path)
# # process_files_and_save_output(Source_file_path, Output_files_path)
# update_pkl_with_csv(Output_files_path, db_pickle_file_path)

# E:\EmailTool-V2\Barzaan\database_source_files
# new_csv_file = r'/Users/sumanverma/Documents/Work/Email_tool/company_database/output/Fresno, CA-10000_2024-12-29_output.csv'
# updated_dict = update_pickle(db_pickle_file_path, new_csv_file)
file = csv_file_path
import pickle

with open(db_pickle_file_path, 'rb') as f:
    email_patterns = pickle.load(f)
df = email_creator_app(file,email_patterns)

print (df)

df.to_csv("CreateEmailTest.csv")
# from email_verifier.email_verifier import verify_app

# api_key = '748ad80421514463bb9099b85004b0dd'
# url = 'https://api.zerobounce.net/v2/validate'
# file = r'/Users/sumanverma/Documents/Work/Email_tool/email_creator_app/files/created_emails/Colorado_output.csv'
# df= verify_app(file, api_key)
# print (df)
