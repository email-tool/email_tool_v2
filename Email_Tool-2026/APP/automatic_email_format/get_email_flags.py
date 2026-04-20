import pandas as pd
import difflib
import re



def extract_emails(text):
    return re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', str(text))
# Apply function to extract emails from each row in the 'snippet' column


def extract_text(value):
    if isinstance(value, str) and value.lower().startswith("what is "):
        return value[9:]  # Remove "what is " (8 characters)
    return value



def extract_domain(email_pattern):
    """Extract domain from the email pattern."""
    match = re.search(r'@([\w.-]+)', str(email_pattern))  # Convert to string (handle NaN)
    return match.group(1) if match else None

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


def get_flags(concatenated_df,col_name):

    concatenated_df.columns = concatenated_df.columns.str.lower()  # Convert all column names to lowercase

    concatenated_df["company"] = concatenated_df["company"].apply(extract_text)
    df = pd.DataFrame()
    # Load CSV
    df = concatenated_df
    df.columns = df.columns.str.lower()  # Convert all column names to lowercase

    # Ensure required columns exist
    if "company" in df.columns and col_name in df.columns:
        # Extract domains and compute similarity
        df["domain"] = df[col_name].apply(extract_domain)
        df["match"] = df.apply(lambda row: similarity_score(row["company"], row["domain"]) if row["domain"] else "N/A", axis=1)


        return df

        print(f"Updated CSV saved to: {output_csv}")
    else:
        print("Error: CSV file must contain 'company' and 'email' columns.")
        return df
