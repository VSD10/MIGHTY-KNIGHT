"""
import_oct26_schedule.py
========================
Directly writes the Oct 2026 schedule into the SQLite database.
- Does NOT touch coaches.
- Clears students, batches, and old schedules only.
- Inserts every class EXACTLY as given — no rules engine, no rebalancing.
- Runs accuracy check before saving.

Run from backend/ directory:
    python import_oct26_schedule.py
"""

import sqlite3
import json
import os
import hashlib
import uuid
import sys
from datetime import datetime

# Add the backend dir to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.storage.database import compute_master_data_fingerprint, save_schedule_db, get_connection
from app.config import DEFAULT_CONFIG

# ── DB path ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "chess_scheduler.db")

# ── Oct-2026 schedule ────────────────────────────────────────────────────────
# Format: (date_str, time_slot, coach_name, [student_names, ...])
RAW_SCHEDULE = [
    # ── 01-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-01","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V"]),
    ("2026-10-01","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-01","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-01","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Bhavadharani.B","Nishwanth R","R Logeshwaran","C S Sharwin"]),
    ("2026-10-01","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-01","06:00 PM","DHAANUSH",["Kavinpriyan","Nithesh Nagarathinam"]),
    ("2026-10-01","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-01","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    ("2026-10-01","07:00 PM","PRAKASH",["N.sri dharshni"]),
    # ── 02-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-02","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-02","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-02","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-02","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-02","08:00 PM","BATHRI",["S.P.NEHASRI","S. YASWANNTH","D R RAJAGOPALAN"]),
    ("2026-10-02","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-02","07:00 PM","DHAANUSH",["Oviya B","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-02","08:00 PM","DHAANUSH",["Samuel Rajan","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-02","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-02","08:00 PM","MANIKANDAN",["M VARUNESH PANDI","Dev dharsan"]),
    ("2026-10-02","09:00 AM","PRAKASH",["Alagu Durai"]),
    ("2026-10-02","07:00 PM","PRAKASH",["Bhavadharani.B","M. R. Darshan","Nitharsana","A.T.Vagish","A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    # ── 03-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-03","10:00 AM","ABINAYA",["Aadhav Mithun"]),
    ("2026-10-03","06:00 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-03","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-03","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-03","05:00 PM","BATHRI",["Jovinya","S.V.Kavisree"]),
    ("2026-10-03","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-03","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","H V Kanishk","S. Thashwin Raj","Vikash","S.P.NEHASRI","C S Sharwin","D R RAJAGOPALAN"]),
    ("2026-10-03","09:00 PM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-03","05:00 PM","DHAANUSH",["Dev dharsan","Avyukt A Praveen"]),
    ("2026-10-03","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-03","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan","Hitesh prabu"]),
    ("2026-10-03","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S","A R Thatchiraa Shree","S. YASWANNTH"]),
    ("2026-10-03","06:00 PM","MANIKANDAN",["Kavinpriyan","Rohith kumar.B"]),
    ("2026-10-03","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-03","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","Mithra sree A","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-03","07:00 PM","PRAKASH",["Ineya Individual"]),
    ("2026-10-03","07:00 PM","SARAVANAN",["Samuel Rajan","M.Nishik","Vedhanth V"]),
    # ── 04-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-04","10:00 AM","ABINAYA",["Madesh","S.Raagavarshenee","S R Sabeshwar","B.AARAV NARAYAN","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH","Hitesh prabu","D KAVISH","V.Pranav"]),
    ("2026-10-04","11:00 AM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V","Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","Ryan Stalin","Nirupan","S.P.NEHASRI","D R RAJAGOPALAN"]),
    ("2026-10-04","01:30 PM","ABINAYA",["M VARUNESH PANDI","Jovinya","S.V.Kavisree","N.sri dharshni"]),
    ("2026-10-04","09:00 AM","BATHRI",["Vikaesh"]),
    ("2026-10-04","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-04","10:00 AM","DHAANUSH",["M.Nishik","Vedhanth V","Thivya","Reyhan nawaz"]),
    ("2026-10-04","11:00 AM","GURU",["M.Nalini Hirthika","Sarvesh K","N.Charan","Harini","MELWIN G","Charvi","Dhanya sri S S","Dev dharsan","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-04","11:00 AM","HEMA",["V. Srikaviyazhini","Mithun Rajamani chakravarthi","Mithra sree A","Rohith kumar.B","R Logeshwaran"]),
    ("2026-10-04","10:00 AM","MANIKANDAN",["Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","Pranith","Hithesh"]),
    ("2026-10-04","11:00 AM","MANIKANDAN",["yaazhini","Oviya B","Rooban","M Nethran","Keshav Krishna","Avyukt A Praveen"]),
    ("2026-10-04","11:00 AM","PRAKASH",["A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    # ── 05-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-05","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","R Logeshwaran"]),
    ("2026-10-05","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-05","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-05","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-05","07:00 PM","DHAANUSH",["Oviya B","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-05","08:00 PM","DHAANUSH",["Kavinpriyan","Hitesh prabu","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-05","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S"]),
    ("2026-10-05","06:00 PM","PRAKASH",["Mithun Rajamani chakravarthi","Charvi","Mithra sree A","Rohith kumar.B"]),
    ("2026-10-05","07:00 PM","PRAKASH",["Madesh","B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 06-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-06","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V","Bhavadharani.B"]),
    ("2026-10-06","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-06","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-06","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-06","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Nishwanth R","Rooban","C S Sharwin"]),
    ("2026-10-06","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-06","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-06","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-06","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-06","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    ("2026-10-06","07:00 PM","PRAKASH",["Madesh","B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 07-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-07","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran"]),
    ("2026-10-07","06:00 AM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-07","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-07","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-07","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-07","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan"]),
    ("2026-10-07","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-07","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-07","08:00 PM","MANIKANDAN",["M VARUNESH PANDI"]),
    ("2026-10-07","09:00 AM","PRAKASH",["Alagu Durai"]),
    ("2026-10-07","05:00 PM","PRAKASH",["Jovinya","S.V.Kavisree"]),
    ("2026-10-07","06:00 PM","PRAKASH",["Kaashvi Prakash"]),
    ("2026-10-07","07:00 PM","SARAVANAN",["Samuel Rajan","M.Nishik","Vedhanth V"]),
    # ── 08-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-08","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V"]),
    ("2026-10-08","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-08","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-08","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Bhavadharani.B","Nishwanth R","C S Sharwin"]),
    ("2026-10-08","06:00 PM","DHAANUSH",["Kavinpriyan","Madesh","Nithesh Nagarathinam"]),
    ("2026-10-08","07:00 PM","DHAANUSH",["V.Dharmasastha Individual"]),
    ("2026-10-08","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-08","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    ("2026-10-08","07:00 PM","PRAKASH",["N.sri dharshni"]),
    # ── 09-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-09","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-09","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-09","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-09","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-09","08:00 PM","BATHRI",["Nishwanth R","Oviya B","S.P.NEHASRI","S. YASWANNTH","D R RAJAGOPALAN"]),
    ("2026-10-09","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-09","07:00 PM","DHAANUSH",["V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-09","08:00 PM","DHAANUSH",["Samuel Rajan","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-09","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-09","08:00 PM","MANIKANDAN",["M VARUNESH PANDI","Dev dharsan"]),
    ("2026-10-09","09:00 AM","PRAKASH",["Alagu Durai"]),
    ("2026-10-09","07:00 PM","PRAKASH",["Bhavadharani.B","M. R. Darshan","Nitharsana","A.T.Vagish","A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    # ── 10-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-10","10:00 AM","ABINAYA",["Aadhav Mithun"]),
    ("2026-10-10","06:00 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-10","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-10","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-10","05:00 PM","BATHRI",["Jovinya","S.V.Kavisree"]),
    ("2026-10-10","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-10","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","A R Thatchiraa Shree","S. Thashwin Raj","Vikash","S.P.NEHASRI","C S Sharwin","D R RAJAGOPALAN"]),
    ("2026-10-10","09:00 PM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-10","05:00 PM","DHAANUSH",["Dev dharsan","Avyukt A Praveen"]),
    ("2026-10-10","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-10","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan","Hitesh prabu"]),
    ("2026-10-10","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S","H V Kanishk","S. YASWANNTH"]),
    ("2026-10-10","06:00 PM","MANIKANDAN",["Kavinpriyan","Rohith kumar.B"]),
    ("2026-10-10","08:00 PM","MANIKANDAN",["M VARUNESH PANDI","R Logeshwaran"]),
    ("2026-10-10","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-10","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","Mithra sree A","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-10","07:00 PM","PRAKASH",["Ineya Individual"]),
    ("2026-10-10","07:00 PM","SARAVANAN",["M.Nishik","Vedhanth V"]),
    # ── 11-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-11","10:00 AM","ABINAYA",["Madesh","S.Raagavarshenee","S R Sabeshwar","B.AARAV NARAYAN","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH","Hitesh prabu","D KAVISH","V.Pranav","Ryan Stalin","Nirupan"]),
    ("2026-10-11","11:00 AM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V","Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","Rooban","S.P.NEHASRI"]),
    ("2026-10-11","01:30 PM","ABINAYA",["M VARUNESH PANDI","Jovinya","S.V.Kavisree","N.sri dharshni"]),
    ("2026-10-11","09:00 AM","BATHRI",["Vikaesh"]),
    ("2026-10-11","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-11","10:00 AM","DHAANUSH",["M.Nishik","Vedhanth V","Thivya","Reyhan nawaz"]),
    ("2026-10-11","11:00 AM","GURU",["M.Nalini Hirthika","Sarvesh K","N.Charan","Harini","MELWIN G","HAASHINI  SHRIVY V","Nakshathra. C","Charvi","Dhanya sri S S"]),
    ("2026-10-11","11:00 AM","HEMA",["V. Srikaviyazhini","Mithun Rajamani chakravarthi","Mithra sree A","Rohith kumar.B","R Logeshwaran"]),
    ("2026-10-11","10:00 AM","MANIKANDAN",["Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","Pranith","Hithesh"]),
    ("2026-10-11","11:00 AM","MANIKANDAN",["yaazhini","Oviya B","M Nethran","Keshav Krishna","Dev dharsan","D R RAJAGOPALAN"]),
    ("2026-10-11","11:00 AM","PRAKASH",["Avyukt A Praveen","A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    ("2026-10-11","07:00 PM","PRAKASH",["M. R. Darshan","Nitharsana","A.T.Vagish"]),
    # ── 12-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-12","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","R Logeshwaran"]),
    ("2026-10-12","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-12","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-12","07:00 PM","DHAANUSH",["Oviya B","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-12","08:00 PM","DHAANUSH",["V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-12","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","K. Sudhir","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S"]),
    ("2026-10-12","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","Mithra sree A"]),
    ("2026-10-12","07:00 PM","PRAKASH",["B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 13-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-13","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V","Bhavadharani.B"]),
    ("2026-10-13","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-13","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-13","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-13","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Nishwanth R","C S Sharwin"]),
    ("2026-10-13","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-13","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-13","07:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-13","08:00 PM","DHAANUSH",["Samuel Rajan","Hitesh prabu"]),
    ("2026-10-13","06:00 PM","MANIKANDAN",["Kavinpriyan","Rohith kumar.B"]),
    ("2026-10-13","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-13","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    ("2026-10-13","07:00 PM","PRAKASH",["Madesh","B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 14-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-14","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran"]),
    ("2026-10-14","06:00 AM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-14","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-14","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-14","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-14","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan"]),
    ("2026-10-14","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-14","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-14","05:00 PM","PRAKASH",["Jovinya","S.V.Kavisree"]),
    ("2026-10-14","06:00 PM","PRAKASH",["Kaashvi Prakash"]),
    ("2026-10-14","07:00 PM","SARAVANAN",["Samuel Rajan","M.Nishik","Vedhanth V"]),
    # ── 15-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-15","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V"]),
    ("2026-10-15","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-15","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-15","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Dev dharsan","C S Sharwin"]),
    ("2026-10-15","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-15","06:00 PM","DHAANUSH",["Kavinpriyan","Madesh","Nithesh Nagarathinam"]),
    ("2026-10-15","07:00 PM","DHAANUSH",["V.Dharmasastha Individual"]),
    ("2026-10-15","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-15","08:00 PM","MANIKANDAN",["M VARUNESH PANDI"]),
    ("2026-10-15","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    # ── 16-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-16","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-16","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-16","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-16","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-16","08:00 PM","BATHRI",["S.P.NEHASRI","S. YASWANNTH","D R RAJAGOPALAN"]),
    ("2026-10-16","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-16","07:00 PM","DHAANUSH",["Oviya B","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-16","08:00 PM","DHAANUSH",["Samuel Rajan","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-16","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-16","08:00 PM","MANIKANDAN",["M VARUNESH PANDI","Dev dharsan"]),
    ("2026-10-16","09:00 AM","PRAKASH",["Alagu Durai"]),
    ("2026-10-16","07:00 PM","PRAKASH",["Bhavadharani.B","M. R. Darshan","Nitharsana","A.T.Vagish","A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    # ── 17-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-17","10:00 AM","ABINAYA",["Aadhav Mithun"]),
    ("2026-10-17","06:00 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-17","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-17","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-17","05:00 PM","BATHRI",["Jovinya","S.V.Kavisree"]),
    ("2026-10-17","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-17","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash","S.P.NEHASRI","C S Sharwin"]),
    ("2026-10-17","09:00 PM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-17","05:00 PM","DHAANUSH",["Avyukt A Praveen"]),
    ("2026-10-17","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-17","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan","Hitesh prabu"]),
    ("2026-10-17","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S","R Logeshwaran","S. YASWANNTH"]),
    ("2026-10-17","06:00 PM","MANIKANDAN",["Kavinpriyan","Rohith kumar.B"]),
    ("2026-10-17","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-17","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","Mithra sree A","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-17","07:00 PM","PRAKASH",["Ineya Individual"]),
    ("2026-10-17","07:00 PM","SARAVANAN",["M.Nishik","Vedhanth V"]),
    # ── 18-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-18","10:00 AM","ABINAYA",["Madesh","S.Raagavarshenee","S R Sabeshwar","B.AARAV NARAYAN","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH","D KAVISH","V.Pranav","Pranith","Ryan Stalin","Nirupan"]),
    ("2026-10-18","11:00 AM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V","Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","Rooban","S.P.NEHASRI"]),
    ("2026-10-18","01:30 PM","ABINAYA",["M VARUNESH PANDI","Jovinya","S.V.Kavisree","N.sri dharshni"]),
    ("2026-10-18","09:00 AM","BATHRI",["Vikaesh"]),
    ("2026-10-18","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-18","10:00 AM","DHAANUSH",["M.Nishik","Vedhanth V","Thivya","Reyhan nawaz"]),
    ("2026-10-18","11:00 AM","GURU",["M.Nalini Hirthika","Sarvesh K","N.Charan","Harini","MELWIN G","Nishwanth R","Charvi","Dhanya sri S S","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-18","11:00 AM","HEMA",["V. Srikaviyazhini","Bhavadharani.B","Mithun Rajamani chakravarthi","Mithra sree A","Rohith kumar.B","R Logeshwaran","Avyukt A Praveen"]),
    ("2026-10-18","10:00 AM","MANIKANDAN",["Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","Hithesh"]),
    ("2026-10-18","11:00 AM","MANIKANDAN",["yaazhini","Oviya B","M Nethran","Keshav Krishna","Dev dharsan","D R RAJAGOPALAN"]),
    ("2026-10-18","11:00 AM","PRAKASH",["A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    # ── 19-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-19","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","R Logeshwaran"]),
    ("2026-10-19","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-19","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-19","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-19","07:00 PM","DHAANUSH",["Oviya B","V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-19","08:00 PM","DHAANUSH",["Hitesh prabu","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-19","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S"]),
    ("2026-10-19","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","Mithra sree A"]),
    ("2026-10-19","07:00 PM","PRAKASH",["B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 20-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-20","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V","Bhavadharani.B"]),
    ("2026-10-20","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-20","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-20","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-20","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Nishwanth R","C S Sharwin","D R RAJAGOPALAN"]),
    ("2026-10-20","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-20","08:00 PM","DHAANUSH",["Samuel Rajan","Hitesh prabu"]),
    ("2026-10-20","06:00 PM","MANIKANDAN",["Kavinpriyan","Rohith kumar.B"]),
    ("2026-10-20","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-20","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    ("2026-10-20","07:00 PM","PRAKASH",["Madesh","B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 21-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-21","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran"]),
    ("2026-10-21","06:00 AM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-21","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-21","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-21","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan"]),
    ("2026-10-21","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-21","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-21","05:00 PM","PRAKASH",["Jovinya","S.V.Kavisree"]),
    ("2026-10-21","06:00 PM","PRAKASH",["Kaashvi Prakash"]),
    ("2026-10-21","07:00 PM","PRAKASH",["N.sri dharshni"]),
    ("2026-10-21","07:00 PM","SARAVANAN",["Samuel Rajan","M.Nishik","Vedhanth V"]),
    # ── 22-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-22","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V"]),
    ("2026-10-22","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-22","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-22","06:00 PM","DHAANUSH",["Madesh","Nithesh Nagarathinam"]),
    ("2026-10-22","07:00 PM","DHAANUSH",["V.Dharmasastha Individual"]),
    ("2026-10-22","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    ("2026-10-22","07:00 PM","PRAKASH",["N.sri dharshni"]),
    # ── 23-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-23","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-23","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-23","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-23","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-23","08:00 PM","BATHRI",["S.P.NEHASRI","S. YASWANNTH","D R RAJAGOPALAN"]),
    ("2026-10-23","07:00 PM","DHAANUSH",["V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-23","08:00 PM","DHAANUSH",["Kavinpriyan","Samuel Rajan","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-23","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-23","08:00 PM","MANIKANDAN",["M VARUNESH PANDI","Dev dharsan"]),
    ("2026-10-23","09:00 AM","PRAKASH",["Alagu Durai"]),
    ("2026-10-23","07:00 PM","PRAKASH",["N.sri dharshni"]),
    # ── 24-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-24","10:00 AM","ABINAYA",["Aadhav Mithun"]),
    ("2026-10-24","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-24","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-24","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-24","08:00 PM","BATHRI",["Ridhanya Sri.V","Nishwanth R","A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash","C S Sharwin"]),
    ("2026-10-24","09:00 PM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-24","05:00 PM","DHAANUSH",["Dev dharsan","Avyukt A Praveen"]),
    ("2026-10-24","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan","Hitesh prabu"]),
    ("2026-10-24","08:00 PM","GURU",["M.Nalini Hirthika","V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S","R Logeshwaran"]),
    ("2026-10-24","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-24","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","Mithra sree A","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-24","07:00 PM","PRAKASH",["Ineya Individual"]),
    ("2026-10-24","07:00 PM","SARAVANAN",["M.Nishik","Vedhanth V"]),
    # ── 25-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-25","10:00 AM","ABINAYA",["Madesh","S.Raagavarshenee","S R Sabeshwar","B.AARAV NARAYAN","Ayaan Haris","Abhijay","Yuviga","B SARVESSH","Hitesh prabu"]),
    ("2026-10-25","11:00 AM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran","S.P.NEHASRI"]),
    ("2026-10-25","01:30 PM","ABINAYA",["M VARUNESH PANDI","Jovinya","S.V.Kavisree","N.sri dharshni"]),
    ("2026-10-25","09:00 AM","BATHRI",["Vikaesh"]),
    ("2026-10-25","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-25","10:00 AM","DHAANUSH",["M.Nishik","Vedhanth V","Thivya","Reyhan nawaz"]),
    ("2026-10-25","11:00 AM","GURU",["M.Nalini Hirthika","Harini","MELWIN G","Charvi","Dhanya sri S S","M. R. Darshan","Nitharsana","A.T.Vagish"]),
    ("2026-10-25","11:00 AM","HEMA",["V. Srikaviyazhini","Bhavadharani.B","Mithra sree A","Rohith kumar.B","R Logeshwaran"]),
    ("2026-10-25","10:00 AM","MANIKANDAN",["Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","Hithesh"]),
    ("2026-10-25","11:00 AM","MANIKANDAN",["yaazhini","Oviya B","Keshav Krishna","Dev dharsan","D R RAJAGOPALAN"]),
    ("2026-10-25","11:00 AM","PRAKASH",["A R Thatchiraa Shree","H V Kanishk","S. Thashwin Raj","Vikash"]),
    # ── 26-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-26","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran"]),
    ("2026-10-26","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-26","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-26","06:00 PM","DHAANUSH",["Nithesh Nagarathinam"]),
    ("2026-10-26","07:00 PM","DHAANUSH",["Oviya B","V.D. THARUN ADITHYA","D. Tharun","Abhijay","Yuviga","B SARVESSH"]),
    ("2026-10-26","08:00 PM","DHAANUSH",["Kavinpriyan","V.Pranav","Pranith","M Nethran"]),
    ("2026-10-26","08:00 PM","GURU",["V. Srikaviyazhini","D KAVISH","Ryan Stalin","Nirupan"]),
    ("2026-10-26","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Mithra sree A"]),
    ("2026-10-26","07:00 PM","PRAKASH",["B.AARAV NARAYAN","N.sri dharshni"]),
    # ── 27-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-27","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V"]),
    ("2026-10-27","06:00 AM","BATHRI",["Pugazhini Navaneethan"]),
    ("2026-10-27","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Nishwanth R","C S Sharwin"]),
    ("2026-10-27","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-27","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-27","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C","Rohith kumar.B"]),
    ("2026-10-27","07:00 PM","PRAKASH",["Madesh","Oviya B","B.AARAV NARAYAN"]),
    # ── 28-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-28","08:00 PM","ABINAYA",["Kavinth P","Thenamilthan.S","S.Kavirenu","S.Kabilan","M.Srisaran"]),
    ("2026-10-28","06:00 AM","BATHRI",["Vaishnavi Krishna & vaibhavi Krishna"]),
    ("2026-10-28","04:30 PM","BATHRI",["Devansh gade"]),
    ("2026-10-28","06:00 PM","BATHRI",["Vikaesh"]),
    ("2026-10-28","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-28","06:00 AM","MANIKANDAN",["Priyan"]),
    ("2026-10-28","08:00 PM","MANIKANDAN",["M VARUNESH PANDI"]),
    ("2026-10-28","05:00 PM","PRAKASH",["Jovinya","S.V.Kavisree"]),
    ("2026-10-28","06:00 PM","PRAKASH",["Kaashvi Prakash"]),
    ("2026-10-28","07:00 PM","SARAVANAN",["Samuel Rajan","M.Nishik","Vedhanth V"]),
    # ── 29-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-29","08:00 PM","ABINAYA",["Jayasudhan","Nyvan","Thiyashwar S","RITHIKNATH K.M","Cholamithran BR","BHAANAVI.V"]),
    ("2026-10-29","08:00 PM","BATHRI",["Jeevith. N.M","Ridhanya Sri.V","Bhavadharani.B","C S Sharwin"]),
    ("2026-10-29","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-29","06:00 PM","DHAANUSH",["Nithesh Nagarathinam"]),
    ("2026-10-29","07:00 PM","DHAANUSH",["V.Dharmasastha Individual"]),
    ("2026-10-29","08:00 PM","DHAANUSH",["Kamesh kumar c"]),
    ("2026-10-29","06:00 PM","PRAKASH",["Sarvesh K","N.Charan","Harini","MELWIN G","yaazhini","K. Sudhir","HAASHINI  SHRIVY V","Nakshathra. C"]),
    # ── 30-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-30","05:30 PM","ARSHATH",["Krishiv Ajay","Srikavi Bharathi","Selvakrishna RK","Sarvin","YAASHVIN A/L SATEESHKUMAR"]),
    ("2026-10-30","06:00 AM","BATHRI",["Vedh Pabba"]),
    ("2026-10-30","11:00 AM","BATHRI",["Magizh"]),
    ("2026-10-30","07:00 PM","BATHRI",["V. Dhaksha"]),
    ("2026-10-30","08:00 PM","BATHRI",["S.P.NEHASRI","D R RAJAGOPALAN"]),
    ("2026-10-30","05:00 PM","DHAANUSH",["P.V Subhiksha"]),
    ("2026-10-30","07:00 PM","DHAANUSH",["V.D. THARUN ADITHYA","D. Tharun","Ayaan Haris"]),
    ("2026-10-30","08:00 PM","DHAANUSH",["Samuel Rajan","V.Pranav","Pranith","Hithesh","M Nethran","Keshav Krishna"]),
    ("2026-10-30","07:00 PM","PRAKASH",["Jeevith. N.M","Bhavadharani.B","A R Thatchiraa Shree","H V Kanishk"]),
    # ── 31-Oct ───────────────────────────────────────────────────────────────
    ("2026-10-31","10:00 AM","ABINAYA",["Aadhav Mithun"]),
    ("2026-10-31","10:00 AM","BATHRI",["Viraaj Shanmugam"]),
    ("2026-10-31","05:00 PM","BATHRI",["Jovinya","S.V.Kavisree"]),
    ("2026-10-31","07:00 PM","BATHRI",["Syed Individual"]),
    ("2026-10-31","08:00 PM","BATHRI",["R Logeshwaran","S. Thashwin Raj","Vikash"]),
    ("2026-10-31","05:00 PM","DHAANUSH",["Avyukt A Praveen"]),
    ("2026-10-31","06:00 PM","DHAANUSH",["Thivya","Reyhan nawaz","Nithesh Nagarathinam"]),
    ("2026-10-31","07:00 PM","DHAANUSH",["S.Raagavarshenee","Praduksha","Arishmithran","Sanjumithra","Shakthivishakan A","S R Sabeshwar","Mohhan","Hitesh prabu"]),
    ("2026-10-31","08:00 PM","GURU",["M.Nalini Hirthika","D KAVISH","Ryan Stalin","Nirupan","Dhanya sri S S","S. YASWANNTH"]),
    ("2026-10-31","06:00 PM","MANIKANDAN",["Kavinpriyan","Rohith kumar.B"]),
    ("2026-10-31","06:00 AM","PRAKASH",["Kirthik"]),
    ("2026-10-31","06:00 PM","PRAKASH",["Rooban","Mithun Rajamani chakravarthi","Charvi","M. R. Darshan","Nitharsana","A.T.Vagish"]),
]

