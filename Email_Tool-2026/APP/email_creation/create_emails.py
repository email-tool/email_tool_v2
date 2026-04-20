import pandas as pd
import pickle
from email_creation.reader_email import reader


# ✅ NEW: normalize UI/manual patterns to backend-supported patterns
def normalize_pattern(pattern):
    if not pattern:
        return pattern

    pattern = pattern.strip()

    alias_map = {
        # UI → backend mappings
        "FirstName_1letterLastName": "FirstInitialLastName",
        "FirstName_1letter.LastName": "FirstInitial.LastName",
        "FirstName_1letter_LastName": "FirstInitial_LastName",

        "LastName_1letterFirstName": "LastInitialFirstName",
        "LastName_1letter.FirstName": "LastInitial.FirstName",
        "LastName_1letter_FirstName": "LastInitial_FirstName",

        "FirstNameLastName_1letter": "FirstNameLastInitial",
        "FirstName.LastName_1letter": "FirstName.LastInitial",
        "FirstName_LastName_1letter": "FirstName_LastInitial",

        # Existing "1" based patterns
        "FirstName1.LastName": "FirstInitial.LastName",
        "FirstName.LastName1": "FirstName.LastInitial",
        "FirstName1LastName": "FirstInitialLastName",
        "FirstNameLastName1": "FirstNameLastInitial",
        "LastNameFirstName1": "LastNameFirstInitial",
    }

    return alias_map.get(pattern, pattern)


def create_emails2(row, email_patterns):

    company_name = row['Company'].strip()
    first_name = row['First Name'].strip().lower()
    last_name = row['Last Name'].strip().lower()

    formats = email_patterns.get(company_name.lower())

    if not formats:
        return None

    try:
        email_pattern, domain = formats.split('@', maxsplit=1)

        # ✅ NEW: normalize pattern BEFORE using
        email_pattern = normalize_pattern(email_pattern)

    except Exception as e:
        print(f"Error processing file: {formats} ----- {str(e)}")
        return None

    # Define patterns
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

        "FirstName.LastInitial": f"{first_name}.{last_name[0]}",
        "FirstInitial.LastName": f"{first_name[0]}.{last_name}",

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

        "FirstInitialLastNameLastInitial": f"{first_name[0]}{last_name}{last_name[0]}",
        "FirstName1LastName": f"{first_name[0]}{last_name}",
        "FirstNameLastName1": f"{first_name}{last_name[0]}",
        "LastInitialFirstName": f"{last_name[0]}{first_name}",
        "LastNameFirstName1": f"{last_name}{first_name[0]}",

        "LastInitial.FirstInitial": f"{last_name[0]}.{first_name[0]}",
        "LastInitial-FirstInitial": f"{last_name[0]}-{first_name[0]}",
        "LastInitial_FirstInitial": f"{last_name[0]}_{first_name[0]}",
        "LastInitialFirstInitial": f"{last_name[0]}{first_name[0]}",

        "LastInitial.FirstName": f"{last_name[0]}.{first_name}",
        "LastInitial-FirstName": f"{last_name[0]}-{first_name}",
        "LastInitial_FirstName": f"{last_name[0]}_{first_name}",
        "LastInitialFirstName": f"{last_name[0]}{first_name}",
    }

    # Case-insensitive matching
    patterns_lower = {k.lower(): v for k, v in patterns.items()}

    email_local_part = patterns_lower.get(email_pattern.lower())

    return f"{email_local_part}@{domain}" if email_local_part else None


def email_creator_app(file, email_patterns):

    try:
        processed_data = reader(file)
        processed_data['Email'] = ""

        processed_data['Email'] = processed_data.apply(
            lambda row: create_emails2(row, email_patterns), axis=1
        )

        print("email generated")

    except Exception as e:
        print(f" Failed email_creator_app ': {e}")

    return processed_data