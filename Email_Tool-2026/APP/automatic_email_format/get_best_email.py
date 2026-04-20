import pandas as pd
import difflib
import re
from automatic_email_format.scarpper_manager import get_email_pattern

def similarity_score(company, domain):
    """Compare similarity between company name and domain."""
    company_clean = re.sub(r'[^a-zA-Z0-9]', '', str(company)).lower()
    domain_clean = re.sub(r'\..*$', '', str(domain)).lower()  # Remove TLD (.com, .edu)

    score = difflib.SequenceMatcher(None, company_clean, domain_clean).ratio()

    if score > 0.8:
        return "High"
    elif score > 0.4:
        return "Medium"
    else:
        return "Low"
    

# def select_best_email(data_list):
    # company_name, data_list = data_dict 
    # Apply selection rule
    selected = None
    # Priority 1: sr_no1 if High
    for entry in data_list:
        if entry['sr_no'] == 'sr_no1' and entry['flag'] == 'High':
            selected = entry
            break

    # Priority 2: sr_no2 if High
    if not selected:
        for entry in data_list:
    
            if entry['sr_no'] == 'sr_no2' and entry['flag'] == 'High':
                selected = entry
                break

    # Priority 3: Any High
    if not selected:
        for entry in data_list:
            if entry['flag'] == 'High':
                selected = entry
                break

    # Priority 4: Any Medium
    if not selected:
        for entry in data_list:
            if entry['flag'] == 'Medium':
                selected = entry
                break
    return selected

def select_best_email(data_list):
    selected = None

    # Step 1: Check first entry
    if len(data_list) > 0 and data_list[0]['flag'] in ['High', 'Medium']:
        selected = data_list[0]

    # Step 2: Check second entry if first was Low
    elif len(data_list) > 1 and data_list[1]['flag'] in ['High', 'Medium']:
        selected = data_list[1]

    # Step 3: Any High
    else:
        for entry in data_list:
            if entry['flag'] == 'High':
                selected = entry
                break

    return selected


def get_selected_email(data):
    # Keep only the first email per sr_no
    for sr_no, emails in data['result_dict'].items():
        data['result_dict'][sr_no] = emails[0] if emails else ""
    # Apply get_email_pattern to each value
    for sr_no, email in data['result_dict'].items():
        pattern = get_email_pattern(email)
        data['result_dict'][sr_no] = pattern
    # Extract flag for each entry
    results = []
    company_name = data['company']
    for sr_no, email in data['result_dict'].items():
        if '@' in email:
            domain = email.split('@')[1]
            flag = similarity_score(company_name, domain)
        else:
            flag = "NA"
        results.append({'sr_no': sr_no, 'email': email, 'flag': flag})
    return company_name, results


import ast

def extract_results_lists(file_path):
    extracted_entries = []

    with open(file_path, "r", encoding="utf-8") as file:
        buffer = ""
        current_query = None
        for line in file:
            line = line.strip()
            if "| QUERY:" in line:
                # New block starts, extract the QUERY company name
                try:
                    query_part = line.split("| QUERY:")[1].split("| RESULTS:")[0].strip()
                    current_query = query_part
                    buffer = line  # start buffer with current line
                except Exception as e:
                    print(f"Error extracting query: {e}")
                    current_query = None
                    buffer = ""
            else:
                buffer += line  # continue buffering

            if "| RESULTS:" in buffer:
                try:
                    parts = buffer.split("| RESULTS:")
                    json_like = parts[1].strip()
                    # Ensure we only try to parse complete list structures
                    if json_like.startswith("[") and json_like.endswith("]"):
                        parsed = ast.literal_eval(json_like)
                        extracted_entries.append({
                            'company': current_query,
                            'results': parsed
                        })
                    buffer = ""  # reset buffer
                except Exception as e:
                    print(f"Error parsing buffer: {e}")
                    buffer = ""  # reset on error too

    return extracted_entries


from automatic_email_format.process_scrapped_data import extract_email_format, extract_emails

def run(result_dict1):
    company_name, output_results = get_selected_email(result_dict1)
    selected_email_output = select_best_email(output_results)
    return company_name, selected_email_output


def get_final_email(results, company):
    result_dict = {}
    for res in results:
        sr_no = res.get('sr_no')
        snippet = res.get('snippet', '')
        emails = extract_email_format(snippet) + extract_emails(snippet)
        result_dict[f'sr_no{sr_no}'] = emails
    final_result = []
    final_result.append({
        'company': company,
        'result_dict': result_dict})
    company_name, email_sel= run(final_result[0])
    final_outcome = {}
    final_outcome[company_name] = email_sel['email']
    return final_outcome


import pickle
import os
# Step 3: New data to add or update
import os
import pickle
import csv
def update_pickle_file(old_pickle_path, new_data_path, key_column='Key', value_column='Value'):

    # Load old pickle data
    if os.path.exists(old_pickle_path):
        with open(old_pickle_path, 'rb') as f:
            old_data = pickle.load(f)
    else:
        old_data = {}

    # Load new data
    if new_data_path.endswith('.pkl'):
        with open(new_data_path, 'rb') as f:
            new_data = pickle.load(f)

    elif new_data_path.endswith('.csv'):
        if not key_column or not value_column:
            raise ValueError("For CSV input, 'key_column' and 'value_column' must be provided.")

        new_data = {}
        with open(new_data_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row[key_column]
                value = row[value_column]
                new_data[key] = value

    else:
        raise ValueError("Unsupported file format. Only .pkl and .csv are supported.")

    # Merge data
    old_data.update(new_data)




    # Save safely (atomic)
    temp_file = old_pickle_path + '.tmp'
    with open(temp_file, 'wb') as f:
        pickle.dump(old_data, f)
    os.replace(temp_file, old_pickle_path)

    print(f"✅ Pickle updated and saved: {old_pickle_path}")