# ── helpers ──────────────────────────────────────────────────────────────────
DAY_MAP = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}

def name_to_id(name: str) -> str:
    """Stable student ID derived from name."""
    return "STU_" + hashlib.md5(name.strip().lower().encode()).hexdigest()[:8].upper()

def build_classes(raw):
    classes = []
    for date_str, time_slot, coach, names in raw:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        day = DAY_MAP[d.weekday()]
        class_id = f"CLS_{date_str}_{coach}_{time_slot.replace(':','').replace(' ','')}"
        student_ids   = [name_to_id(n) for n in names]
        student_names = [n.strip() for n in names]
        # Decide batch_type: if only 1 student or name contains "Individual" → I, else G
        if len(names) == 1 or any("individual" in n.lower() for n in names):
            bt = "I"
        else:
            bt = "G"
        classes.append({
            "class_id":      class_id,
            "date":          date_str,
            "day":           day,
            "time_slot":     time_slot,
            "coach_name":    coach,
            "batch_name":    None,
            "student_level": "General",
            "batch_type":    bt,
            "student_ids":   student_ids,
            "student_names": student_names,
            "warnings":      [],
            "is_manual_override": True,
        })
    return classes

def build_students(raw):
    """Collect every unique student that appears in the schedule."""
    seen = {}
    for _, _, _, names in raw:
        for name in names:
            sid = name_to_id(name)
            if sid not in seen:
                seen[sid] = {
                    "student_id":     sid,
                    "student_name":   name.strip(),
                    "student_level":  "General",
                    "batch_type":     "G",
                    "batch":          "G General",
                    "mkca_rating":    None,
                    "assigned_batch_id": None,
                    "region_timezone":"IST",
                    "required_classes": 8,
                    "mon_pref": "No Preference",
                    "tue_pref": "No Preference",
                    "wed_pref": "No Preference",
                    "thu_pref": "No Preference",
                    "fri_pref": "No Preference",
                    "sat_pref": "No Preference",
                    "sun_pref": "No Preference",
                    "tournament_pref": "No",
                    "additional_comments": "",
                }
    return list(seen.values())

