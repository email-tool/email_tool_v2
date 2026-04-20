# Email Tool v2

A sophisticated email generation and verification platform that extracts, formats, and validates email addresses for companies at scale. Combines a Django web dashboard, Flask backend services, AI-powered email pattern detection, and multi-engine web scraping.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Modules](#modules)
- [Django Dashboard](#django-dashboard)
- [Data Storage](#data-storage)
- [Email Processing Pipeline](#email-processing-pipeline)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Docker Deployment](#docker-deployment)
- [Web Interface](#web-interface)
- [API Integrations](#api-integrations)
- [Database Management](#database-management)
- [Known Limitations and Notes](#known-limitations-and-notes)

---

## Overview

Email Tool v2 is an end-to-end system for generating and validating professional email addresses. Given a spreadsheet of contacts with company names and personal names, the tool:

1. Looks up or discovers the email pattern used by that company (e.g., `first.last@company.com`)
2. Generates the email address using that pattern
3. Verifies deliverability of generated emails via the ZeroBounce API
4. Presents a collaborative dashboard for human review of uncertain records

The platform supports bulk file processing (CSV/XLSX), persistent pattern storage in a pickle database, and a role-based web UI for team workflows.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    User / Web Browser                    │
└───────────────────────────┬──────────────────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │  Django Dashboard  │  Port 8000 / 8123
                  │  (Web UI + Auth)   │
                  └─────────┬──────────┘
                            │  File uploads / work assignments
                  ┌─────────▼──────────┐
                  │   Flask Backend    │  new_tool.py / old_tool.py
                  │  (Processing API)  │
                  └──┬──────┬──────────┘
                     │      │
          ┌──────────▼─┐  ┌─▼────────────────┐
          │  Email      │  │  Web Scraper     │
          │  Creation   │  │  (4 engines)     │
          └──────────┬──┘  └─┬───────────────┘
                     │       │
                  ┌──▼───────▼──┐
                  │   Pickle DB  │  Company → Pattern
                  │  (PKL files) │
                  └─────────────┘
                     │
          ┌──────────▼──────────┐
          │  ZeroBounce API     │  Email Verification
          └─────────────────────┘
```

---

## Directory Structure

```
email_tool_v2/
├── Email_Tool-2026/                          # Main application directory
│   ├── APP/                                  # Flask backend + Python processing modules
│   │   ├── email_creation/                   # Email generation logic
│   │   │   ├── create_emails.py              # Core email creation with pattern matching
│   │   │   ├── reader_email.py               # Input file reader
│   │   │   └── get_email_flags.py            # Email quality flag assignment
│   │   ├── email_verifier/                   # ZeroBounce-based verification
│   │   │   ├── email_verifier.py             # HTTP verification requests
│   │   │   └── csv_excel_loader.py           # File loader
│   │   ├── automatic_email_format/           # AI-powered pattern discovery
│   │   │   ├── web_email_scrapper_multiEngine.py  # Multi-engine scraping
│   │   │   ├── scarpper_manager.py           # Scraping orchestration + pattern detection
│   │   │   ├── get_best_email.py             # Best pattern selection
│   │   │   ├── process_scrapped_data.py      # Post-processing scraped results
│   │   │   └── scrapper_run.py               # Batch runner with checkpointing
│   │   ├── database_training/                # Email pattern DB management
│   │   │   ├── email_format_extracter.py     # Pattern extraction from samples
│   │   │   ├── database_process_single_file.py   # Single-file processing
│   │   │   ├── database_process_mutifile.py  # Batch file processing
│   │   │   ├── merger_for_pckl.py            # CSV → Pickle merge
│   │   │   ├── update_db_manually.py         # Manual database update utility
│   │   │   └── reader.py                     # Generic file reader
│   │   ├── helper/                           # Utility functions
│   │   │   └── csv_excel_loader.py           # CSV/Excel unified loader
│   │   ├── new_tool.py                       # Main Flask application
│   │   ├── old_tool.py                       # Legacy Flask application
│   │   └── full_pipeline_code.py             # Standalone pipeline script
│   │
│   ├── email-generator/                      # Django web application
│   │   ├── email_generator/                  # Django project settings
│   │   │   ├── settings.py                   # Project-wide configuration
│   │   │   ├── urls.py                       # Root URL routing
│   │   │   ├── wsgi.py                       # WSGI entrypoint
│   │   │   └── asgi.py                       # ASGI entrypoint
│   │   ├── dashboard/                        # Core Django app
│   │   │   ├── models.py                     # ORM models
│   │   │   ├── views.py                      # Request handlers
│   │   │   ├── forms.py                      # Form validation
│   │   │   ├── urls.py                       # App URL patterns
│   │   │   ├── admin.py                      # Admin site config
│   │   │   ├── migrations/                   # Database migrations
│   │   │   ├── templates/                    # HTML templates
│   │   │   └── static/                       # CSS and JavaScript
│   │   ├── manage.py                         # Django CLI
│   │   ├── docker-compose.yml                # Docker orchestration
│   │   ├── Dockerfile                        # Docker image build
│   │   ├── db.sqlite3                        # SQLite database
│   │   └── Readme.md                         # Django-specific setup notes
│   │
│   └── run_all.py                            # Launcher: Django + Flask (all services)
│
├── email_creation/                           # Root-level module copies
├── email_verifier/
├── automatic_email_format/
├── database_training/
├── helper/
├── templates/                                # Legacy HTML templates
├── static/                                   # Legacy static assets
├── new_tool.py                               # Root-level standalone Flask app
├── old_tool.py                               # Root-level legacy Flask app
├── full_pipeline_code.py                     # Root-level standalone pipeline
├── email_db_logs/                            # Database activity logs
└── .gitignore
```

---

## Modules

### `email_creation/`

Handles the core task of generating email addresses from company names, personal names, and detected patterns.

**`create_emails.py`**

The main email creation engine. Normalizes pattern names from UI-friendly labels to backend codes, then applies those patterns to generate email addresses.

Supported patterns:

| Pattern Code | Example |
|---|---|
| `fn` | `john@company.com` |
| `ln` | `doe@company.com` |
| `fn.ln` | `john.doe@company.com` |
| `fn_ln` | `john_doe@company.com` |
| `fi.ln` | `j.doe@company.com` |
| `fi_ln` | `j_doe@company.com` |
| `fn.li` | `john.d@company.com` |
| `fnln` | `johndoe@company.com` |
| `filn` | `jdoe@company.com` |
| `lnfi` | `doej@company.com` |
| `ln.fn` | `doe.john@company.com` |

Key functions:

```python
normalize_pattern(pattern)
# Maps UI-friendly pattern names to internal codes

create_emails2(row, email_patterns)
# Generates an email for a single DataFrame row

email_creator_app(file, email_patterns)
# Batch-processes an entire file and returns a DataFrame with emails
```

**`get_email_flags.py`**

Assigns quality flags (`High`, `Medium`, `Low`) to generated emails based on source confidence (database hit vs. scraped vs. inferred).

---

### `email_verifier/`

Validates generated email addresses against the ZeroBounce API.

**`email_verifier.py`**

```python
get_email_status(email, api_key)
# Sends a single email to ZeroBounce for validation
# Returns: valid | invalid | catch-all | unknown | abuse | do_not_mail

verify_app(file, api_key)
# Validates all emails in a CSV/XLSX file
```

Verification statuses returned by ZeroBounce:

| Status | Meaning |
|---|---|
| `valid` | Email is deliverable |
| `invalid` | Email does not exist |
| `catch-all` | Domain accepts all email (inconclusive) |
| `unknown` | Server unreachable or unverifiable |
| `abuse` | Known spam or abuse address |
| `do_not_mail` | Flagged for opt-out / role-based |

---

### `automatic_email_format/`

Automatically discovers email patterns for companies not yet in the database through multi-engine web scraping.

**`web_email_scrapper_multiEngine.py`**

Scrapes search results from four engines:

- Google
- Bing
- Yahoo
- StartPage

Extracts email addresses from scraped HTML pages using BeautifulSoup.

**`scarpper_manager.py`**

Orchestrates the scraping pipeline:

1. Builds a search query for the target company
2. Fetches results from all four engines
3. Extracts raw email addresses from results
4. Identifies which pattern the emails follow using template matching
5. Logs all queries and results with timestamps

Pattern detection uses name variation matching (common first/last names like `john`, `jane`, `first`, `last`) and regex against extracted emails.

**`get_best_email.py`**

When multiple candidate patterns are found, selects the best one:

- Uses `difflib.SequenceMatcher` to score similarity between company name and email domain
- Prioritizes high-confidence patterns
- Falls back to best-overall if no definitive winner

**`scrapper_run.py`**

Batch runner for processing large lists of companies:

- Processes companies in chunks
- Writes checkpoint `.txt` files to allow resume after interruption
- Saves discovered patterns to CSV output files

---

### `database_training/`

Manages the persistent pickle-file email pattern database.

**`email_format_extracter.py`**

Extracts the email format from sample emails provided in source files:

```
Input:  john.smith@acme.com
Output: fn.ln
```

**`database_process_single_file.py`**

Processes a single CSV/XLSX source file:

1. Loads file
2. Extracts patterns per company domain
3. Saves results as a timestamped CSV in `files/database_output_files/`

**`database_process_mutifile.py`**

Batch version of the above — processes all files in a directory.

**`merger_for_pckl.py`**

Merges CSV output files into the main pickle database:

```python
update_pickle(pickle_file, new_csv_file)
# Loads existing PKL, merges new data, deduplicates, saves
```

**`update_db_manually.py`**

Manual utility for one-off database updates. Handles column normalization (e.g., `mail patterns` → `email pattern`) and merge conflicts.

---

### `helper/`

Shared utility functions used across modules.

**`csv_excel_loader.py`**

Unified file loader that handles:

- `.csv` files
- `.xls` files
- `.xlsx` files (including multi-sheet workbooks)

Returns a pandas DataFrame regardless of input format.

---

## Django Dashboard

The Django application at `Email_Tool-2026/email-generator/` provides a web interface for team-based workflows.

### Models

**`UploadSheet`**

Stores files uploaded by users for processing.

| Field | Type | Description |
|---|---|---|
| `user` | ForeignKey | Owning user |
| `file` | FileField | Uploaded Excel file |
| `created_at` | DateTimeField | Upload timestamp |
| `updated_at` | DateTimeField | Last modification |

**`MissingDataFile`**

Stores files that contain records with missing or unresolvable email data, flagged for human review.

| Field | Type | Description |
|---|---|---|
| `file` | FileField | File with incomplete records |
| `created_at` | DateTimeField | Creation timestamp |

**`WorkAssignment`**

Assigns a slice of a file to a specific user for review.

| Field | Type | Description |
|---|---|---|
| `user` | ForeignKey | Assigned user |
| `upload_sheet` | ForeignKey | Parent uploaded file |
| `start_row` | IntegerField | First row of assignment |
| `end_row` | IntegerField | Last row of assignment |
| `is_active` | BooleanField | Assignment status |

### Views and URL Routes

| URL | View | Description |
|---|---|---|
| `/` | `home` | Dashboard home |
| `/login` | `login_view` | Authentication |
| `/logout` | `logout_view` | Session logout |
| `/upload-sheet` | `upload_sheet` | File upload and processing |
| `/missing-data` | `missing_data` | Review incomplete records |
| `/download/<type>/<id>` | `download_file` | Download output, missing, or summary files |
| `/admin/` | Django Admin | Admin interface |

### Forms

**`UploadSheetForm`**

Validates that uploaded files contain the required columns before accepting the upload.

### Templates

Located in `email-generator/dashboard/templates/`:

- `home.html` — Dashboard landing page
- `upload_sheet.html` — File upload interface
- `login.html` — Login page
- `missing_data.html` — Missing data review interface

---

## Data Storage

### SQLite / PostgreSQL (Django ORM)

Used for user accounts, file metadata, and work assignments. Default is SQLite (`db.sqlite3`). PostgreSQL configuration is present in `settings.py` but commented out.

### Pickle Files

The core email pattern database is stored as Python pickle files:

| File | Description |
|---|---|
| `files/main_database/new_db_2026.pkl` | Primary database — company domain → email pattern |
| `files/main_database/old_db_2026.pkl` | Legacy/previous version database |
| `files/main_database/new_db_backup.pkl` | Backup of primary database |
| `files/main_database/old_db_backup.pkl` | Backup of legacy database |

Database structure (dict):

```python
{
  "acme.com": "fn.ln",
  "globex.com": "fi.ln",
  ...
}
```

### File Storage Directories

All data files are organized under `files/`:

```
files/
├── database_source_files/           # Raw input files for pattern training
├── database_output_files/           # Extracted pattern CSVs (timestamped)
├── database_output_files_new/       # New-batch output CSVs
├── main_database/                   # Pickle database files
├── created_emails/
│   ├── new_tool/                    # Output from new_tool.py
│   └── old_tool/                    # Output from old_tool.py
├── automatic_emails_format_created/ # Patterns discovered via scraping
├── missing_emails/                  # Records that could not be resolved
└── verified_emails/                 # Email verification results
```

### Logs

| File | Description |
|---|---|
| `log.txt` | General application log |
| `flask_access.log` | Flask HTTP access log |
| `email_db_logs/` | Database training activity logs |
| `*.txt` (checkpoint files) | Scraping batch progress (used for resume) |

---

## Email Processing Pipeline

The full end-to-end pipeline has three stages:

### Stage 1: Email Generation

```
Input CSV/XLSX
    │
    ▼
Load file (csv_excel_loader)
    │
    ▼
For each row:
    ├── Look up company domain in pickle database
    │       ├── Found → use stored pattern
    │       └── Not found → go to Stage 2 (Scraping)
    │
    ▼
Apply pattern to first/last name
    │
    ▼
Output DataFrame with generated emails
```

### Stage 2: Pattern Discovery (Scraping)

Triggered when a company domain is not in the database.

```
Company name / domain
    │
    ▼
Build search queries
    │
    ▼
Scrape Google + Bing + Yahoo + StartPage in parallel
    │
    ▼
Extract raw email addresses from HTML
    │
    ▼
Match extracted emails against name variation templates
    │
    ▼
Score and select best matching pattern
    │
    ▼
Save pattern to database for future lookups
```

### Stage 3: Verification

```
Generated emails
    │
    ▼
Batch submit to ZeroBounce API
    │
    ▼
Tag each email: valid / invalid / catch-all / unknown
    │
    ▼
Output verified file + missing/flagged records
```

---

## Configuration

### Django Settings (`email-generator/email_generator/settings.py`)

| Setting | Value | Description |
|---|---|---|
| `DEBUG` | `True` | Development mode — set `False` in production |
| `ALLOWED_HOSTS` | `.quantilence.com`, `127.0.0.1`, `localhost` | Accepted hostnames |
| `CSRF_TRUSTED_ORIGINS` | `https://email-gen.quantilence.com` | Trusted CSRF origins |
| `DATABASES` | SQLite by default | Switch to PostgreSQL by uncommenting config |
| `LOGIN_URL` | `/login` | Redirect target for unauthenticated requests |
| `MEDIA_ROOT` | `uploads/` | Uploaded file storage path |
| `STATIC_URL` | `/static/` | Static asset URL prefix |

### Docker Compose (`email-generator/docker-compose.yml`)

Two services are defined:

| Service | Port | Description |
|---|---|---|
| `web` | 8123 | Gunicorn-served Django application |
| `nginx` | 8125 | Nginx reverse proxy |

---

## Environment Variables

The following variables must be set before running the application. Create a `.env` file in the project root or export them in your shell:

| Variable | Required | Description |
|---|---|---|
| `ZEROBOUNCE_API_KEY` | Yes | API key for email verification (from zerobounce.net) |
| `DJANGO_SECRET_KEY` | Yes | Django cryptographic secret key |
| `DEBUG` | No | Set to `False` in production (default: `True`) |
| `POSTGRES_HOST` | No | PostgreSQL host (if not using SQLite) |
| `POSTGRES_PORT` | No | PostgreSQL port (default: `5432`) |
| `POSTGRES_DB` | No | PostgreSQL database name |
| `POSTGRES_USER` | No | PostgreSQL username |
| `POSTGRES_PASSWORD` | No | PostgreSQL password |

---

## Installation

### Prerequisites

- Python 3.11+
- pip
- (Optional) Docker and Docker Compose for containerized deployment

### 1. Clone the repository

```bash
git clone <repo-url>
cd email_tool_v2
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install Python dependencies

```bash
pip install django flask flask-socketio pandas requests \
    beautifulsoup4 openpyxl googlesearch-python gunicorn
```

### 4. Configure environment variables

```bash
cp .env.example .env            # If an example file exists
# Edit .env with your actual values
```

### 5. Initialize the Django database

```bash
cd Email_Tool-2026/email-generator
python manage.py migrate
python manage.py createsuperuser
```

### 6. Set up the file storage directories

The application expects a `files/` directory with specific subdirectories. Create them if they do not exist:

```bash
mkdir -p files/main_database
mkdir -p files/database_source_files
mkdir -p files/database_output_files
mkdir -p files/database_output_files_new
mkdir -p files/created_emails/new_tool
mkdir -p files/created_emails/old_tool
mkdir -p files/automatic_emails_format_created
mkdir -p files/missing_emails
mkdir -p files/verified_emails
mkdir -p uploads
```

---

## Running the Application

### Option A: All Services at Once

```bash
cd Email_Tool-2026
python run_all.py
```

This launches the Django development server, `old_tool.py`, and `new_tool.py` as separate processes.

### Option B: Run Services Individually

**Django Dashboard:**

```bash
cd Email_Tool-2026/email-generator
python manage.py runserver
# Accessible at http://127.0.0.1:8000
```

**Flask Backend (new tool):**

```bash
cd Email_Tool-2026/APP
python new_tool.py
```

**Flask Backend (legacy tool):**

```bash
cd Email_Tool-2026/APP
python old_tool.py
```

### Option C: Standalone Pipeline (no web UI)

```bash
python Email_Tool-2026/APP/full_pipeline_code.py
```

---

## Docker Deployment

```bash
cd Email_Tool-2026/email-generator

# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# Apply migrations inside the container
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Stop services
docker-compose down
```

Services after deployment:

| Service | URL |
|---|---|
| Django App | `http://localhost:8123` |
| Nginx Proxy | `http://localhost:8125` |

For production, update `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `DEBUG=False` in `settings.py` before building the image.

---

## Web Interface

### User Workflow

1. **Login** at `/login` with your Django credentials
2. **Upload a sheet** at `/upload-sheet`
   - File must be CSV or XLSX
   - Required columns are validated on upload
3. The system processes the file through the pipeline (generation + verification)
4. **Download results** from the dashboard:
   - Output file (with generated/verified emails)
   - Missing data file (records that could not be resolved)
   - Summary report
5. If missing data exists, it is assigned to team members via **Work Assignments**
6. Reviewers access `/missing-data` to fill in or correct records

### Admin Interface

The Django admin at `/admin/` allows superusers to:

- Manage users and permissions
- View and manage all uploaded files
- Inspect work assignments
- Access raw database records

---

## API Integrations

### ZeroBounce

Used for email deliverability verification.

- **Endpoint**: `https://api.zerobounce.net/v2/validate`
- **Parameters**: `api_key`, `email`
- **Documentation**: https://www.zerobounce.net/docs/

Usage in code:

```python
from email_verifier.email_verifier import get_email_status

status = get_email_status("john.doe@example.com", api_key="YOUR_KEY")
# Returns: "valid", "invalid", "catch-all", etc.
```

---

## Database Management

### Viewing the Pattern Database

```python
import pickle

with open("files/main_database/new_db_2026.pkl", "rb") as f:
    db = pickle.load(f)

print(db)  # { "acme.com": "fn.ln", ... }
```

### Adding Patterns Manually

Use the `update_db_manually.py` script:

```bash
cd Email_Tool-2026/APP
python database_training/update_db_manually.py
```

Edit the script to specify the source CSV file path and target pickle file before running.

### Training from New Source Files

Place new source files (CSV/XLSX containing sample emails) into `files/database_source_files/`, then run:

```python
from database_training.database_process_mutifile import get_email_formats
get_email_formats("files/database_source_files/")
```

Merge the resulting CSVs into the pickle database:

```python
from database_training.merger_for_pckl import update_pickle
update_pickle(
    "files/main_database/new_db_2026.pkl",
    "files/database_output_files/your_output.csv"
)
```

---

## Known Limitations and Notes

- **No formal test suite**: The `tests.py` file exists but contains no tests. All testing is manual.
- **Hardcoded secrets**: `SECRET_KEY` in `settings.py` and Flask `secret_key` in `new_tool.py` should be moved to environment variables before production deployment.
- **SQLite in production**: The default SQLite database is not suitable for concurrent multi-user access. Switch to PostgreSQL for production by uncommenting the PostgreSQL config in `settings.py`.
- **DEBUG=True**: Must be set to `False` before deploying publicly.
- **Scraping reliability**: Multi-engine scraping depends on the structure and availability of search engine result pages. Rate limits or layout changes may reduce pattern discovery accuracy.
- **Pickle files not version-controlled**: `.gitignore` excludes `.pkl` files. The pattern database must be shared or reproduced separately across environments.
- **Duplicate module copies**: The same modules exist both under `Email_Tool-2026/APP/` and at the project root. The root-level copies appear to be legacy or development duplicates.
