import requests
from bs4 import BeautifulSoup
import math
# from duckduckgo_search import DDGS
import time


# https://www.startpage.com/
# Fetch Bing results
def fetch_startpage_results(query, num_results=5):
    language = 'en'
    url = f"https://www.startpage.com/search?q={query}&setlang={language}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    for item in soup.find_all('li', class_='b_algo')[:num_results]:
        title = item.find('h2')
        link = title.find('a')['href'] if title else None
        snippet = item.find('p').text if item.find('p') else None
        if title and link:
            results.append({'title': title.text, 'link': link, 'snippet': snippet})
    # If no results are found, return a single entry with "NA" values
    if not results:
        results.append({'title': 'NA', 'link': 'NA', 'snippet': 'NA'})
    return results



# Fetch Bing results
def fetch_bing_results(query, num_results=10):
    language = 'en'
    # url = f"https://www.bing.com/search?÷q={query}&setlang={language}"
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    for item in soup.find_all('li', class_='b_algo')[:num_results]:
        title = item.find('h2')
        link = title.find('a')['href'] if title else None
        snippet = item.find('p').text if item.find('p') else None
        if title and link:
            results.append({'title': title.text, 'link': link, 'snippet': snippet})
    # If no results are found, return a single entry with "NA" values
    if not results:
        results.append({'title': 'NA', 'link': 'NA', 'snippet': 'NA'})
    return results

# Fetch Yahoo results
def fetch_yahoo_results(query, num_results=30):
    url = f"https://search.yahoo.com/search?p={query}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    for item in soup.find_all('div', class_='Sr')[:num_results]:
        title = item.find('h3')
        link = item.find('a')['href'] if item.find('a') else None
        snippet = item.find('p').text if item.find('p') else None
        if title and link:
            results.append({'title': title.text, 'link': link, 'snippet': snippet})
    # If no results are found, return a single entry with "NA" values
    if not results:
        results.append({'title': 'NA', 'link': 'NA', 'snippet': 'NA'})
    return results


import requests
from bs4 import BeautifulSoup
from googlesearch import search


def fetch_google_results(query, proxy, num_results=5):

    results = list(search(query, num_results=5, proxy =proxy ,  advanced= True) ) # Fetch up to 4 results
    data=[]
    for i, result in enumerate(results, start=5):

        data.append({'title': result.title, 'link': result.url, 'snippet': result.description})
    return data

    # If no results are found, return a single entry with "NA" values
    if not results:
        results.append({'title': 'NA', 'link': 'NA', 'snippet': 'NA'})
        
    return results




# Fetch DuckDuckGo results
# def fetch_duckduckgo_results(query, num_results=5):
#     resultss = DDGS().text(query, max_results=num_results)
#     # Transform the data into the desired format
#     formatted_data = [
#         {
#             'title': item['title'],
#             'link': item['href'],
#             'snippet': item['body']
#         }
#         for item in resultss
#     ]
#     results = []

#     if not formatted_data:
#         results.append({'title': 'NA', 'link': 'NA', 'snippet': 'NA'})
#     else:
#         for i in range(len(formatted_data)): 
#             results.append({'title': formatted_data[i]["title"], 'link': formatted_data[i]["link"], 'snippet': formatted_data[i]["snippet"]})
    
#     return results



# Function to handle retries if an engine fails
def fetch_results_with_retry(query, num_results=5, engines=["DuckDuckGo", "Bing", "Yahoo"]):
    for engine in engines:
        try:
            if engine == "DuckDuckGo":
                return fetch_duckduckgo_results(query, num_results)
            elif engine == "Bing":
                return fetch_bing_results(query, num_results)
            elif engine == "Yahoo":
                return fetch_yahoo_results(query, num_results)
        except Exception as e:
            print(f"Failed to fetch results from {engine} for query '{query}': {e}")
    # If all engines fail, return a result with "NA"
    return [{'title': 'error', 'link': 'error', 'snippet': 'error'}]

