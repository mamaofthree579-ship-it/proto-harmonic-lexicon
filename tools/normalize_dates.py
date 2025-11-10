#!/usr/bin/env python3
# tools/normalize_dates.py
"""
Normalize chronology fields in data/motifs_expanded.csv

- Detects likely date columns and prints a preview
- Produces/overwrites two columns:
    - chronology_bce (string form like "3400 BCE" or "700 CE")
    - year (numeric integer used for plotting; numeric part only: 3400, 700, etc.)
- Saves a backup of the original CSV to data/motifs_expanded.bak.csv
- Writes the cleaned CSV back to data/motifs_expanded.csv
"""

import pandas as pd
import re
from pathlib import Path
import shutil

DATA_PATH = Path("data/motifs_expanded.csv")
BACKUP_PATH = Path("data/motifs_expanded.bak.csv")

if not DATA_PATH.exists():
    raise SystemExit(f"Error: {DATA_PATH} not found. Place your CSV at {DATA_PATH}")

# Read CSV
df = pd.read_csv(DATA_PATH, dtype=str)  # read all as string to be safe
print("Columns found:", list(df.columns))
print("\nFirst 5 rows (raw):")
print(df.head(5).to_string(index=False))

# Candidate columns to inspect for chronology information
candidates = [c for c in df.columns if c.lower() in ('chronology_bce','date_estimated','date','year','chronology','chronology_bce ')]
# also consider any column containing 'date' or 'chron'
if not candidates:
    candidates = [c for c in df.columns if 'date' in c.lower() or 'chron' in c.lower()]

print("\nPotential date columns to use:", candidates)

# Prompt-like decision: choose the best candidate automatically by priority,
# but print the choice and first 10 parsed values for your review.
priority = ['chronology_bce','date_estimated','date','year','chronology']
selected = None
for p in priority:
    for c in df.columns:
        if c.lower() == p:
            selected = c
            break
    if selected:
        break
if not selected and candidates:
    selected = candidates[0]

if not selected:
    print("\nNo date-like column detected automatically. The script will add an empty 'chronology_bce' and 'year' column.\n")
else:
    print(f"\nSelected column for parsing: '{selected}'")
    sample = df[selected].fillna("").astype(str).head(10).tolist()
    print("Sample values from selected column:", sample)

# Define parser
def parse_to_chronology(value):
    """
    Input: string value (could be '3400 BCE', '700 CE', '-3400', '3400', 'c.3400', '3400-3200 BCE')
    Output: (chronology_bce_string, year_int) where:
       chronology_bce_string -> e.g. '3400 BCE' or '700 CE' (best-effort)
       year_int -> integer for plotting (positive numeric part: 3400, 700, etc.)
    Rules / assumptions:
       - if 'BCE' present -> treat as BCE and use numeric part (3400)
       - if 'CE' present -> treat as CE and use numeric part (700)
       - if negative numeric like -3400 -> treat as BCE -> 3400
       - if range '3400-3200 BCE' -> take the earlier (larger) value '3400'
       - if plain number:
           - if >= 1000 -> assume BCE (3400)
           - else -> assume CE (700)
       - any 'c.' or 'ca.' trimmed
    """
    if value is None:
        return ("", "")
    s = str(value).strip()
    if s == "" or s.lower() in ("nan","none","n/a"):
        return ("", "")
    s = s.replace("ca.", "").replace("c.", "").replace("approx", "")
    s = s.replace(",", "").strip()
    # Range handling: take the first/earliest token
    m_range = re.match(r'^\s*(\d{3,4})\s*-\s*(\d{3,4})\s*(bce|ce)?', s, flags=re.I)
    if m_range:
        first = int(m_range.group(1))
        era = m_range.group(3)
        if era:
            era = era.upper()
            return (f"{first} {era}", first)
        # if no era label, use numeric inference below
    
    # BCE or CE presence
    m = re.search(r'(\d{2,4})\s*(BCE|CE)', s, flags=re.I)
    if m:
        num = int(m.group(1))
        era = m.group(2).upper()
        return (f"{num} {era}", num)
    # Negative number like -3400
    m = re.match(r'^\s*-(\d{3,4})\s*$', s)
    if m:
        num = int(m.group(1))
        # negative interpreted as BCE
        return (f"{num} BCE", num)
    # Plain number
    m = re.match(r'^\s*(\d{2,4})\s*$', s)
    if m:
        num = int(m.group(1))
        # heuristic: if >= 1000 assume BCE (older), else assume CE
        if num >= 1000:
            return (f"{num} BCE", num)
        else:
            return (f"{num} CE", num)
    # Try to extract first number in text
    m = re.search(r'(\d{2,4})', s)
    if m:
        num = int(m.group(1))
        if num >= 1000:
            return (f"{num} BCE", num)
        else:
            return (f"{num} CE", num)
    # unable to parse
    return (s, "")

# Create columns
if 'chronology_bce' not in df.columns:
    df['chronology_bce'] = ""
if 'year' not in df.columns:
    df['year'] = ""

# If we have a selected column, parse values from it
if selected:
    for idx, val in df[selected].fillna("").astype(str).items():
        chron, yr = parse_to_chronology(val)
        df.at[idx, 'chronology_bce'] = chron
        df.at[idx, 'year'] = yr
else:
    # No selected column - leave empty but warn
    print("Warning: no date column selected; 'chronology_bce' and 'year' are empty. Please populate them manually.")
    
# If chronology_bce already existed but was different, try not to overwrite non-empty values
# (We already overwrote from selected; if selected==chronology_bce this is fine.)

# Show a preview of parsed results
print("\nParsed chronology preview (first 10 rows):")
print(df[['id','symbol_name','chronology_bce','year']].head(10).to_string(index=False))

# Backup original CSV and write updated CSV
shutil.copyfile(DATA_PATH, BACKUP_PATH)
df.to_csv(DATA_PATH, index=False)
print(f"\nWrote cleaned CSV to {DATA_PATH} (backup saved to {BACKUP_PATH})")
print("If anything looks wrong, restore backup and adjust your source chronology values manually.")
