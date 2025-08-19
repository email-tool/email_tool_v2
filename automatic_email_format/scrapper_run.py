   
from automatic_email_format.scarpper_manager import scrapper_manager 
from automatic_email_format.get_email_flags import get_flags
import pandas as pd
import time,os,requests

def app_run(csv_file,db_pickle_file_path,new_pickle_file_path, scrapper_output):

        file_name = os.path.splitext(os.path.basename(csv_file))[0]
        output_txt_file = file_name + ".txt"
        output_txt_file = output_txt_file.replace(" ","")
        checkpoint_file = file_name+"checkpoint.txt"
        checkpoint_file = checkpoint_file.replace(" ","")

        # create text file from missing data with conpany name and index
        df = pd.read_csv(csv_file)

        unique_companies = df["Company"].dropna().unique()  # Assuming 'company_name' is the column name
       
        # Write unique company names to the output text file with index
        with open(output_txt_file, "w") as f:
            for i, company in enumerate(unique_companies, start=0):
                f.write(f"{i} {company}\n")

        with open(output_txt_file, "r" ) as file:
            company_list = [line.strip().split(maxsplit=1)[1] for line in file if line.strip()]


        # Determine the starting index from the checkpoint file
        if os.path.exists(checkpoint_file):

            print ("existing file:", checkpoint_file)

            with open(checkpoint_file, "r") as f:
                last_index, last_file = f.readline().strip().split()
                last_index = int(last_index)
        else:
            last_index = 0
            with open(checkpoint_file, "w") as f:
                f.write(f"{last_index} {output_txt_file}\n")
        print ("last_index:", last_index)
        # Define batch size
        BATCH_SIZE =6500

        queries = company_list[last_index:last_index+BATCH_SIZE]
        # Get the number of full batches
        num_batches = len(queries) // BATCH_SIZE  # Number of complete batches
        remainder = len(queries) % BATCH_SIZE  # Remaining elements in an extra batch (if any)

        # Iterate over batches
        for batch_idx in range(num_batches + (1 if remainder > 0 else 0)):  # Include remainder batch
            start_index = batch_idx * BATCH_SIZE
            end_index = min(start_index + BATCH_SIZE, len(queries))  # Avoid exceeding list size
            batch = queries[start_index:end_index]

            print (f"Batch:: {start_index}_{end_index}")

            # Print batch details
            namefile = f"{scrapper_output}/Batch{start_index}_{end_index}__3__AprSCRAPPER_"
            # df_raw= scrapper_manager(queries[start_index:end_index],namefile, last_index, output_txt_file,db_pickle_file_path,new_pickle_file_path,checkpoint_file) 
            time.sleep(1)