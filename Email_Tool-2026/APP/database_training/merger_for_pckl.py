import os
import pandas as pd
import pickle





def update_pkl_with_csv(file_name, output_pkl_path):
    # Initialize an empty dictionary or load existing data from the .pkl file

        output_dir = os.path.dirname(output_pkl_path)
       
        if file_name.endswith('.csv'):

            print(f"Processing file: {file_name}")

            # Step 1: Load the pickle file
            pickle_file = output_pkl_path

            with open(pickle_file, "rb") as file:
                email_dict = pickle.load(file)

            # Read the CSV file into a DataFrame
            try:
                new_data = pd.read_csv(file_name)
           
                # Step 3: Convert the new CSV data into a dictionary
                new_dict = {}
                for _, row in new_data.iterrows():
                    company = row['company']
                    email_format = row['email pattern']
                    new_dict[company] = email_format

                # Step 4: Update the existing dictionary with the new data
                email_dict.update(new_dict)

                # Step 5: Save the updated dictionary back to the pickle file
                with open(pickle_file, "wb") as file:
                    pickle.dump(email_dict, file)

                print(f"Pickle file updated")
            except Exception as e:
                print(f"Error reading file {file_name}: {e}")











def update_pkl_with_folder_csv(folder_path, output_pkl_path):
    # Initialize an empty dictionary or load existing data from the .pkl file

    output_dir = os.path.dirname(output_pkl_path)

    # Iterate through all files in the folder
    for file_name in os.listdir(folder_path):
       
        if file_name.endswith('.csv'):
            file_path = os.path.join(folder_path, file_name)
            print(f"Processing file: {file_path}")

            # Step 1: Load the pickle file
            pickle_file = output_pkl_path

            with open(pickle_file, "rb") as file:
                email_dict = pickle.load(file)

            # Read the CSV file into a DataFrame
            try:
                new_data = pd.read_csv(file_path)
           
                # Step 3: Convert the new CSV data into a dictionary
                new_dict = {}
                for _, row in new_data.iterrows():
                    company = row['company']
                    email_format = row['email pattern']
                    new_dict[company] = email_format

                # Step 4: Update the existing dictionary with the new data
                email_dict.update(new_dict)

                # Step 5: Save the updated dictionary back to the pickle file
                with open(pickle_file, "wb") as file:
                    pickle.dump(email_dict, file)

                print(f"Pickle file updated")
                print(f"Deleted file: {file_path}")
                os.remove(file_path)
             

            except Exception as e:
                print(f"Error reading file {file_name}: {e}")
                continue


    print("All files processed.")