# Function to distribute queries across batches
def distribute_queries_across_engines(queries, batch_size):
    search_engines = [ "Bing", "Yahoo"]
    
    num_batches = math.ceil(len(queries) / batch_size)
    all_results = []

    start_time = time.time()  # Start time for entire execution
    print ("Number of batch:", num_batches, " and each batch have ", batch_size, " many rows ")
    for batch_idx in range(num_batches):
        # Start time for this batch
        batch_start_time = time.time()

        # Get queries for the current batch
        start_idx = batch_idx * batch_size
        end_idx = start_idx + batch_size
        current_queries = queries[start_idx:end_idx]
        
        print(f"\nFetching batch {batch_idx + 1}...")

        for query in current_queries:
            try:
                # Try fetching results with retries
                results = fetch_results_with_retry(query, num_results=5)
                # Ensure that we always have at least one result entry for each engine
                if not results:  # If results are empty, append a result with "NA"
                    results.append({'title': 'NA', 'link': 'NA', 'snippet': 'NA'})
                all_results.append({'query': query, 'engine': "Retry", 'results': results})
            except Exception as e:
                print(f"Failed to fetch results for query '{query}': {e}")
                # In case of error, we append the result with "NA" values for this query
                all_results.append({'query': query, 'engine': "Retry", 'results': [{'title': 'error', 'link': 'error', 'snippet': 'error'}]})

        # End time for this batch
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time
        print(f"Batch {batch_idx + 1} completed in {batch_duration:.2f} seconds.")
        
        # Delay of 1 minute after each batch
        print("Waiting for 1 minute before starting the next batch...")
        time.sleep(3)  # Wait for 60 seconds (1 minute)

    # End time for entire execution
    end_time = time.time()
    total_duration = end_time - start_time
    print(f"\nTotal execution time: {total_duration:.2f} seconds.")
    
    return all_results





def get_email_from_snippet(data):
    import pandas as pd
    import re
    from urllib.parse import urlparse
    # Function to extract domain name from URL
    def extract_website(url):
        domain = urlparse(url).netloc
        return domain.split('.')[0] if domain else "Unknown"

    # Function to extract email format from snippet
    def extract_email(snippet):
        match = re.search(r'[\w\.\[\]]+@[\w\.\[\]]+', snippet)  # Extracts email-like patterns
        return match.group(0) if match else "Not Found"

    # Function to extract accuracy from snippet (if mentioned)
    def extract_accuracy(snippet):
        match = re.search(r'(\d{1,3}\.\d+)%', snippet)
        return float(match.group(1)) if match else "Unknown"

    # Creating DataFrame
    records = []
    for entry in data:
        for result in entry['results']:
            text = (entry['query'])
            # Extract text after "email format for"
            company = text.replace("email format for", "").strip()
            website = extract_website(result['link'])
            email = extract_email(result['snippet'])
            accuracy = extract_accuracy(result['snippet'])
            query = company
            records.append({"Company":query,"Website": website, "Email": email, "Accuracy": accuracy})

    df = pd.DataFrame(records)

    # Display DataFrame
    return df



import os
import pickle

def update_pickle_file(old_pickle_path, new_pickle_path, backup_path):
    # Load old pickle
    try:
        if os.path.exists(old_pickle_path):
            with open(old_pickle_path, 'rb') as f:
                old_data = pickle.load(f)
        else:
            raise FileNotFoundError("Main pickle file missing.")
    except Exception as e:
        print(f"⚠️ Failed to load main pickle ({old_pickle_path}): {e}")
        # Attempt to restore from backup
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'rb') as f:
                    old_data = pickle.load(f)
                print(f"🔁 Restored from backup: {backup_path}")
            except Exception as e2:
                print(f"❌ Failed to load backup file: {e2}")
                old_data = {}
        else:
            print("⚠️ No backup found. Starting with empty data.")
            old_data = {}

    # Load new pickle data
    try:
        with open(new_pickle_path, 'rb') as f:
            new_data = pickle.load(f)
    except Exception as e:
        print(f"❌ Failed to load new pickle data: {e}")
        return

    # Update old data with new data (overwrite duplicates)
    old_data.update(new_data)

    # Save safely (atomic)
    temp_file = old_pickle_path + '.tmp'
    try:
        with open(temp_file, 'wb') as f:
            pickle.dump(old_data, f)
        os.replace(temp_file, old_pickle_path)
    except Exception as e:
        print(f"❌ Failed to save updated pickle: {e}")