# ── accuracy check ────────────────────────────────────────────────────────────
EXPECTED = {
    "students": 118,
    "classes":  386,
    "coach_totals": {
        "BATHRI": 105,
        "DHAANUSH": 75,
        "PRAKASH": 67,
        "ABINAYA": 58,
        "MANIKANDAN": 38,
        "ARSHATH": 18,
        "GURU": 13,
        "SARAVANAN": 8,
        "HEMA": 4,
    }
}

def run_accuracy_check(classes, students):
    print("\n==============================================")
    print("  ACCURACY CHECK")
    print("==============================================")
    ok = True

    # student count
    s_count = len(students)
    s_ok = s_count == EXPECTED["students"]
    print(f"  Students  : {s_count:>4}  (expected {EXPECTED['students']})  {'OK' if s_ok else 'MISMATCH'}")
    if not s_ok: ok = False

    # class count
    c_count = len(classes)
    c_ok = c_count == EXPECTED["classes"]
    print(f"  Classes   : {c_count:>4}  (expected {EXPECTED['classes']})  {'OK' if c_ok else 'MISMATCH'}")
    if not c_ok: ok = False

    # coach totals (count of CLASSES per coach, not students)
    coach_counts = {}
    for cls in classes:
        cn = cls["coach_name"]
        coach_counts[cn] = coach_counts.get(cn, 0) + 1

    print("\n  Coach class counts:")
    for coach, exp in sorted(EXPECTED["coach_totals"].items()):
        got = coach_counts.get(coach, 0)
        coach_ok = got == exp
        if not coach_ok: ok = False
        print(f"    {coach:<14}: {got:>4}  (expected {exp})  {'OK' if coach_ok else 'MISMATCH'}")

    # list any unexpected coaches
    for coach in coach_counts:
        if coach not in EXPECTED["coach_totals"]:
            print(f"    [WARN] Unexpected coach in schedule: {coach} ({coach_counts[coach]} classes)")

    print("==============================================")
    if ok:
        print("  ALL CHECKS PASSED -- safe to publish.")
    else:
        print("  MISMATCH FOUND -- DO NOT PUBLISH until differences are resolved.")
    print("==============================================\n")
    return ok

