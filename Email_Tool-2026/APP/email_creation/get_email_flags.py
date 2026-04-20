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


def get_flags(concatenated_df, col_name):
    # Store original column names
    original_columns = concatenated_df.columns  

    # Convert all column names to lowercase for processing
    concatenated_df.columns = concatenated_df.columns.str.lower()  

    print(concatenated_df.columns)

    # Process "company" column
    concatenated_df["company"] = concatenated_df["company"].apply(extract_text)

    # Ensure required columns exist
    if "company" in concatenated_df.columns and col_name.lower() in concatenated_df.columns:
        # Extract domains and compute similarity
        concatenated_df["domain"] = concatenated_df[col_name.lower()].apply(extract_domain)
        concatenated_df["match"] = concatenated_df.apply(
            lambda row: similarity_score(row["company"], row["domain"]) if row["domain"] else "N/A", axis=1
        )

        # Restore original column names
        concatenated_df.columns = original_columns  

        return concatenated_df
    else:
        print("Error: CSV file must contain 'company' and the specified column.")
        return concatenated_df
