# =========================================================
# DEEP HEART PRO - FINAL FIXED APP.PY
# =========================================================

import streamlit as st
import database_helper as db
import auth
import model_handler as mh
import pandas as pd
from datetime import datetime
import pytz

st.set_page_config(page_title="Deep Heart Pro", page_icon="🫀", layout="wide")

# -----------------------------
# SESSION STATE
# -----------------------------
for key in ["logged_in", "auth_mode", "editing_patient_id", "editing_record_id"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "logged_in" else None

# -----------------------------
# INIT DB
# -----------------------------
@st.cache_resource
def init_db():
    db.init_db()

init_db()

# -----------------------------
# AUTH
# -----------------------------
if not st.session_state.logged_in:
    if st.session_state.auth_mode == "login":
        auth.login_page()
    elif st.session_state.auth_mode == "signup":
        auth.signup_page()
    else:
        auth.forgot_password_page()

# =========================================================
# MAIN APP
# =========================================================
else:

    st.sidebar.title(f"👨‍⚕️ Dr. {st.session_state.user_name}")

    menu = st.sidebar.radio("Navigation",
        ["Dashboard", "Patients", "Add Patient", "Medical Records", "Logout"]
    )

    if menu == "Logout":
        st.session_state.logged_in = False
        st.rerun()

    # =====================================================
    # DASHBOARD (UNCHANGED LOGIC SAFE)
    # =====================================================
    elif menu == "Dashboard":
        st.title("📈 Dashboard")

        patients = db.get_patients(st.session_state.user_id)
        total = len(patients)

        probs = []
        for _, p in patients.iterrows():
            rec = db.get_records(p["id"])
            if not rec.empty:
                probs.append(rec.iloc[0]["Probability"])

        avg = round(sum(probs)/len(probs)*100, 1) if probs else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Patients", total)
        c2.metric("Avg Risk", f"{avg}%")
        c3.metric("Records", len(probs))

    # =====================================================
    # ADD PATIENT (FIXED SAVE + REFRESH)
    # =====================================================
    elif menu == "Add Patient":

        st.title("🩺 Cardiac Analysis")

        patients = db.get_patients(st.session_state.user_id)

        options = ["New Patient"]
        if not patients.empty:
            options += (patients["name"] + " | " + patients["contact_no"]).tolist()

        choice = st.selectbox("Select Patient", options)

        with st.form("form"):

            if choice == "New Patient":
                name = st.text_input("Name")
                age = st.number_input("Age", 1, 120, 30)
                contact = st.text_input("Contact")
                new = True
                pid = None
            else:
                contact = choice.split(" | ")[-1]
                row = patients[patients["contact_no"] == contact].iloc[0]
                name, age, pid = row["name"], row["age"], row["id"]
                new = False

            gender = st.selectbox("Gender", ["Male", "Female"])
            chest = st.selectbox("Chest Pain", ["Typical Angina","Atypical Angina","Non-Anginal Pain","Asymptomatic"])

            submit = st.form_submit_button("Analyze")

            if submit:

                input_data = {
                    "Age": age,
                    "Gender": 1 if gender == "Male" else 0,
                    "ChestPainType": ["Typical Angina","Atypical Angina","Non-Anginal Pain","Asymptomatic"].index(chest),
                    "RestingBloodPressure": 120,
                    "Cholesterol": 200,
                    "FastingBloodSugar": 0,
                    "RestECG": 0,
                    "MaxHeartRate": 150,
                    "ExerciseInducedAngina": 0,
                    "ST_Depression": 0.0,
                    "ST_Slope": 0,
                    "MajorVessels": 0,
                    "Thalassemia": 1
                }

                target, prob, cat, status = mh.predict_heart_risk(input_data)

                if new:
                    pid = db.create_patient(st.session_state.user_id, name, contact, age)

                db.create_medical_record(pid, input_data, target, prob)

                st.success(f"{cat} - {prob:.2f}%")

                st.rerun()   # 🔥 IMPORTANT FIX

    # =====================================================
    # MEDICAL RECORDS (FIXED FULL REFRESH + NO STALE DATA)
    # =====================================================
    elif menu == "Medical Records":

        st.title("📋 Medical Records")

        patients = db.get_patients(st.session_state.user_id)

        all_data = []

        for _, p in patients.iterrows():
            rec = db.get_records(p["id"])
            if not rec.empty:
                rec = rec.copy()
                rec["Patient"] = p["name"]
                rec["Contact"] = p["contact_no"]
                rec["Probability"] = rec["Probability"].apply(lambda x: f"{x:.2f}%")  # FIXED
                all_data.append(rec)

        if all_data:

            df = pd.concat(all_data).sort_values("visit_date", ascending=False)

            st.dataframe(df, use_container_width=True)

            st.write("---")

            selected = st.selectbox("Select Record", df["id"])

            if st.button("Delete"):
                db.delete_medical_record(selected)
                st.rerun()

            if st.button("Edit"):
                st.session_state.editing_record_id = selected

        # =================================================
        # EDIT RECORD (FIXED INDEX + SAFE MAPPING)
        # =================================================
        if st.session_state.editing_record_id:

            record = None

            for _, p in patients.iterrows():
                r = db.get_records(p["id"])
                if not r.empty:
                    m = r[r["id"] == st.session_state.editing_record_id]
                    if not m.empty:
                        record = m.iloc[0]
                        break

            if record is not None:

                with st.form("edit"):

                    age = st.number_input("Age", value=int(record["Age"]))
                    chol = st.number_input("Cholesterol", value=int(record["Cholesterol"]))

                    if st.form_submit_button("Update"):

                        updated = dict(record)
                        updated["Age"] = age
                        updated["Cholesterol"] = chol

                        target, prob, cat, status = mh.predict_heart_risk(updated)

                        db.update_medical_record(
                            st.session_state.editing_record_id,
                            updated,
                            target,
                            prob
                        )

                        st.session_state.editing_record_id = None
                        st.rerun()
