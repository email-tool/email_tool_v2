import os
import time
import json
import re
import difflib
import random
import requests
import pandas as pd
from datetime import datetime

from automatic_email_format.scarpper_manager import get_email_pattern


# =========================================================
# LOGGER
# =========================================================
def log(message, log_file="serper_email_discovery.log"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# =========================================================
# FILE READERS (CSV / EXCEL)
# =========================================================
def read_input_file(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file type. Use CSV or Excel.")


def save_output_file(df: pd.DataFrame, input_file: str, output_dir: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(input_file))[0]
    ext = os.path.splitext(input_file)[1].lower()

    output_path = os.path.join(output_dir, f"{base}_serper_{ts}{ext}")

    if ext == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_excel(output_path, index=False)

    return output_path


# =========================================================
# SERPER SEARCH
# =========================================================
def serper_search(query: str, api_key: str, num_results: int = 10):
    url = "https://google.serper.dev/search"

    payload = {
        "q": query,
        "num": num_results,
        "gl": "us",
        "hl": "en"
    }

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"❌ SERPER ERROR ({api_key[-4:]}): {e}")
        return None


# =========================================================
# PARSING LOGIC
# =========================================================
def convert_to_old_format(serper_data):
    if not serper_data or "organic" not in serper_data:
        return [{"sr_no": 1, "snippet": "No results"}]

    return [
        {"sr_no": i + 1, "snippet": item.get("snippet", "")}
        for i, item in enumerate(serper_data["organic"][:5])
    ]


def extract_emails(text):
    return re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", str(text))


def extract_domain(email):
    match = re.search(r"@([\w.-]+)", str(email))
    return match.group(1) if match else None


def similarity_score(company, domain):
    if not domain:
        return "Low"

    company_clean = re.sub(r"[^a-zA-Z0-9]", "", company.lower())
    domain_clean = re.sub(r"\..*", "", domain.lower())

    score = difflib.SequenceMatcher(None, company_clean, domain_clean).ratio()

    if score > 0.8:
        return "High"
    if score > 0.4:
        return "Medium"
    return "Low"


def select_best_email(old_results, company):
    candidates = []

    for r in old_results:
        for email in extract_emails(r["snippet"]):
            domain = extract_domain(email)
            tag = similarity_score(company, domain)

            if tag in ("High", "Medium"):
                candidates.append((tag, r["sr_no"], email))

    for tag, sr, email in candidates:
        if tag == "High" and sr == 1:
            return email

    for tag, _, email in candidates:
        if tag == "High":
            return email

    return candidates[0][2] if candidates else None


def get_final_pattern(serper_data, company):
    old_format = convert_to_old_format(serper_data)
    email = select_best_email(old_format, company)

    if not email:
        return "No valid pattern found"

    return get_email_pattern(email)


# =========================================================
# MAIN PUBLIC FUNCTION (CSV + EXCEL + UNIQUE + SHUFFLE)
# =========================================================
def run_serper_with_multiple_keys(
    input_file: str,
    output_dir: str,
    api_keys: list,
    rows_per_key: int = 2500
):
    """
    - Supports CSV & Excel
    - Removes duplicate companies
    - Shuffles company list
    - Each API key processes `rows_per_key` rows
    """

    os.makedirs(output_dir, exist_ok=True)

    # -------- READ INPUT --------
    df = read_input_file(input_file)

    if "Company" not in df.columns:
        raise ValueError("Input file must contain 'Company' column")

    # -------- UNIQUE + CLEAN + SHUFFLE --------
    companies = (
        df["Company"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    random.shuffle(companies)

    max_rows = len(api_keys) * rows_per_key
    companies = companies[:max_rows]

    log(f"🔑 API KEYS: {len(api_keys)}")
    log(f"📊 UNIQUE COMPANIES (SHUFFLED): {len(companies)}")

    results = {}
    global_index = 0

    # -------- PROCESS --------
    for key_index, api_key in enumerate(api_keys, start=1):
        start = (key_index - 1) * rows_per_key
        end = start + rows_per_key
        batch = companies[start:end]

        log(f"➡️ USING API KEY {key_index}/{len(api_keys)} | ROWS: {len(batch)}")

        for company in batch:
            global_index += 1
            log(f"[{global_index}] {company}")

            query = f"what is email format for {company}"
            serper_data = serper_search(query, api_key)

            if not serper_data:
                results[company] = "Search failed"
                continue

            results[company] = get_final_pattern(serper_data, company)

    # -------- SAVE OUTPUT --------
    df_out = pd.DataFrame(results.items(), columns=["Company", "Email Pattern"])

    df_out = df_out[
        ~df_out["Email Pattern"]
        .astype(str)
        .str.lower()
        .isin(["no valid pattern found", "unknown pattern"])
    ]

    output_path = save_output_file(df_out, input_file, output_dir)

    log(f"✅ COMPLETED → {output_path}")
    return output_path
