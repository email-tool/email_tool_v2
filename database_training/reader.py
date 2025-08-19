import pandas as pd
import os
import re

def process_file(file_path, chunk_size=50000):
    """Efficiently processes large CSV/Excel files with optimized memory handling."""
    
    _, file_extension = os.path.splitext(file_path)  # Get file extension
    
    # Define required and all possible columns
    required_columns = ["company", "contact name", "email"]
    all_columns = ["srl no", "company", "contact name", "first name", "last name", "email", 
                   "designation", "location", "industry", "mailer_status"]

    def process_chunk(data, chunk_number):
        """Processes each chunk of data efficiently."""
        if data.empty:
            print(f"⚠️ Skipping empty chunk {chunk_number}")
            return None  # Skip empty chunks

        # Ensure column names are lowercase
        data.columns = data.columns.str.lower()

        # Ensure required columns exist
        missing_required_columns = [col for col in required_columns if col not in data.columns]
        if missing_required_columns:
            print(f"⚠️ Skipping chunk {chunk_number}: Missing columns {missing_required_columns}")
            return None

        # Drop rows with missing values in required columns
        data.dropna(subset=required_columns, inplace=True)

        if data.empty:
            print(f"⚠️ Skipping chunk {chunk_number}: All rows dropped after dropna()")
            return None  # Skip if dropna() removed everything

        # Convert all columns to string BEFORE using `.str` functions
        data = data.astype(str)  # ✅ Convert the entire DataFrame to strings

        # Handle missing "first name" and "last name" by splitting "contact name"
        if "first name" not in data.columns or "last name" not in data.columns:
            if "contact name" in data.columns:
                split_names = data["contact name"].str.extract(r'(\S+)\s*(.*)', expand=True)
                data["first name"] = split_names[0].fillna("")
                data["last name"] = split_names[1].fillna("")

        # Convert all string columns to lowercase safely
        data = data.apply(lambda x: x.str.lower() if x.dtype == "object" else x)

        print(f"✅ Processed chunk {chunk_number}: {data.shape[0]} rows")
        return data

    processed_chunks = []

    # Process CSV in chunks
    if file_extension == ".csv":
        print ("FIle is CSV")
        chunk_iterator = pd.read_csv(file_path, chunksize=chunk_size, low_memory=False)
        for i, chunk in enumerate(chunk_iterator):
            processed_chunk = process_chunk(chunk, i)
            if processed_chunk is not None:
                processed_chunks.append(processed_chunk)

    # Process Excel files (first 5 sheets only)
    elif file_extension in [".xls", ".xlsx"]:
        print ("FIle is Excel")
        excel_data = pd.ExcelFile(file_path)
        sheets = excel_data.sheet_names[:5]  # Read only first 5 sheets
        for i, sheet in enumerate(sheets):
            try:
                chunk = excel_data.parse(sheet, dtype=str)  # ✅ `dtype=str` prevents `.str` errors
                processed_chunk = process_chunk(chunk, i)
                if processed_chunk is not None:
                    processed_chunks.append(processed_chunk)
            except Exception as e:
                print(f"⚠️ Error processing sheet {sheet}: {e}")

    else:
        raise ValueError("Unsupported file format. Only CSV and Excel files are allowed.")

    # Ensure we return at least one valid DataFrame
    if processed_chunks:
        return pd.concat(processed_chunks, ignore_index=True)
    else:
        print("🚨 No valid data found! Returning empty DataFrame.")
        return pd.DataFrame()  # Return an empty DataFrame instead of failing

def reader(file_path):
    try:
        processed_data = process_file(file_path)
        print("✅ Final processed DataFrame shape:", processed_data.shape)
        return processed_data
    except Exception as e:
        print(f"🚨 Error processing file {file_path}: {e}")
        return pd.DataFrame()  # Return empty DataFrame instead of failing
