# =============================================================================
# db_pipeline.py  —  Database Training Pipeline
# =============================================================================
# Single-file module that covers the entire database training pipeline:
# read user files → extract email patterns → save CSV → update pickle DB.
#
# SECTIONS
# ─────────────────────────────────────────────────────────────────────────────
#  §1  Imports & Logging
#  §2  Config Loader       — loads patterns.json and column_map.json
#  §3  File Reader         — reads CSV/XLSX, normalises columns, splits names
#  §4  Pattern Extractor   — identifies company email pattern from sample rows
#  §5  Single File Processor — extract → save CSV → update PKL (one file)
#  §6  Multi File Processor  — folder, processes file-by-file with checkpoint
#  §7  Database Updater    — merges a CSV into the pickle database
#
# PUBLIC API (used by new_tool.py / new_tool_v2.py)
# ─────────────────────────────────────────────────────────────────────────────
#  process_single_file(input_file, output_folder, pkl_path)  → dict
#  process_folder(input_folder, output_folder, pkl_path)     → dict
#  update_pickle(pkl_path, csv_path)                         → dict
#
# INPUT FILE CONTRACT (what the user uploads)
# ─────────────────────────────────────────────────────────────────────────────
#  Required data:  company, first name, last name, email
#  Column names:   flexible — see column_map.json for accepted variations
#  Formats:        CSV, XLS, XLSX  (case-insensitive extension)
#  Sheets:         for Excel, first 5 sheets are read and combined
#
# OUTPUT FORMAT
# ─────────────────────────────────────────────────────────────────────────────
#  Intermediate CSV columns:  company | email_pattern
#  Pickle DB structure:       { "company name (lowercase)": "Pattern@domain.com" }
# =============================================================================


# =============================================================================
# §1  Imports & Logging
# =============================================================================

import json
import logging
import os
import pickle
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# =============================================================================
# §2  Config Loader
# =============================================================================
# Loads patterns.json and column_map.json from the same directory as this file.
# Both files are the single source of truth — no pattern or column alias is
# hard-coded anywhere else in this module.
# =============================================================================

_MODULE_DIR   = Path(__file__).resolve().parent
_PATTERNS_FILE   = _MODULE_DIR / "patterns.json"
_COLUMN_MAP_FILE = _MODULE_DIR / "column_map.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_patterns() -> tuple[dict, dict, list]:
    """Returns (patterns dict, aliases dict, invalid list)."""
    data = _load_json(_PATTERNS_FILE)
    return data["patterns"], data["aliases"], data["invalid"]


def _load_column_map() -> dict:
    """Returns {standard_name: [accepted variations]} mapping."""
    data = _load_json(_COLUMN_MAP_FILE)
    return {k: v for k, v in data.items() if not k.startswith("_")}


# Cache on first load — files don't change at runtime
_PATTERNS, _ALIASES, _INVALID_PATTERNS = _load_patterns()
_COLUMN_MAP = _load_column_map()

# Reverse map: "first name" → "first_name", "fname" → "first_name", etc.
_COL_REVERSE: dict[str, str] = {}
for _std, _variants in _COLUMN_MAP.items():
    for _v in _variants:
        _COL_REVERSE[_v.lower().strip()] = _std


# =============================================================================
# §3  File Reader
# =============================================================================
# Reads a CSV or XLSX file and returns a normalised DataFrame with standard
# column names: company | first_name | last_name | email
#
# Handles:
#   - Case-insensitive file extensions (.CSV, .Xlsx, etc.)
#   - Empty files              → raises ValueError with clear message
#   - Flexible column names    → mapped via column_map.json
#   - contact_name present but first/last missing → auto-splits on first space
#   - Missing mandatory columns after all attempts → raises ValueError listing
#     exactly which columns are missing and what names the user can use
#   - Large CSV files          → chunk-based reading to avoid memory issues
#   - Excel multi-sheet        → first 5 sheets combined
# =============================================================================

