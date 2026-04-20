import os
import pickle
import math
import time
import csv
import logging
import pandas as pd
import tempfile
from datetime import datetime
from pathlib import Path
from database_training import update_db_manually
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO

# Custom modules
from helper.csv_excel_loader import file_load
from email_verifier.email_verifier import verify_app
from automatic_email_format.web_email_scrapper_multiEngine import recover_with_latest, update_pickle_file, fetch_google_results
from automatic_email_format.get_best_email import get_final_email
from automatic_email_format.process_scrapped_data import process_run
from automatic_email_format.automatic_email_runner import run_automatic_email
from database_training.update_db_manually import update_pickle
from database_training.db_pipeline import process_single_file, process_folder
from email_creation.create_emails import email_creator_app

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')

socketio = SocketIO(app, cors_allowed_origins="*")

# Logging — terminal + file for both app logger and werkzeug
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),                        # terminal
        logging.FileHandler("flask_access.log"),        # file
    ]
)
logger = logging.getLogger(__name__)

# ===================================================================
# Path setup
# ===================================================================
BASE_DIR   = Path(__file__).resolve().parent
base_path  = BASE_DIR / "files"
FILES_DIR  = base_path
UPLOAD_DIR = BASE_DIR / "uploads"

# Always use the absolute UPLOAD_DIR — avoids mismatch when Flask runs
# from a different working directory than BASE_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_DIR)

source_file_path          = base_path / "database_source_files"
output_files_path         = base_path / "database_output_files"
output_files_path_new     = base_path / "database_output_files_new"
main_db_dir               = base_path / "main_database"
new_db_pickle_file_path   = main_db_dir / "new_db_2026.pkl"
old_db_pickle_file_path   = main_db_dir / "old_db_2026.pkl"
new_db_pickle_file_path_bckup = main_db_dir / "new_db_backup.pkl"
old_db_pickle_file_path_bckup = main_db_dir / "old_db_backup.pkl"

email_created_path         = base_path / "created_emails"
email_created_new_tool_path = email_created_path / "new_tool"
email_created_old_tool_path = email_created_path / "old_tool"
scrapper_output            = base_path / "automatic_emails_format_created"
missing_data               = base_path / "missing_emails"
verified_path              = base_path / "verified_emails"

# Create all directories
for d in [
    source_file_path, output_files_path, output_files_path_new,
    main_db_dir, email_created_path, email_created_new_tool_path,
    email_created_old_tool_path, scrapper_output, missing_data,
    verified_path, BASE_DIR / "track_automation",
]:
    d.mkdir(parents=True, exist_ok=True)

# Initialize pickle files
new_data = {'10th sfg': 'LastName@soc.mil'}
def create_pickle_if_missing(file_path, data):
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            pickle.dump(data, f)

create_pickle_if_missing(new_db_pickle_file_path, new_data)
create_pickle_if_missing(old_db_pickle_file_path, new_data)

# ===================================================================
# Database Count
# ===================================================================
@app.route('/database-counts')

# ===================================================================
# In-memory cache for DB count (GLOBAL)
# ===================================================================


