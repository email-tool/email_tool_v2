import os
import pandas as pd
from datetime import datetime
from database_training.email_format_extracter  import get_email_formats



def process_files_and_save_output(input_folder, output_folder):
    try:
        # Get the current date for the output filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if the output folder exists; if not, create it
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Initialize an empty DataFrame to store merged data
        merged_df = pd.DataFrame()

        # Iterate through all files in the input folder
        for file_name in os.listdir(input_folder):
            file_path = os.path.join(input_folder, file_name)
            
            # Get the file name without the extension
            file_name_only = os.path.splitext(file_name)[0]

            print (f"--------------------------------------------****************file name: {file_name_only}********************")

            # Process CSV and Excel files only
            if file_name.endswith('.csv'):
                try:
                    processed_data= get_email_formats(file_path)
                    # Get the number of rows
                    num_rows = len(processed_data)
                    print(f"Number of rows: {num_rows}")
                    output_file_name = f"{file_name_only}_{current_date}_output.csv"
                    output_file_path = os.path.join(output_folder, output_file_name)
                    processed_data.to_csv(output_file_path, index=False)


                except Exception as e:
                    print(f"Error reading CSV file {file_name}: {e}")
                    continue
            elif file_name.endswith(('.xls', '.xlsx')):
                try:
                    processed_data= get_email_formats(file_path)
                    output_file_name = f"{file_name_only}_{current_date}_output.csv"
                    output_file_path = os.path.join(output_folder, output_file_name)
                    processed_data.to_csv(output_file_path, index=False)
                      # Get the number of rows
                    num_rows = len(processed_data)
                    print(f"Number of rows: {num_rows}")
       
                except Exception as e:
                    print(f"Error reading Excel file {file_name}: {e}")
                    continue
            else:
                print(f"Skipped non-supported file: {file_name}")
                continue



        # Check if the merged DataFrame has data
        if merged_df.empty:
            print("No data was processed. Exiting.")
            return



        print(f"Merged data saved to: {output_file_path}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