import os
import re
import tempfile
from datetime import datetime



import os, re
from datetime import datetime

import os
import re

import re, os

def get_latest_log_file(log_path):
    """
    Find the latest 'logs_for_tracking*.txt' file in the given directory.
    Prioritizes today's file (2025-08-26), otherwise uses modification time.
    """

    log_dir = os.path.dirname(log_path)
    today_file = os.path.join(log_dir, 'logs_for_tracking2025-08-26.txt')
    latest_file = None
    latest_mtime = None

    # Check if today's file exists
    if os.path.exists(today_file):
        print("📄 Latest log file:", today_file)
        return today_file

    # If today's file doesn't exist, find the latest by modification time
    for fname in os.listdir(log_dir):
        if re.match(r"logs_for_tracking\d{4}-\d{2}-\d{2}\.txt", fname):
            full_path = os.path.join(log_dir, fname)
            file_mtime = os.path.getmtime(full_path)

            if latest_mtime is None or file_mtime > latest_mtime:
                latest_mtime = file_mtime
                latest_file = full_path

    print("📄 Latest log file:", latest_file)
    return latest_file


   





import os, re, tempfile

def recover_from_logs(log_file, output_txt_file, checkpoint_file):
    last_company = None
    total_results = 0

    # --- Step 1: read log file backwards ---
    with open(log_file, "r", encoding="latin1") as f:
        for line in reversed(f.readlines()):
            # Capture last "RESULTS: -------> nnnn"
            match_results = re.search(r"RESULTS:\s*------->\s*(\d+)", line)
            if match_results and total_results == 0:
                total_results = int(match_results.group(1))

            # Capture last company
            if "QUERY:" in line and last_company is None:
                match = re.search(r"QUERY:\s*(.*?)(?:\||RESULTS:|$)", line)
                if match:
                    last_company = match.group(1).strip()

            if last_company and total_results:
                break  # we got both → stop scanning

    if not last_company:
        print("⚠️ No company found in logs. Starting from index 0.")
        return 0, output_txt_file, 0

    # --- Step 2: find index in output file ---
    last_index = 0
    with open(output_txt_file, "r", encoding="latin1") as f:
        for line in f:
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                idx, company = parts
                if company.strip().lower() == last_company.lower():
                    last_index = int(idx)
                    break

    # --- Step 3: relative file path (folder + filename only) ---
    folder = os.path.basename(os.path.dirname(output_txt_file))
    filename = os.path.basename(output_txt_file)
    relative_name = os.path.join(folder, filename) if folder else filename

    # --- Step 4: write checkpoint safely ---
    dir_name = os.path.dirname(checkpoint_file) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, suffix=".tmp") as tmp_file:
        tmp_file.write(f"{last_index} {relative_name} {total_results}\n")
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        temp_file_name = tmp_file.name

    os.replace(temp_file_name, checkpoint_file)

    return last_index, relative_name, total_results


def recover_with_latest(log_dir, output_txt_file, checkpoint_file):
    latest_log = get_latest_log_file(log_dir)
    if not latest_log:
        raise FileNotFoundError(f"No log files found in {log_dir}")

    print(f"📄 Using latest log file: {os.path.basename(latest_log)}")

    return recover_from_logs(latest_log, output_txt_file, checkpoint_file)

