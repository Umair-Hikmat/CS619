import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "deep_heart_pro.db"

def init_db():
    """Initializes the database with your specific schema and relationship constraints."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # 1. DOCTORS TABLE
        cursor.execute('''CREATE TABLE IF NOT EXISTS doctors
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          first_name TEXT, last_name TEXT, email TEXT UNIQUE,
                          contact_no TEXT, password TEXT, qualification TEXT, dob DATE,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # 2. PATIENTS TABLE
        cursor.execute('''CREATE TABLE IF NOT EXISTS patients
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          doc_id INTEGER, name TEXT, contact_no TEXT, age INTEGER,
                          FOREIGN KEY(doc_id) REFERENCES doctors(id))''')

        # 3. MEDICAL RECORDS TABLE (13 Features + Target + Probability)
        cursor.execute('''CREATE TABLE IF NOT EXISTS records
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER,
                          Age INTEGER, Gender INTEGER, ChestPainType INTEGER,
                          RestingBloodPressure INTEGER, Cholesterol INTEGER,
                          FastingBloodSugar INTEGER, RestECG INTEGER, MaxHeartRate INTEGER,
                          ExerciseInducedAngina INTEGER, ST_Depression REAL,
                          ST_Slope INTEGER, MajorVessels INTEGER, Thalassemia INTEGER,
                          Target INTEGER, Probability REAL, visit_date TIMESTAMP,
                          FOREIGN KEY(patient_id) REFERENCES patients(id))''')
        conn.commit()

# ==========================================
# --- AUTHENTICATION ---
# ==========================================

def verify_login(email, password):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, first_name, last_name FROM doctors WHERE email=? AND password=?", (email, password))
        return cursor.fetchone()

# ==========================================
# --- DOCTOR CRUD ---
# ==========================================

def create_doctor(f_name, l_name, email, contact, pwd, qual, dob):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""INSERT INTO doctors (first_name, last_name, email, contact_no, password, qualification, dob)
                         VALUES (?,?,?,?,?,?,?)""", (f_name, l_name, email, contact, pwd, qual, str(dob)))
            return True
    except sqlite3.IntegrityError: return False

def get_doctors(doc_ids=None):
    """Retrieves 1 (int), multiple (list), or all (None) doctors."""
    with sqlite3.connect(DB_NAME) as conn:
        if doc_ids is None:
            return pd.read_sql("SELECT * FROM doctors", conn)
        ids = [doc_ids] if isinstance(doc_ids, int) else doc_ids
        id_tuple = str(tuple(ids)).replace(',)', ')')
        return pd.read_sql(f"SELECT * FROM doctors WHERE id IN {id_tuple}", conn)

def update_doctor(doc_id, f_name, l_name, contact, qual):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("UPDATE doctors SET first_name=?, last_name=?, contact_no=?, qualification=? WHERE id=?",
                     (f_name, l_name, contact, qual, doc_id))

def delete_doctor(doc_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM doctors WHERE id=?", (doc_id,))

# ==========================================
# --- PATIENT CRUD ---
# ==========================================

def create_patient(doc_id, name, contact, age):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO patients (doc_id, name, contact_no, age) VALUES (?,?,?,?)",
                     (doc_id, name, contact, age))
        return cursor.lastrowid # Return the ID of the newly created patient

def get_patients(doc_id, patient_ids=None):
    """Retrieves 1, multiple, or all patients for a specific doctor."""
    with sqlite3.connect(DB_NAME) as conn:
        if patient_ids is None:
            query = f"SELECT * FROM patients WHERE doc_id={doc_id}"
        else:
            ids = [patient_ids] if isinstance(patient_ids, int) else patient_ids
            id_tuple = str(tuple(ids)).replace(',)', ')')
            query = f"SELECT * FROM patients WHERE doc_id={doc_id} AND id IN {id_tuple}"
        return pd.read_sql(query, conn)

def update_patient(p_id, name, contact, age):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("UPDATE patients SET name=?, contact_no=?, age=? WHERE id=?", (name, contact, age, p_id))

def delete_patient(p_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM records WHERE patient_id=?", (p_id,))
        conn.execute("DELETE FROM patients WHERE id=?", (p_id,))

# ==========================================
# --- MEDICAL RECORD CRUD ---
# ==========================================

def create_medical_record(patient_id, data_dict, target, prob):
    with sqlite3.connect(DB_NAME) as conn:
        vals = list(data_dict.values())
        query = """INSERT INTO records (patient_id, Age, Gender, ChestPainType, RestingBloodPressure,
                   Cholesterol, FastingBloodSugar, RestECG, MaxHeartRate, ExerciseInducedAngina,
                   ST_Depression, ST_Slope, MajorVessels, Thalassemia, Target, Probability, visit_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)"""
        conn.execute(query, [patient_id] + vals + [target, prob])

def get_records(patient_id, record_ids=None):
    """Retrieves 1, multiple, or all records for a patient."""
    with sqlite3.connect(DB_NAME) as conn:
        if record_ids is None:
            query = f"SELECT * FROM records WHERE patient_id={patient_id} ORDER BY visit_date DESC"
        else:
            ids = [record_ids] if isinstance(record_ids, int) else record_ids
            id_tuple = str(tuple(ids)).replace(',)', ')')
            query = f"SELECT * FROM records WHERE patient_id={patient_id} AND id IN {id_tuple} ORDER BY visit_date DESC"
        return pd.read_sql(query, conn)

def update_medical_record(record_id, data_dict, target, prob):
    with sqlite3.connect(DB_NAME) as conn:
        vals = list(data_dict.values())
        query = """UPDATE records SET
                   Age=?, Gender=?, ChestPainType=?, RestingBloodPressure=?,
                   Cholesterol=?, FastingBloodSugar=?, RestECG=?, MaxHeartRate=?,
                   ExerciseInducedAngina=?, ST_Depression=?, ST_Slope=?,
                   MajorVessels=?, Thalassemia=?, Target=?, Probability=?,
                   visit_date=CURRENT_TIMESTAMP WHERE id=?"""
        conn.execute(query, vals + [target, prob, record_id])

def delete_medical_record(record_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM records WHERE id=?", (record_id,))