_MANDATORY = ["company", "first_name", "last_name", "email"]
_CHUNK_SIZE = 50_000


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renames DataFrame columns to internal standard names via column_map."""
    rename_map = {}
    for col in df.columns:
        std = _COL_REVERSE.get(col.lower().strip())
        if std:
            rename_map[col] = std
    return df.rename(columns=rename_map)


def _split_contact_name(df: pd.DataFrame) -> pd.DataFrame:
    """
    If first_name/last_name are absent but contact_name exists, splits it.

    Strategy: first word → first_name, last word → last_name.
    Middle names are ignored.
    e.g. "David Parker James" → first_name="david", last_name="james"
         "David James"        → first_name="david", last_name="james"
         "David"              → first_name="david", last_name=""
    """
    has_first   = "first_name"   in df.columns
    has_last    = "last_name"    in df.columns
    has_contact = "contact_name" in df.columns

    if (not has_first or not has_last) and has_contact:
        # Split into individual words, then take first and last word
        words = df["contact_name"].fillna("").str.strip().str.split()
        if not has_first:
            df["first_name"] = words.apply(lambda w: w[0]  if w else "")
        if not has_last:
            df["last_name"]  = words.apply(lambda w: w[-1] if len(w) > 1 else "")

    return df


def _check_mandatory(df: pd.DataFrame) -> None:
    """Raises ValueError listing every missing mandatory column with hints."""
    missing = [c for c in _MANDATORY if c not in df.columns]
    if not missing:
        return

    hints = {k: v[:4] for k, v in _COLUMN_MAP.items() if k in missing}
    msg_parts = []
    for col in missing:
        accepted = ", ".join(f'"{x}"' for x in (hints.get(col) or [col]))
        msg_parts.append(f"  • '{col}'  (accepted column names: {accepted}, ...)")

    raise ValueError(
        f"Missing mandatory columns after reading the file:\n" + "\n".join(msg_parts) +
        f"\n\nTip: Column names are case-insensitive. "
        f"See column_map.json for the full list of accepted names."
    )


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drops rows with missing mandatory values and lowercases string columns."""
    df = df.dropna(subset=[c for c in _MANDATORY if c in df.columns])
    df = df[df["email"].str.contains("@", na=False)]  # must be a valid-ish email
    for col in ["first_name", "last_name", "company"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    return df.reset_index(drop=True)


def _process_chunk(chunk: pd.DataFrame, chunk_idx: int) -> pd.DataFrame | None:
    """Normalises a single chunk; returns None if the chunk has no usable rows."""
    if chunk.empty:
        logger.debug("Skipping empty chunk %d", chunk_idx)
        return None

    chunk = _normalise_columns(chunk)
    chunk = _split_contact_name(chunk)

    missing = [c for c in _MANDATORY if c not in chunk.columns]
    if missing:
        logger.warning("Chunk %d skipped — missing columns: %s", chunk_idx, missing)
        return None

    chunk = _clean_dataframe(chunk)
    if chunk.empty:
        logger.debug("Chunk %d has no valid rows after cleaning", chunk_idx)
        return None

    logger.debug("Chunk %d: %d valid rows", chunk_idx, len(chunk))
    return chunk


def read_file(file_path: str | Path) -> pd.DataFrame:
    """
    Reads a user-uploaded CSV or XLSX file and returns a clean, normalised
    DataFrame with columns: company | first_name | last_name | email.

    Raises
    ------
    FileNotFoundError  if the file does not exist.
    ValueError         if the file is empty or mandatory columns are missing.
    ValueError         if the file extension is unsupported.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"File is empty: {path.name}")

    ext = path.suffix.lower()
    chunks: list[pd.DataFrame] = []

    if ext == ".csv":
        logger.info("Reading CSV: %s", path.name)
        try:
            for i, chunk in enumerate(pd.read_csv(path, chunksize=_CHUNK_SIZE, low_memory=False, dtype=str)):
                processed = _process_chunk(chunk, i)
                if processed is not None:
                    chunks.append(processed)
        except Exception as e:
            raise ValueError(f"Could not read CSV '{path.name}': {e}") from e

    elif ext in (".xls", ".xlsx"):
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        logger.info("Reading Excel (%s): %s", engine, path.name)
        try:
            xf = pd.ExcelFile(path, engine=engine)
            sheets = xf.sheet_names[:5]
            for i, sheet in enumerate(sheets):
                chunk = xf.parse(sheet, dtype=str)
                processed = _process_chunk(chunk, i)
                if processed is not None:
                    chunks.append(processed)
        except Exception as e:
            raise ValueError(f"Could not read Excel '{path.name}': {e}") from e

    else:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Only .csv, .xls, and .xlsx are accepted."
        )

    if not chunks:
        raise ValueError(
            f"No usable data found in '{path.name}'. "
            f"Check that the file has rows and the required columns are present."
        )

    df = pd.concat(chunks, ignore_index=True)

    # Final mandatory column check on the merged result
    _check_mandatory(df)

    logger.info("Read '%s' → %d rows", path.name, len(df))
    return df


# =============================================================================
# §4  Pattern Extractor
# =============================================================================
# For each row in the normalised DataFrame, applies every pattern template to
# the row's first/last name and checks whether the result matches the email
# local part (the part before @).
#
# Pattern templates are loaded from patterns.json using placeholders:
#   {fn} = first_name,  {ln} = last_name
#   {fi} = first initial,  {li} = last initial
#
# Returns a DataFrame with two columns: company | email_pattern
# Rows where no pattern matches are silently dropped.
# =============================================================================


def _apply_template(template: str, fn: str, ln: str) -> str:
    """Substitutes {fn}, {ln}, {fi}, {li} into a pattern template."""
    fi = fn[0] if fn else ""
    li = ln[0] if ln else ""
    return template.format(fn=fn, ln=ln, fi=fi, li=li)


def _identify_pattern(fn: str, ln: str, email_local: str) -> str | None:
    """
    Tries every pattern in patterns.json against (fn, ln).
    Returns the matched pattern name, or None if nothing matches.
    """
    if not fn or not ln or not email_local:
        return None

    for pattern_name, template in _PATTERNS.items():
        try:
            computed = _apply_template(template, fn, ln)
            if computed == email_local:
                return pattern_name
        except (IndexError, KeyError):
            continue  # skip patterns that need a char that doesn't exist (e.g. empty name)

    return None


def _extract_domain(email: str) -> str:
    """Returns the domain part of an email, or 'unknown' if malformed."""
    try:
        return email.split("@")[1].strip().lower()
    except IndexError:
        return "unknown"


def extract_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifies the email pattern used per row and returns a deduplicated
    DataFrame with columns: company | email_pattern

    Rows where the pattern cannot be identified are dropped.
    email_pattern format: PatternName@domain.com  (e.g. FirstName.LastName@acme.com)
    """
    results = []

    for _, row in df.iterrows():
        fn  = str(row.get("first_name", "")).strip().lower()
        ln  = str(row.get("last_name",  "")).strip().lower()
        email = str(row.get("email", "")).strip().lower()
        company = str(row.get("company", "")).strip().lower()

        if not fn or not ln or "@" not in email or not company:
            continue

        email_local = email.split("@")[0]
        domain      = _extract_domain(email)

        pattern_name = _identify_pattern(fn, ln, email_local)

        if pattern_name and domain != "unknown":
            results.append({
                "company":       company,
                "email_pattern": f"{pattern_name}@{domain}"
            })

    if not results:
        logger.warning("No email patterns could be identified from this data.")
        return pd.DataFrame(columns=["company", "email_pattern"])

    result_df = pd.DataFrame(results)

    # Keep the most frequent pattern per company (majority vote)
    result_df = (
        result_df.groupby(["company", "email_pattern"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .drop_duplicates(subset="company", keep="first")
        .drop(columns="count")
        .reset_index(drop=True)
    )

    logger.info("Extracted patterns for %d companies", len(result_df))
    return result_df


# =============================================================================
# §5  Single File Processor
# =============================================================================
# Reads one file, extracts patterns, saves a dated CSV to output_folder,
# then immediately updates the pickle DB.
#
# Processing order is intentional — CSV is saved before PKL update so that
# if the PKL step fails the CSV is not lost and can be retried.
#
# Returns a status dict:
#   {
#     "file": filename,
#     "rows_extracted": int,
#     "csv_saved": str path or None,
#     "pkl_updated": bool,
#     "error": str or None
#   }
# =============================================================================


def process_single_file(
    input_file:    str | Path,
    output_folder: str | Path,
    pkl_path:      str | Path,
    emit_fn=None,
) -> dict:
    """
    Full pipeline for one file:  read → extract → save CSV → update PKL.

    Parameters
    ----------
    input_file    : path to the user-uploaded CSV or XLSX
    output_folder : directory where the extracted-pattern CSV will be saved
    pkl_path      : path to the pickle database file to update
    emit_fn       : optional callable(msg: str) for live progress updates (e.g. SocketIO emit)

    Returns a status dict with keys:
      file, rows_read, rows_extracted, new_companies, updated_companies,
      db_total, csv_saved, pkl_updated, error
    """
    input_file    = Path(input_file)
    output_folder = Path(output_folder)
    pkl_path      = Path(pkl_path)

    status = {
        "file":              input_file.name,
        "rows_read":         0,
        "rows_extracted":    0,
        "new_companies":     0,
        "updated_companies": 0,
        "db_total":          0,
        "csv_saved":         None,
        "pkl_updated":       False,
        "error":             None,
    }

    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1 — Read
        _emit(emit_fn, f"Processing: {input_file.name}")
        df = read_file(input_file)
        status["rows_read"] = len(df)

        # Step 2 — Extract patterns
        patterns_df = extract_patterns(df)

        if patterns_df.empty:
            status["error"] = "No patterns could be identified from this file."
            logger.warning("%s", _SEP)
            logger.warning("  SKIP  %s", input_file.name)
            logger.warning("  %s", status["error"])
            logger.warning("%s", _SEP)
            _emit(emit_fn, f"{input_file.name} — Failed", "error")
            return status

        status["rows_extracted"] = len(patterns_df)
        _emit(emit_fn, f"Found {len(patterns_df):,} new formats", "success")

        # Step 3 — Save CSV immediately (before PKL update)
        date_str = datetime.now().strftime("%Y-%m-%d")
        csv_name = f"{input_file.stem}_{date_str}_output.csv"
        csv_path = output_folder / csv_name
        patterns_df.to_csv(csv_path, index=False)
        status["csv_saved"] = str(csv_path)

        # Step 4 — Update pickle and capture detailed stats
        pkl_result = update_pickle(pkl_path, csv_path)
        status["pkl_updated"]       = True
        status["new_companies"]     = pkl_result["new"]
        status["updated_companies"] = pkl_result["updated"]
        status["db_total"]          = pkl_result["total"]

        logger.info("%s", _SEP)
        logger.info("  OK    %s", input_file.name)
        logger.info("  rows: %d  |  patterns: %d  |  +new: %d  |  updated: %d  |  db total: %d",
            status["rows_read"], status["rows_extracted"],
            pkl_result["new"], pkl_result["updated"], pkl_result["total"])
        logger.info("%s", _SEP)
        _emit(emit_fn, "Done", "success")

    except (FileNotFoundError, ValueError) as e:
        status["error"] = str(e)
        logger.error("%s", _SEP)
        logger.error("  FAIL  %s", input_file.name)
        logger.error("  %s", e)
        logger.error("%s", _SEP)
        _emit(emit_fn, f"{input_file.name} — Failed", "error")
    except Exception as e:
        status["error"] = f"Unexpected error: {e}"
        logger.exception("%s", _SEP)
        logger.exception("  FAIL  %s  —  %s", input_file.name, e)
        logger.exception("%s", _SEP)
        _emit(emit_fn, f"{input_file.name} — Failed", "error")

    return status


# =============================================================================
# §6  Multi File Processor  (folder)
# =============================================================================
# Processes every CSV/XLSX file in a folder, one at a time.
#
# Checkpoint behaviour:
#   Before processing a file, checks if an output CSV for it already exists
#   in output_folder (matched by stem + date pattern). If found, the file is
#   skipped. This means if the process is interrupted (power cut, crash) and
#   restarted, only unprocessed files are worked on — no work is lost.
#
# Each file is saved and its PKL entry written before moving to the next file.
#
# Returns a summary dict:
#   {
#     "processed":  [list of status dicts for each processed file],
#     "skipped":    [filenames skipped due to checkpoint],
#     "failed":     [filenames that errored],
#     "total_patterns_added": int
#   }
# =============================================================================

_SUPPORTED_EXTS = {".csv", ".xls", ".xlsx"}
_SEP = "=" * 60


def _emit(emit_fn, msg: str, kind: str = "info") -> None:
    """Calls emit_fn(msg, kind) if provided — decouples live-log calls from caller."""
    if emit_fn:
        emit_fn(msg, kind)


def _already_processed(stem: str, existing_csv_names: set[str]) -> bool:
    """Returns True if an output CSV for this file stem already exists."""
    pattern = re.compile(rf"^{re.escape(stem)}_\d{{4}}-\d{{2}}-\d{{2}}_output\.csv$")
    return any(pattern.match(name) for name in existing_csv_names)


def process_folder(
    input_folder:  str | Path,
    output_folder: str | Path,
    pkl_path:      str | Path,
    emit_fn=None,
) -> dict:
    """
    Processes all CSV/XLSX files in input_folder, one at a time.
    Each file is saved and its PKL entry written before moving to the next.

    Parameters
    ----------
    input_folder  : directory containing user-uploaded files
    output_folder : directory for extracted-pattern CSVs
    pkl_path      : path to the pickle database file to update

    Returns a summary dict (see module docstring §6).
    """
    input_folder  = Path(input_folder)
    output_folder = Path(output_folder)
    pkl_path      = Path(pkl_path)

    output_folder.mkdir(parents=True, exist_ok=True)

    summary = {
        "processed":             [],
        "skipped":               [],
        "failed":                [],
        "total_patterns_added":  0,
    }

    files = sorted(
        f for f in input_folder.iterdir()
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTS
    )

    def _emit(msg: str, kind: str = "info"):
        if emit_fn:
            emit_fn(msg, kind)

    if not files:
        logger.warning("No supported files found in: %s", input_folder)
        _emit("No supported files found in folder.", "error")
        return summary

    total   = len(files)
    divider = "─" * 70
    logger.info("")
    logger.info("  FOLDER  %s", input_folder.name)
    logger.info("  %d file(s) queued", total)
    logger.info("  %-6s %-50s %s", "STATUS", "FILE", "DETAILS")
    logger.info("  %s", divider)
    _emit(f"Found {total} file(s) to process")

    for idx, file_path in enumerate(files, start=1):
        # Checkpoint — skip if already done
        if _already_processed(file_path.stem, output_folder):
            logger.info("  SKIP  %-50s  already processed", file_path.name)
            _emit(f"[{idx}/{total}] Skipped: {file_path.name}")
            summary["skipped"].append(file_path.name)
            continue

        _emit(f"[{idx}/{total}] Processing: {file_path.name}")
        status = process_single_file(file_path, output_folder, pkl_path, emit_fn=emit_fn)

        if status["error"]:
            summary["failed"].append(file_path.name)
            _emit(f"[{idx}/{total}] Failed: {file_path.name} — {status['error']}")
        else:
            summary["processed"].append(status)
            summary["total_patterns_added"] += status["rows_extracted"]
            _emit(
                f"[{idx}/{total}] Done: {file_path.name} — "
                f"+{status['new_companies']} new, {status['updated_companies']} updated"
            )

    logger.info("  %s", divider)
    logger.info(
        "  DONE   processed: %d  |  skipped: %d  |  failed: %d  |  total patterns: %d",
        len(summary["processed"]), len(summary["skipped"]),
        len(summary["failed"]), summary["total_patterns_added"]
    )
    logger.info("")
    _emit(
        f"Folder complete — {len(summary['processed'])} processed, "
        f"{len(summary['skipped'])} skipped, {len(summary['failed'])} failed, "
        f"{summary['total_patterns_added']} total patterns"
    )
    return summary


# =============================================================================
# §7  Database Updater
# =============================================================================
# Merges a CSV file (company | email_pattern) into the pickle database.
#
# Rules:
#   - Normalises company key to lowercase and strips whitespace
#   - Skips rows where email_pattern is in the invalid list (patterns.json)
#   - If company already exists in PKL, overwrites with the new pattern
#   - If pkl_path does not exist yet, creates a new empty database
#   - Unwraps single-item lists left by legacy merge code
#
# Also handles the legacy column name "mail patterns" → "email_pattern"
# so older CSV files continue to work.
# =============================================================================


def _load_pickle(pkl_path: Path) -> dict:
    """Loads an existing pickle DB or returns an empty dict if not found."""
    if pkl_path.exists():
        with pkl_path.open("rb") as f:
            data = pickle.load(f)
        logger.info("Loaded existing PKL: %d entries", len(data))
        return data
    logger.info("PKL not found — creating new database at: %s", pkl_path)
    return {}


def _save_pickle(pkl_path: Path, data: dict) -> None:
    pkl_path.parent.mkdir(parents=True, exist_ok=True)
    with pkl_path.open("wb") as f:
        pickle.dump(data, f)


def update_pickle(pkl_path: str | Path, csv_path: str | Path) -> dict:
    """
    Reads csv_path (must have 'company' and 'email_pattern' columns) and
    merges its data into the pickle database at pkl_path.

    Parameters
    ----------
    pkl_path : path to the .pkl file (created if it does not exist)
    csv_path : path to the CSV with extracted patterns

    Returns the updated database dict.
    """
    pkl_path = Path(pkl_path)
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # Load CSV and normalise column names
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as e:
        raise ValueError(f"Could not read CSV '{csv_path.name}': {e}") from e

    df.columns = df.columns.str.lower().str.strip()

    # Legacy column name support
    if "mail patterns" in df.columns and "email_pattern" not in df.columns:
        df.rename(columns={"mail patterns": "email_pattern"}, inplace=True)
    if "email pattern" in df.columns and "email_pattern" not in df.columns:
        df.rename(columns={"email pattern": "email_pattern"}, inplace=True)

    if "company" not in df.columns or "email_pattern" not in df.columns:
        raise ValueError(
            f"CSV '{csv_path.name}' must have 'company' and 'email_pattern' columns. "
            f"Found: {list(df.columns)}"
        )

    # Clean values
    df["company"]       = df["company"].fillna("").astype(str).str.strip().str.lower()
    df["email_pattern"] = df["email_pattern"].fillna("").astype(str).str.strip()

    # Drop invalid patterns
    invalid_lower = [p.lower() for p in _INVALID_PATTERNS]
    df = df[
        (df["company"] != "") &
        (df["email_pattern"] != "") &
        (~df["email_pattern"].str.lower().isin(invalid_lower))
    ]

    if df.empty:
        logger.warning("No valid rows in '%s' — PKL not changed.", csv_path.name)
        return _load_pickle(pkl_path)

    # Build update dict from CSV
    new_entries = dict(zip(df["company"], df["email_pattern"]))

    # Load, merge, fix legacy list values, save
    db = _load_pickle(pkl_path)
    size_before = len(db)
    truly_new   = sum(1 for k in new_entries if k not in db)
    updated     = len(new_entries) - truly_new

    db.update(new_entries)
    db = {
        k: (v[0] if isinstance(v, list) and len(v) == 1 else v)
        for k, v in db.items()
    }

    _save_pickle(pkl_path, db)
    logger.info(
        "PKL updated: +%d new  |  %d updated  |  total %d  (%s)",
        truly_new, updated, len(db), pkl_path.name
    )
    return {"db": db, "new": truly_new, "updated": updated, "total": len(db), "before": size_before}
