import sqlite3
import pandas as pd

DB_NAME = "deep_heart_pro.db"

# =========================================================
# INIT DATABASE
# =========================================================

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # ---------------- DOCTORS ----------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE,
            contact_no TEXT,
            password TEXT,
            qualification TEXT,
            dob TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ---------------- PATIENTS ----------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            name TEXT,
            contact_no TEXT,
            age INTEGER,
            FOREIGN KEY(doc_id) REFERENCES doctors(id)
        )
        """)

        # ---------------- RECORDS ----------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,

            Age INTEGER,
            Gender INTEGER,
            ChestPainType INTEGER,
            RestingBloodPressure INTEGER,
            Cholesterol INTEGER,
            FastingBloodSugar INTEGER,
            RestECG INTEGER,
            MaxHeartRate INTEGER,
            ExerciseInducedAngina INTEGER,
            ST_Depression REAL,
            ST_Slope INTEGER,
            MajorVessels INTEGER,
            Thalassemia INTEGER,

            Target INTEGER,
            Probability REAL,

            visit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
        """)

        conn.commit()

# =========================================================
# AUTH
# =========================================================

def verify_login(email, password):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, first_name, last_name
            FROM doctors
            WHERE email=? AND password=?
        """, (email, password))
        return cursor.fetchone()

# =========================================================
# DOCTORS
# =========================================================

def create_doctor(f_name, l_name, email, contact, pwd, qual, dob):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                INSERT INTO doctors
                (first_name, last_name, email, contact_no, password, qualification, dob)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f_name, l_name, email, contact, pwd, qual, dob))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def get_doctors(doc_ids=None):
    with sqlite3.connect(DB_NAME) as conn:

        if doc_ids is None:
            return pd.read_sql("SELECT * FROM doctors", conn)

        ids = [doc_ids] if isinstance(doc_ids, int) else doc_ids
        query = f"""
            SELECT * FROM doctors
            WHERE id IN ({','.join(['?']*len(ids))})
        """
        return pd.read_sql(query, conn, params=ids)


def update_doctor(doc_id, f_name, l_name, contact, qual):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            UPDATE doctors
            SET first_name=?, last_name=?, contact_no=?, qualification=?
            WHERE id=?
        """, (f_name, l_name, contact, qual, doc_id))
        conn.commit()

# =========================================================
# PATIENTS
# =========================================================

def create_patient(doc_id, name, contact, age):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO patients (doc_id, name, contact_no, age)
            VALUES (?, ?, ?, ?)
        """, (doc_id, name, contact, age))
        conn.commit()
        return cursor.lastrowid


def get_patients(doc_id, patient_ids=None):
    with sqlite3.connect(DB_NAME) as conn:

        if patient_ids is None:
            return pd.read_sql(
                "SELECT * FROM patients WHERE doc_id=?",
                conn,
                params=(doc_id,)
            )

        ids = [patient_ids] if isinstance(patient_ids, int) else patient_ids
        query = f"""
            SELECT * FROM patients
            WHERE doc_id=?
            AND id IN ({','.join(['?']*len(ids))})
        """

        return pd.read_sql(query, conn, params=(doc_id, *ids))


def update_patient(p_id, name, contact, age):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            UPDATE patients
            SET name=?, contact_no=?, age=?
            WHERE id=?
        """, (name, contact, age, p_id))
        conn.commit()


def delete_patient(p_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM records WHERE patient_id=?", (p_id,))
        conn.execute("DELETE FROM patients WHERE id=?", (p_id,))
        conn.commit()

# =========================================================
# MEDICAL RECORDS
# =========================================================

def create_medical_record(patient_id, data_dict, target, prob):
    with sqlite3.connect(DB_NAME) as conn:

        values = list(data_dict.values())

        conn.execute("""
            INSERT INTO records (
                patient_id,
                Age, Gender, ChestPainType,
                RestingBloodPressure, Cholesterol,
                FastingBloodSugar, RestECG,
                MaxHeartRate, ExerciseInducedAngina,
                ST_Depression, ST_Slope,
                MajorVessels, Thalassemia,
                Target, Probability,
                visit_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (patient_id, *values, target, prob))

        conn.commit()


def get_records(patient_id, record_ids=None):
    with sqlite3.connect(DB_NAME) as conn:

        if record_ids is None:
            return pd.read_sql("""
                SELECT * FROM records
                WHERE patient_id=?
                ORDER BY visit_date DESC
            """, conn, params=(patient_id,))

        ids = [record_ids] if isinstance(record_ids, int) else record_ids
        query = f"""
            SELECT * FROM records
            WHERE patient_id=?
            AND id IN ({','.join(['?']*len(ids))})
            ORDER BY visit_date DESC
        """

        return pd.read_sql(query, conn, params=(patient_id, *ids))


def update_medical_record(record_id, data_dict, target, prob):
    with sqlite3.connect(DB_NAME) as conn:

        values = list(data_dict.values())

        conn.execute("""
            UPDATE records SET
                Age=?, Gender=?, ChestPainType=?,
                RestingBloodPressure=?, Cholesterol=?,
                FastingBloodSugar=?, RestECG=?,
                MaxHeartRate=?, ExerciseInducedAngina=?,
                ST_Depression=?, ST_Slope=?,
                MajorVessels=?, Thalassemia=?,
                Target=?, Probability=?,
                visit_date=CURRENT_TIMESTAMP
            WHERE id=?
        """, (*values, target, prob, record_id))

        conn.commit()


def delete_medical_record(record_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM records WHERE id=?", (record_id,))
        conn.commit()
