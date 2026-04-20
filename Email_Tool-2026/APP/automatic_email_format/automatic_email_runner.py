import os
import time
import pandas as pd
from datetime import datetime

from automatic_email_format.get_best_email import get_final_email
from automatic_email_format.scarpper_manager import get_email_pattern
import requests
# 2025-12-19 00:13:34] TOTAL EXECUTION TIME: 503.6import requests
import json
import re
import difflib
from datetime import datetime
import pandas as pd

from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("SERPER_API_KEY")
LOG_FILE = os.getenv("LOG_FILE", "serper_email_discovery.log")

if not API_KEY:
    raise ValueError("SERPER_API_KEY not set")


LOG_FILE = "serper_email_discovery.log"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def serper_search(query, num_results=10):
    log(f"SEARCHING: {query}")
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "num": num_results,
        "gl": "us",
        "hl": "en"
    })
    headers = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        log("RAW SERPER RESPONSE RECEIVED")
        return data
    except Exception as e:
        log(f"SERPER API ERROR: {e}")
        return None

# === CONVERT SERPER → YOUR OLD FORMAT ===
def convert_to_old_format(serper_data):
    if not serper_data or 'organic' not in serper_data:
        log("NO ORGANIC RESULTS FROM SERPER")
        return [{'sr_no': 1, 'snippet': 'No results'}]

    results = []
    for i, item in enumerate(serper_data['organic'][:5], start=1):  # Top 5 like your old code
        snippet = item.get('snippet', 'No snippet')
        log(f"   SNIPPET {i}: {snippet}")
        results.append({
            'sr_no': i,
            'snippet': snippet
        })
    return results

# === YOUR ORIGINAL EXTRACTION FUNCTIONS ===
def extract_emails(snippet):
    if not isinstance(snippet, str):
        return []
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
    if emails:
        log(f"   NORMAL EMAILS FOUND: {emails}")
    return emails

def extract_email_format(snippet):
    if not isinstance(snippet, str):
        return []
    pattern = r"email formats:\s*1\.\s*([^()]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    match = re.search(pattern, snippet)
    if match:
        email = match.group(1).strip()
        log(f"   'email formats: 1.' FOUND: {email}")
        return [email]
    return []

def extract_domain(email):
    match = re.search(r'@([\w.-]+)', str(email))
    return match.group(1) if match else None

def similarity_score(company, domain):
    if not domain:
        return "N/A"
    company_clean = re.sub(r'[^a-zA-Z0-9]', '', str(company)).lower()
    domain_clean = re.sub(r'\..*$', '', str(domain)).lower()
    score = difflib.SequenceMatcher(None, company_clean, domain_clean).ratio()
    tag = "High" if score > 0.8 else "Medium" if score > 0.4 else "Low"
    log(f"      SIMILARITY: {score:.3f} → {tag}")
    return tag

# === YOUR ORIGINAL FLATTEN & SELECTION LOGIC (FIXED) ===
def flatten_email_matches(email_data, company_name):
    log(f"\nFLATTENING {len(email_data)} RESULTS FOR: {company_name}")
    flattened = []

    for entry in email_data:
        sr_no = entry.get('sr_no', 1)
        emails = entry.get('extracted_emails', [])
        log(f"   RESULT #{sr_no}: {len(emails)} emails")
        for email in emails:
            domain = extract_domain(email)
            if domain:
                match_tag = similarity_score(company_name, domain)
                flattened.append({
                    'sr_no': sr_no,
                    'email': email,
                    'domain': domain,
                    'company_name': company_name,
                    'match_tag': match_tag
                })

    # Filter only High/Medium
    filtered = [e for e in flattened if e['match_tag'] in ['High', 'Medium']]
    log(f"   FILTERED TO {len(filtered)} HIGH/MEDIUM CANDIDATES")

    if not filtered:
        log("   NO HIGH OR MEDIUM MATCH → NO PATTERN FOUND")
        return None  # ← This was causing NoneType error

    # Priority selection
    log("\nAPPLYING PRIORITY RULES:")
    # Priority 1: High + sr_no 1
    for e in filtered:
        if e['match_tag'] == 'High' and e['sr_no'] == 1:
            log(f"   BEST: High match + sr_no 1 → {e['email']}")
            return e['email']

    # Priority 2: Any High
    for e in filtered:
        if e['match_tag'] == 'High':
            log(f"   BEST: Any High match → {e['email']}")
            return e['email']

    # Priority 3: Medium fallback
    log(f"   BEST: Medium fallback → {filtered[0]['email']}")
    return filtered[0]['email']

