from pathlib import Path
import os
import pandas as pd
import re

def sanitize_username(username):
    return re.sub(r'[^\w\s-]', '', username).strip().lower()

def create_directory(name):
    path = Path("")
    parent_dir = path.parent.absolute()
    # Directory
    directory = name
    
    # Path
    path = os.path.join(parent_dir, directory)
    print ("path:", path)
    try:    
        os.mkdir(path)
        print("Directory '% s' created" % directory)
    except:
        print ("directory exists")


def generate_email(file):
    print(os.path.basename(file))

    create_directory("output")
    print ("somenthinh")

    file_name = os.path.basename(file).split(".")
    data = pd.read_excel(file)
    data['email']= "NA"
    base_name= f".//output//{file_name[0]}"
    print (base_name)
    data.to_csv(f"{base_name}_output.csv")
    data.to_csv(f"{base_name}_missing.csv")
    data.to_csv(f"{base_name}_missing_companies.csv")
   

    # Open the file in write mode
    with open(f"{base_name}_summary.txt", 'w') as file:
        # Write content to the file
        file.write("Emails are generated.")   