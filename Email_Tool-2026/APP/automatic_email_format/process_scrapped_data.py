import requests
from bs4 import BeautifulSoup
from googlesearch import search

def fetch_google_results(query, company_name,proxy, num_results=8):
    results = list(search(query, num_results=5,proxy =proxy, advanced= True) ) # Fetch up to 4 results
    
    if not results:
        return [{'sr_no': 1, 'title': 'NA', 'link': 'NA', 'snippet': 'NA','company_name':company_name}]
    
    data = []
    for i, result in enumerate(results, start=1):
        data.append({
            'sr_no': i,
            'snippet': result.description
        })
    
    return data

import re
import difflib

def extract_domain(email):
    """Extract domain from a single email."""
    match = re.search(r'@([\w.-]+)', str(email))
    return match.group(1) if match else None

def similarity_score(company, domain):
    """Compare similarity between company name and domain."""
    company_clean = re.sub(r'[^a-zA-Z0-9]', '', str(company)).lower()
    domain_clean = re.sub(r'\..*$', '', str(domain)).lower()  # Remove TLD (.com, .io)

    score = difflib.SequenceMatcher(None, company_clean, domain_clean).ratio()

    if score > 0.8:
        return "High"
    elif score > 0.4:
        return "Medium"
    else:
        return "Low"

def evaluate_email_matches(email_data, company_name):
    """
    Given a list of dicts like [{'sr_no': 1, 'extracted_emails': [...]}, ...]
    Add 'email_matches' with [{'email': ..., 'domain': ..., 'match': ...}]
    """
    output = []

    for entry in email_data:
        sr_no = entry.get('sr_no')
        emails = entry.get('extracted_emails', [])
        email_matches = []

        for email in emails:
            domain = extract_domain(email)
            if domain:
                match = similarity_score(company_name, domain)
                email_matches.append({
                    'email': email,
                    'domain': domain,
                    'match': match
                })

        output.append({
            'sr_no': sr_no,
            'email_matches': email_matches
        })

    return output

def flatten_email_matches(email_data, company_name):
    """
    Returns a list of dictionaries with:
    sr_no, email, domain, company_name, match_tag
    """
    flattened = []

    for entry in email_data:
        sr_no = entry.get('sr_no')
        emails = entry.get('extracted_emails', [])

        for email in emails:
            domain = extract_domain(email)
            if domain:
                match = similarity_score(company_name, domain)
                flattened.append({
                    'sr_no': sr_no,
                    'email': email,
                    'domain': domain,
                    'company_name': company_name,
                    'match_tag': match
                })

    return flattened


def select_best_email(email_data):
    """
    Given a list of email match dictionaries for a single company,
    return the best email using updated logic.
    """
    # Remove all 'Low' entries
    filtered = [e for e in email_data if e['match_tag'] in ['High', 'Medium']]
    
    if not filtered:
        return {
            'company_name': email_data[0]['company_name'] if email_data else None,
            'best_email': None
        }

    # Priority 1: High with sr_no 1
    for e in filtered:
        if e['match_tag'] == 'High' and e['sr_no'] == 1:
            return {
                'company_name': e['company_name'],
                'best_email': e['email']
            }

    # Priority 2: Any other High
    for e in filtered:
        if e['match_tag'] == 'High':
            return {
                'company_name': e['company_name'],
                'best_email': e['email']
            }

    # Priority 3: Any Medium
    return {
        'company_name': filtered[0]['company_name'],
        'best_email': filtered[0]['email']
    }
def extract_emails(snippet):
    
    if not isinstance(snippet, str):
        return []

    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)  # Extracts actual emails
   
    return emails if emails else []



 #Function to extract full email format after "email formats: 1."
def extract_email_format(snippet):
    
    if not isinstance(snippet, str):
        return []

    pattern = r"email formats:\s*1\.\s*([^()]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    match = re.search(pattern, snippet)

    

    return [match.group(1).strip()] if match else []

def process_run(company, query, proxy):
        # company = 'aarp colorado'
        # query = f"what is email format for {company}"
        data = fetch_google_results(query, company,proxy, num_results=5)


        final_output = []

        for result in data:
            emails = extract_email_format(result['snippet']) + extract_emails(result['snippet']) #extract_email_format(result['snippet']) 
           
            final_output.append({
                'sr_no': result['sr_no'],
                'extracted_emails': emails
            })

        output_data = flatten_email_matches(final_output, company) 

        return data


        # best = select_best_email(output_data)
        # print(best)

# process_run('new jersey state police', 'email format for new jersey state police')