# === YOUR get_final_email (FIXED to handle None) ===
def get_final_email(old_format_results, company):
    log(f"\nRUNNING FINAL SELECTION FOR: {company}")

    email_data = []
    for entry in old_format_results:
        emails = extract_email_format(entry['snippet']) + extract_emails(entry['snippet'])
        email_data.append({
            'sr_no': entry['sr_no'],
            'extracted_emails': emails
        })

    best_email = flatten_email_matches(email_data, company)

    if best_email:
        pattern = get_email_pattern(best_email)
        log(f"🎉 FINAL PATTERN FOR {company}: {pattern}")
        return {company: pattern}
    else:
        log(f"❌ NO PATTERN FOUND FOR {company}")
        return {company: "No valid pattern found"}


# === MAIN PIPELINE ===
def discover_with_serper(companies):
    log("="*80)
    log("STARTING EMAIL PATTERN DISCOVERY WITH SERPER.DEV")
    log("="*80)
    
    results = {}
    for company in companies:
        log(f"\nPROCESSING: {company}")
        query = f"what is email format for {company}"
        serper_data = serper_search(query, num_results=10)
        
        if not serper_data:
            results[company] = "Search failed"
            continue

        old_format = convert_to_old_format(serper_data)
        result = get_final_email(old_format, company)
        results.update(result)

    return results

def run_automatic_email(input_file, output_dir, socketio=None, max_companies=None):

    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(input_file)
    df = df[:1600]

    if "Company" not in df.columns:
        raise ValueError("CSV must contain 'Company' column")

    companies = df["Company"].dropna().astype(str).tolist()
    

    if max_companies:
        companies = companies[:max_companies]

    total = len(companies)
    results = {}
    start_time = time.time()

    def emit(msg):
        if socketio:
            socketio.emit("log_update", {"logs": msg})

    emit(f"LOADED {total} COMPANIES")

    for idx, company in enumerate(companies, start=1):
        emit(f"[{idx}/{total}] PROCESSING: {company}")

        try:
            query = f"what is email format for {company}"
            serper_data = serper_search(query, num_results=10)

            if not serper_data:
                results[company] = "Search failed"
                continue

            old_format = convert_to_old_format(serper_data)
            result = get_final_email(old_format, company)
            results.update(result)

        except Exception as e:
            emit(f"[ERROR] {company}: {e}")
            results[company] = "ERROR"

        if idx % 5 == 0:
            elapsed = time.time() - start_time
            emit(f"PROGRESS: {idx}/{total} | {elapsed:.1f}s")

    # SAVE OUTPUT

    # SAVE OUTPUT
    safe_name = os.path.basename(input_file)
    base_name = os.path.splitext(safe_name)[0]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(
        output_dir,
        f"{base_name}_{ts}.csv"
    )

    df_out = pd.DataFrame(list(results.items()), columns=["Company", "Email Pattern"])

    invalid_patterns = ["no valid pattern found", "unknown pattern"]

    df_out = df_out[
        ~df_out["email pattern"]
        .astype(str)
        .str.lower()
        .isin(invalid_patterns)
    ]

    df_out.to_csv(output_csv, index=False)

    total_time = time.time() - start_time
    emit(f"DONE: {total} companies in {total_time:.1f}s")
    emit(f"OUTPUT: {os.path.basename(output_csv)}")


    return output_csv