# ===================================================================
# Database Count (MAIN ONLY)
# ===================================================================
@app.route('/database-counts')
def database_count():
    _db_count_cache = {
    "main": {"count": None, "mtime": None}
}
    try:
        main_mtime = os.path.getmtime(new_db_pickle_file_path)

        # Reload only if file changed
        if _db_count_cache["main"]["mtime"] != main_mtime:
            with open(new_db_pickle_file_path, 'rb') as f:
                db = pickle.load(f)

            _db_count_cache["main"] = {
                "count": len(db),
                "mtime": main_mtime
            }

        return jsonify({

            "main_db": f"New DB {_db_count_cache["main"]["count"]}" 
            # "main_db": _db_count_cache["main"]["count"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ===================================================================
# File Browser (with subfolder support)
# ===================================================================
FILES_DIR = os.path.join(BASE_DIR, 'files')




@app.route('/list-files')
def list_files():
    rel_path = request.args.get('path', '/').lstrip('/')
    full_path = os.path.join(FILES_DIR, rel_path)

    if not os.path.abspath(full_path).startswith(os.path.abspath(FILES_DIR)):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.exists(full_path):
        return jsonify({"error": "Path not found"}), 404

    try:
        items = []
        for entry in sorted(os.listdir(full_path)):
            entry_path = os.path.join(full_path, entry)
            if os.path.isdir(entry_path):
                items.append({"name": entry, "is_dir": True})
            else:
                items.append({
                    "name": entry,
                    "is_dir": False,
                    "size": os.path.getsize(entry_path)
                })
        return jsonify({"items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download-file')
def download_file():
    file_path = request.args.get('path')
    if not file_path:
        return "No file specified", 400
    full_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(full_path):
        return "File not found", 404
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename, as_attachment=True)

# ===================================================================
# Helper Functions
# ===================================================================
def log_query_result(log_file, query, results, error=None):
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if error:
            log_entry = f"{timestamp} | QUERY: {query} | ERROR: {error}\n"
        else:
            log_entry = f"{timestamp} | QUERY: {query} | RESULTS: {results}\n"
        f.write(log_entry)
        f.flush()

def make_backup_db(main_file_path, backup_path):
    try:
        with open(main_file_path, 'rb') as f:
            data = pickle.load(f)
        with open(backup_path, 'wb') as f:
            pickle.dump(data, f)
    except:
        pass

# ===================================================================
# Routes
# ===================================================================
@app.route('/')
def dashboard():
    return render_template('dashboard.html')



@app.route('/train-database', methods=['POST'])
def train_database():
    """
    Feature: Extract Email Patterns from Uploaded File or Folder
    ─────────────────────────────────────────────────────────────
    Accepts a single CSV/XLSX file OR a folder of files.
    For each file:  reads → extracts company email patterns → saves CSV → updates PKL.
    Each file is committed to the PKL immediately so no work is lost on interruption.

    Form fields:
      file   — single file upload
      folder — multiple files (folder upload)
    """
    has_file   = 'file'   in request.files and request.files['file'].filename
    has_folder = 'folder' in request.files

    if not has_file and not has_folder:
        return jsonify({"error": "No file or folder provided"}), 400

    def emit_train_log(msg: str, kind: str = "info"):
        socketio.emit("train_log", {"message": msg, "type": kind})

    # ── Single file ──────────────────────────────────────────────────────────
    if has_file:
        file = request.files['file']
        safe_name = Path(file.filename).name
        file_path = UPLOAD_DIR / safe_name
        file.save(file_path)
        logger.info("[train-database] Single file received: %s", safe_name)

        status = process_single_file(
            file_path, output_files_path_new, new_db_pickle_file_path,
            emit_fn=emit_train_log
        )

        if status["error"]:
            return jsonify({"error": status["error"]}), 400

        return jsonify({
            "log": (
                f"Done! {status['rows_extracted']} patterns extracted — "
                f"+{status['new_companies']} new companies, "
                f"{status['updated_companies']} updated, "
                f"DB total: {status['db_total']:,}"
            )
        })

    # ── Folder ───────────────────────────────────────────────────────────────
    uploaded_files = request.files.getlist('folder')
    supported = ('.csv', '.xls', '.xlsx')
    folder_upload_dir = UPLOAD_DIR / "folder_upload"
    folder_upload_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for uf in uploaded_files:
        if uf.filename and Path(uf.filename).suffix.lower() in supported:
            dest = folder_upload_dir / Path(uf.filename).name
            uf.save(dest)
            saved_files.append(dest)

    if not saved_files:
        return jsonify({"error": "No supported files found in the folder upload (.csv / .xls / .xlsx)"}), 400

    logger.info("[train-database] Folder upload: %d files received", len(saved_files))
    summary = process_folder(
        folder_upload_dir, output_files_path_new, new_db_pickle_file_path,
        emit_fn=emit_train_log
    )

    failed_msg  = f" | Failed: {', '.join(summary['failed'])}" if summary["failed"] else ""
    skipped_msg = f" | Skipped (already done): {len(summary['skipped'])}" if summary["skipped"] else ""

    return jsonify({
        "log": (
            f"Folder done! {len(summary['processed'])} files, "
            f"{summary['total_patterns_added']} patterns added."
            f"{skipped_msg}{failed_msg}"
        )
    })






@app.route('/upload', methods=['POST'])
def upload_file():
    print("Received request...")
    log_message = "No file processed"

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file and file.filename != '':
        print("Processing single file...")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        print(f"File saved at: {file_path}")
        try:
            process_single_file(file_path, Output_files_path_new, new_db_pickle_file_path)
            log_message = "File processed successfully!"
        except Exception as e:
            log_message = f"Error processing file: {str(e)}"

    if 'folder' in request.files:
        print("folder is selected")
        files = request.files.getlist('folder')
        for uploaded_file in files:
            if uploaded_file.filename != '' and (uploaded_file.filename.endswith('.csv') or uploaded_file.filename.endswith('.xlsx')):
                file_path = os.path.join(base_path, os.path.basename(uploaded_file.filename))
                uploaded_file.save(file_path)
                try:
                    process_single_file(file_path, Output_files_path_new, new_db_pickle_file_path)
                    log_message = "Files processed successfully!"
                except Exception as e:
                    log_message += f" | Error on {uploaded_file.filename}: {str(e)}"

    return jsonify({"log": log_message})

@app.route('/update-database-manually', methods=['POST'])
def update_file():
    log_message = "No file processed"
    print ("data updating")
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file and file.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        try:
            updated_dictd = update_pickle(new_db_pickle_file_path, file_path)
            update_pickle(old_db_pickle_file_path, file_path)
            log_message = "Database updated successfully!"
        except Exception as e:
            log_message = f"Error: {str(e)}"

    return jsonify({"log": log_message})

@app.route('/email', methods=['POST'])
def create_email():
    print("\n" + "="*80)
    print(f"[EMAIL] Route hit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

    try:
        with open(new_db_pickle_file_path, 'rb') as f:
            email_patterns = pickle.load(f)
        print(f"[EMAIL] Loaded {len(email_patterns):,} patterns")
    except Exception as e:
        print(f"[EMAIL] Cannot load patterns: {e}")
        return jsonify({"error": f"Cannot load email patterns: {str(e)}"}), 500

    processed_count = 0
    errors = []
    received_type = "none"

    # Prefer single file if both are present (user most likely meant single file)
    if 'file' in request.files and request.files['file'].filename:
        print("[EMAIL] Processing SINGLE FILE upload (priority)")
        received_type = "single"
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        safe_name = os.path.basename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        file.save(file_path)
        print(f"[EMAIL] Saved single file → {safe_name}")

        try:
            df = email_creator_app(file_path, email_patterns)
            missing = df[df["Email"].isna() | (df["Email"].str.strip() == "")]
            good = df[df["Email"].notna() & (df["Email"].str.strip() != "")]

            base_name = os.path.splitext(safe_name)[0]
            good.to_csv(os.path.join(email_created_new_tool_path, f"{base_name}_new_tool_output.csv"), index=False)
            missing.to_csv(os.path.join(missing_data, f"{base_name}_new_tool_missing.csv"), index=False)

            processed_count = len(good)
            print(f"[EMAIL] Processed single file → {processed_count} good emails")

        except Exception as e:
            errors.append(f"Single file {safe_name}: {str(e)}")
            print(f"[EMAIL] Single file error: {e}")

    # Only process folder if NO single file was provided
    elif 'folder' in request.files:
        print("[EMAIL] Processing FOLDER upload")
        received_type = "folder"
        files = request.files.getlist('folder')
        print(f"[EMAIL] Found {len(files)} items in folder upload")

        combined_email_data = pd.DataFrame()

        for uploaded_file in files:
            if not uploaded_file.filename or not uploaded_file.filename.lower().endswith(('.csv', '.xlsx')):
                continue

            safe_name = os.path.basename(uploaded_file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
            uploaded_file.save(temp_path)
            print(f"[EMAIL] Saved folder file → {safe_name}")

            try:
                df = email_creator_app(temp_path, email_patterns)
                missing = df[df["Email"].isna() | (df["Email"].str.strip() == "")]
                good = df[df["Email"].notna() & (df["Email"].str.strip() != "")]

                combined_email_data = pd.concat([combined_email_data, good], ignore_index=True)

                base_name = os.path.splitext(safe_name)[0]
                good.to_csv(os.path.join(email_created_new_tool_path, f"{base_name}_new_tool_output.csv"), index=False)
                missing.to_csv(os.path.join(missing_data, f"{base_name}_new_tool_missing.csv"), index=False)

                processed_count += len(good)
                print(f"[EMAIL] Processed {safe_name} → {len(good)} good emails")

            except Exception as e:
                errors.append(f"{safe_name}: {str(e)}")
                print(f"[EMAIL] Error on {safe_name}: {e}")

        if not combined_email_data.empty:
            combined_email_data.to_csv(os.path.join(email_created_new_tool_path, "combined_email_output.csv"), index=False)

    else:
        return jsonify({"error": "No file or folder provided"}), 400

    if errors:
        msg = f"Processed {processed_count} emails, but had errors:\n" + "\n".join(errors)
        return jsonify({"log": msg, "error": "Partial failure"})

    success_msg = f"Email generation completed! {processed_count} emails created ({received_type} upload)."
    print("[EMAIL] Success:", success_msg)
    return jsonify({"log": success_msg})


@app.route('/emailverify', methods=['POST'])  # ← note: you had /email-verify in JS but /emailverify in backend
def verify_email():
    log_message = "No file processed"
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    try:
        api_key = '748ad80421514463bb9099b85004b0dd'
        df = verify_app(file_path, api_key)
        file_name_no_ext = os.path.splitext(file.filename)[0]
        df.to_csv(f"{verified_path}/{file_name_no_ext}_Verified.csv")
        log_message = f"Verification completed! Rows: {len(df)}"
    except Exception as e:
        log_message = f"Error: {str(e)}"

    return jsonify({"log": log_message})


from automatic_email_format.automatic_email_runner import run_automatic_email

@app.route('/automatic-email', methods=['POST'])


def automatic_email():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "Empty file"}), 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(input_path)

    try:
        output_file = run_automatic_email(
            input_file=input_path,
            output_dir=scrapper_output,
            socketio=socketio, max_companies=None
        )
        d  = update_db_manually.update_pickle(new_db_pickle_file_path, output_file)
        d  = update_db_manually.update_pickle(old_db_pickle_file_path, output_file)
        return jsonify({"log": f"Discovery completed. Output: {os.path.basename(output_file)}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    return jsonify({"log": "Logs cleared!"})

if __name__ == '__main__':
    app.run(port=3000, debug=True)