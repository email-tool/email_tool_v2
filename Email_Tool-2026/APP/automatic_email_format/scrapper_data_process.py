import pandas as pd
import re
from urllib.parse import urlparse
import pandas as pd
import os
import re
# Input dictionary
def get_email_pattern(EMAIL):    
    names = [
        {"first": "john", "last": "smith"},
        {"first": "jane", "last": "doe"},
        {"first": "john", "last": "doe"},
        {"first": "first", "last": "last"}
    ]
    

    email = EMAIL.split("@")[0].strip().lower()

    for name in names:
        first_name = name["first"]
        last_name = name["last"]
        patterns = {
                # 1. Full Name Variations
                "FirstNameLastName": f"{first_name}{last_name}",
                "FirstName.LastName": f"{first_name}.{last_name}",
                "FirstName_LastName": f"{first_name}_{last_name}",
                "FirstName-LastName": f"{first_name}-{last_name}",

                "LastNameFirstName": f"{last_name}{first_name}",
                "LastName.FirstName": f"{last_name}.{first_name}",
                "LastName_FirstName": f"{last_name}_{first_name}",
                "LastName-FirstName": f"{last_name}-{first_name}",

                # 2. First Initial + Last Name
                "FirstName1LastName": f"{first_name[0]}{last_name}",
                "FirstName1.LastName": f"{first_name[0]}.{last_name}",
                "FirstName1_LastName": f"{first_name[0]}_{last_name}",
                "FirstName1-LastName": f"{first_name[0]}-{last_name}",

                # 3. Last Initial + First Name
                "LastName1FirstName": f"{last_name[0]}{first_name}",
                "LastName1.FirstName": f"{last_name[0]}.{first_name}",
                "LastName1_FirstName": f"{last_name[0]}_{first_name}",
                "LastName1-FirstName": f"{last_name[0]}-{first_name}",

                # 4. First Name + Last Initial
                "FirstNameLastName1": f"{first_name}{last_name[0]}",
                "FirstName.LastName1": f"{first_name}.{last_name[0]}",
                "FirstName_LastName1": f"{first_name}_{last_name[0]}",
                "FirstName-LastName1": f"{first_name}-{last_name[0]}",

                # 5. Last Name + First Initial
                "LastNameFirstName1": f"{last_name}{first_name[0]}",
                "LastName.FirstName1": f"{last_name}.{first_name[0]}",
                "LastName_FirstName1": f"{last_name}_{first_name[0]}",
                "LastName-FirstName1": f"{last_name}-{first_name[0]}",


                # 7. First initial + Last Initial
                "FirstName1LastName1": f"{first_name[0]}{last_name[0]}",
                "FirstName1.LastName1": f"{first_name[0]}.{last_name[0]}",
                "FirstName1_LastName1": f"{first_name[0]}_{last_name[0]}",
                "FirstName1-LastName1": f"{first_name[0]}-{last_name[0]}",


                # 6. Only First Name, Last Name, Initials
                "FirstName": first_name,
                "LastName": last_name,
                "FirstName1": first_name[0],
                "LastName1": last_name[0]
            }

        for pattern_name, pattern in patterns.items():
            if pattern == email:
                return pattern_name
    return "No matching pattern found"
# Function to extract email format from snippet


def extract_email(snippet):
    match = re.search(r'[\w\.\[\]]+@[\w\.\[\]]+', snippet)  # Extracts email-like patterns
    return match.group(0) if match else "Not Found"
# Function to extract accuracy from snippet (if mentioned)
def extract_accuracy(snippet):
    match = re.search(r'(\d{1,3}\.\d+)%', snippet)
    return float(match.group(1)) if match else "Unknown"
# Function to extract domain name from URL
def extract_website(url):
    try:
        domain = url.split("//")[1]
        g = domain.split('.')
        g = g[0]+g[1]
    except:
        g = "NA"
    return g if g else "Unknown"
def get_domain(email):

    try:
        domain = email.split('@')[1]
    except:
        domain ="NA"
    return domain



# Assuming df is your dataframe and 'snippet' is the column name
def extract_text(text):
    keyword = 'for'
    cleaned_text = text.replace("what is email format for ", "")
    cleaned_text = cleaned_text.replace("what is ", "")
    return cleaned_text

# combined_df["Company"] = combined_df["Company"]
# Assuming df is your dataframe and 'snippet' is the column name
def extract_emails(text):
    return re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', str(text))


def createCSV(data,name):
    # Creating DataFrame
    records = []
    for entry in data:
        for result in entry['results']:
            text = (entry['query'])
            # Extract text after "email format for"
            company = text.replace("what is email format for", "").strip()
            company = company.replace("+", " ").strip()
            website = extract_website(result['link'])
            engine = (entry['engine'])
            email = extract_emails(result['snippet'])
            accuracy = extract_accuracy(result['snippet'])
            
            snippet = result['snippet']
            query = company
            records.append({"company":query,"Website": website, "Email": email, "Engine":engine, "Accuracy": accuracy, "Snippet": snippet})

    df = pd.DataFrame(records)
    df["email pattern"] = df["Email"].apply(get_email_pattern)
    df.to_csv(name)
    return df



def get_emailPattern_flags(df):
    print (df.head(1))
    combined_df = df.rename(columns={"company": "Company"})
    combined_df["Company"] = combined_df["Company"].apply(extract_text)
    combined_df = combined_df.dropna(subset=['Snippet'])  # Removes NaN
    combined_df['email'] = combined_df['Snippet'].apply(lambda x: extract_emails(x))
    combined_df['email_list'] = combined_df['Snippet'].apply(lambda x: extract_emails(x))
    combined_df["email"] = combined_df["email_list"].apply(lambda x: x[0] if isinstance(x, list) and x else "NA")
    combined_df = combined_df [ combined_df["email"] != "NA"]
    combined_df["email_format"] = combined_df["email"].apply(get_email_pattern) + "@" + combined_df["email"].apply(get_domain)
    df_extracted_emails = combined_df[['Company', 'Accuracy', 'Website' , 'Engine',  'email','email_list', 'email_format']]
    condition = "No matching pattern found"
    version2 = df_extracted_emails[~df_extracted_emails["email_format"].str.contains(condition, na=False)]
    version2 = version2[['Company', 'Accuracy', 'Website', 'Engine', 'email', 'email_list', 'email_format']].rename(
        columns={"Company": "company", "email_format": "email pattern"}
    )
    # Group by 'Company' and keep the first occurrence
    version2 = version2.groupby("company", as_index=False).first()
    version2["company"] = version2["company"].str.strip()
    version2= version2[['company', 'email pattern']]
    version2.to_csv("OnlyEmailPatterns_1march.csv")
    print (version2.shape)
    print (version2.head())
    return version2