

import pandas as pd
import requests
from email_verifier.csv_excel_loader import file_load
# Function to validate email
import requests
import pandas as pd

# Function to validate email
def get_email_status(email, api_key):
    url = f'https://api.zerobounce.net/v2/validate?api_key={api_key}&email={email}'
    response = requests.get(url)
    data = response.json()
    # Check if the response contains the 'status' field
    if 'status' in data:
        return data['status']
    else:
        return 'Error'  # In case the API response is unexpected or there's an error

# Function to get verified data
def get_verified_data(file, api_key):
    processed_data = file_load(file)  # Assuming file_load is a function to load the data
    df = processed_data[:2]  # Assuming you're slicing the first 2 rows (modify as needed)

    # Apply the function to the 'Email' column and create a new 'status' column
    df['status'] = df['Email'].apply(lambda email: get_email_status(email, api_key))
    
    return df



def verify_app(file, api_key):

    # globals.py
    df = get_verified_data(file, api_key)
    return df