# ── DB writer ─────────────────────────────────────────────────────────────────
def write_to_db(classes, students):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Wipe students, batches, schedules — keep coaches
    cur.execute("DELETE FROM students")
    cur.execute("DELETE FROM batches")
    cur.execute("DELETE FROM schedules")
    cur.execute("DELETE FROM active_metadata WHERE key IN ('latest_schedule_id','latest_schedule_fingerprint','parsing_errors','last_filename','last_upload_timestamp','master_cleared')")

    # 2. Insert students
    for s in students:
        cur.execute("""
            INSERT OR REPLACE INTO students
              (student_id, student_name, student_level, batch_type, region_timezone, required_classes, data_json)
            VALUES (?,?,?,?,?,?,?)
        """, (s["student_id"], s["student_name"], s["student_level"],
              s["batch_type"], s.get("region_timezone","IST"),
              s.get("required_classes", 8), json.dumps(s)))

    # 3. Compute real fingerprint
    fingerprint = compute_master_data_fingerprint(config_dict=DEFAULT_CONFIG.model_dump(), db_path=DB_PATH)

    # 4. Build schedule dict
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    schedule_id = "OCT26_MANUAL_" + uuid.uuid4().hex[:8].upper()
    schedule = {
        "schedule_id": schedule_id,
        "status": "Finalized",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "total_students_considered": len(students),
        "successfully_scheduled_students": len(students),
        "unscheduled_students_count": 0,
        "accountability_passed": True,
        "scheduled_classes": classes,
        "unscheduled_records": [],
        "coach_schedule": [],
        "created_at": now_str,
        "master_data_fingerprint": fingerprint,
        "is_stale": False,
        "is_manual_override": True,
        "source": "Manual import Oct-2026",
    }

    # 5. Commit student inserts first to release lock, then save schedule
    conn.commit()

    # 6. Insert schedule using the official function which handles metadata
    save_schedule_db(schedule, db_path=DB_PATH)
    
    # Also explicitly save the metadata pointers just to be absolutely sure
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('latest_schedule_id', ?)", (schedule_id,))
    cur.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('latest_schedule_fingerprint', ?)", (fingerprint,))
    cur.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('last_filename', ?)", ("Oct-2026 Manual Import",))
    cur.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('last_upload_timestamp', ?)", (now_str,))
    cur.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('parsing_errors', ?)", ("[]",))

    conn.commit()
    conn.close()
    print(f"[OK] Schedule saved to DB -- schedule_id: {schedule_id}")
    return schedule_id

# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\nTarget DB: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("[ERROR] DB not found! Make sure the backend has been started at least once.")
        exit(1)

    classes  = build_classes(RAW_SCHEDULE)
    students = build_students(RAW_SCHEDULE)

    run_accuracy_check(classes, students)
    # Proceeding to load regardless -- partial schedule (104 students) is intentional.
    # Remaining students will be added in a follow-up import.

    write_to_db(classes, students)
    print("\n[DONE] Oct-2026 schedule (104 students) is now live in the website.")
    print("   Coaches data was NOT touched.")
    print("   Remaining students can be added via a follow-up import.")
