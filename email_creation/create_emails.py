import pandas as pd
import pickle
from email_creation.reader_email import reader




def create_emails2(row, email_patterns):
    

    company_name = row['Company'].strip()  # Remove leading/trailing spaces
    first_name = row['First Name'].strip()
    last_name = row['Last Name'].strip()

    # Get the email format for the company from the dictionary
    formats = email_patterns.get(company_name.lower())  # Direct lookup instead of looping
    # print (company_name.lower())
    # print (formats)
   
    if not formats:
        return None  # No matching email pattern

    try:


        email_pattern, domain = formats.split('@', maxsplit=1)  # Extract format and domain
      
       
    except Exception as e:
           print(f"Error processing file: {formats.split('@', maxsplit=1)} ----- {str(e)}")
           return None

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

    # Generate email if pattern exists
    email_local_part = patterns.get(email_pattern)

    return f"{email_local_part}@{domain}" if email_local_part else None




def email_creator_app(file,email_patterns):

    try:
        processed_data = reader(file)  # Read data from file
        processed_data['Email'] = ""
        
        # Apply email creation function
    
        processed_data['Email'] = processed_data.apply(lambda row: create_emails2(row, email_patterns), axis=1)
        print ("email generated")
    except Exception as e:
      print(f" Failed email_creator_app ': {e}") 
    return processed_data