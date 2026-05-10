# =========================================================
# DEEP HEART PRO - FINAL APP.PY
# =========================================================

import streamlit as st
import database_helper as db
import auth
import model_handler as mh
import pandas as pd
from datetime import datetime
import pytz

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Deep Heart Pro",
    page_icon="🫀",
    layout="wide"
)

# =========================================================
# CONSTANTS
# =========================================================

LOW_RISK_THRESHOLD = 0.30
MODERATE_RISK_THRESHOLD = 0.45
HIGH_RISK_THRESHOLD = 0.75

GENDER_MAP = {"Male": 1, "Female": 0}

CP_MAP = {
    "Typical Angina": 0,
    "Atypical Angina": 1,
    "Non-Anginal Pain": 2,
    "Asymptomatic": 3
}

RESTECG_MAP = {
    "Normal": 0,
    "ST-T Wave Abnormality": 1,
    "Left Ventricular Hypertrophy": 2
}

SLOPE_MAP = {
    "Up": 0,
    "Flat": 1,
    "Down": 2
}

THAL_MAP = {
    "Normal": 1,
    "Fixed Defect": 2,
    "Reversible Defect": 3
}

REV_GENDER_MAP = {v: k for k, v in GENDER_MAP.items()}
REV_CP_MAP = {v: k for k, v in CP_MAP.items()}
REV_RESTECG_MAP = {v: k for k, v in RESTECG_MAP.items()}
REV_SLOPE_MAP = {v: k for k, v in SLOPE_MAP.items()}
REV_THAL_MAP = {v: k for k, v in THAL_MAP.items()}

# =========================================================
# DATABASE INIT
# =========================================================

@st.cache_resource
def initialize_database():
    db.init_db()

initialize_database()

# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

if "editing_patient_id" not in st.session_state:
    st.session_state.editing_patient_id = None

if "editing_record_id" not in st.session_state:
    st.session_state.editing_record_id = None

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def calculate_risk_status(prob):

    if prob < LOW_RISK_THRESHOLD:
        return "🟢 Low Risk"

    elif prob < MODERATE_RISK_THRESHOLD:
        return "🟡 Moderate Risk"

    elif prob < HIGH_RISK_THRESHOLD:
        return "🟠 High Risk"

    return "🔴 Critical Risk"


def validate_patient(name, contact):

    if not name.strip():
        return False, "Patient name required"

    if not contact.strip():
        return False, "Contact required"

    return True, "Success"

# =========================================================
# AUTH FLOW
# =========================================================

if not st.session_state.logged_in:

    if st.session_state.auth_mode == "login":
        auth.login_page()

    elif st.session_state.auth_mode == "signup":
        auth.signup_page()

    elif st.session_state.auth_mode == "forgot":
        auth.forgot_password_page()

# =========================================================
# MAIN APPLICATION
# =========================================================

else:

    # =====================================================
    # SIDEBAR
    # =====================================================

    st.sidebar.title(f"👨‍⚕️ Dr. {st.session_state.user_name}")

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Patients",
            "Add Patient",
            "Medical Records",
            "Logout"
        ]
    )

    # =====================================================
    # LOGOUT
    # =====================================================

    if menu == "Logout":

        st.session_state.logged_in = False
        st.session_state.auth_mode = "login"

        st.rerun()

    # =====================================================
    # DASHBOARD
    # =====================================================

    elif menu == "Dashboard":

        st.title("📈 Clinical Dashboard")

        patients_df = db.get_patients(
            st.session_state.user_id
        )

        total_patients = len(patients_df)

        all_probs = []

        if not patients_df.empty:

            for _, patient in patients_df.iterrows():

                recs = db.get_records(patient["id"])

                if not recs.empty:
                    all_probs.append(recs.iloc[0]["Probability"])

        high_risk = len(
            [x for x in all_probs if x >= MODERATE_RISK_THRESHOLD]
        )

        critical_risk = len(
            [x for x in all_probs if x >= HIGH_RISK_THRESHOLD]
        )

        avg_risk = (
            round(sum(all_probs) / len(all_probs) * 100, 1)
            if all_probs else 0
        )

        pak_tz = pytz.timezone("Asia/Karachi")

        pkt_now = datetime.now(pak_tz).strftime("%I:%M %p")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total Patients", total_patients)
        c2.metric("High Risk", high_risk)
        c3.metric("Critical Cases", critical_risk)
        c4.metric("Average Risk", f"{avg_risk}%")

        st.write("---")

        st.subheader("📊 Risk Distribution")

        if all_probs:

            risk_df = pd.DataFrame({
                "Risk Probability": [x * 100 for x in all_probs]
            })

            st.bar_chart(risk_df)

        st.caption(f"Last Updated (PKT): {pkt_now}")

    # =====================================================
    # PATIENTS
    # =====================================================

    elif menu == "Patients":

        st.title("🧑 Patients List")

        patients_df = db.get_patients(
            st.session_state.user_id
        )

        patient_data = []

        for _, patient in patients_df.iterrows():

            records = db.get_records(patient["id"])

            if not records.empty:

                latest = records.iloc[0]

                prob = latest["Probability"]

                patient_data.append({
                    "ID": patient["id"],
                    "Name": patient["name"],
                    "Age": patient["age"],
                    "Contact": patient["contact_no"],
                    "Probability": f"{prob * 100:.1f}%",
                    "Status": calculate_risk_status(prob),
                    "Last Visit": latest["visit_date"]
                })

            else:

                patient_data.append({
                    "ID": patient["id"],
                    "Name": patient["name"],
                    "Age": patient["age"],
                    "Contact": patient["contact_no"],
                    "Probability": "N/A",
                    "Status": "⚪ No Data",
                    "Last Visit": "No History"
                })

        df = pd.DataFrame(patient_data)

        search = st.text_input(
            "🔍 Search Patients"
        )

        if search:

            df = df[
                df["Name"].str.contains(
                    search,
                    case=False,
                    na=False
                ) |
                df["Contact"].str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.write("---")

        if not df.empty:

            patient_ids = df["ID"].tolist()

            selected_patient = st.selectbox(
                "Select Patient",
                patient_ids,
                format_func=lambda x:
                f"{df[df['ID']==x]['Name'].iloc[0]} (ID: {x})"
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button("✏ Edit Patient"):

                    st.session_state.editing_patient_id = selected_patient

            with c2:

                if st.button("🗑 Delete Patient"):

                    db.delete_patient(selected_patient)

                    st.success("Patient deleted successfully")

                    st.rerun()

        # =================================================
        # EDIT PATIENT
        # =================================================

        if st.session_state.editing_patient_id is not None:

            patient_df = db.get_patients(
                st.session_state.user_id,
                st.session_state.editing_patient_id
            )

            if not patient_df.empty:

                patient = patient_df.iloc[0]

                with st.expander(
                    f"Edit Patient: {patient['name']}",
                    expanded=True
                ):

                    with st.form("edit_patient_form"):

                        edit_name = st.text_input(
                            "Patient Name",
                            value=patient["name"]
                        )

                        edit_contact = st.text_input(
                            "Contact",
                            value=patient["contact_no"]
                        )

                        edit_age = st.number_input(
                            "Age",
                            min_value=1,
                            max_value=120,
                            value=int(patient["age"])
                        )

                        col1, col2 = st.columns(2)

                        with col1:

                            if st.form_submit_button("Update"):

                                db.update_patient(
                                    st.session_state.editing_patient_id,
                                    edit_name,
                                    edit_contact,
                                    edit_age
                                )

                                st.success("Patient updated")

                                st.session_state.editing_patient_id = None

                                st.rerun()

                        with col2:

                            if st.form_submit_button("Cancel"):

                                st.session_state.editing_patient_id = None

                                st.rerun()

    # =====================================================
    # ADD PATIENT
    # =====================================================

    elif menu == "Add Patient":

        st.title("🩺 Cardiac Risk Analysis")

        existing_patients = db.get_patients(
            st.session_state.user_id
        )

        options = ["-- Register New Patient --"]

        if not existing_patients.empty:

            options += (
                existing_patients["name"] +
                " | " +
                existing_patients["contact_no"]
            ).tolist()

        selection = st.selectbox(
            "Select Patient",
            options
        )

        with st.form("patient_form"):

            st.subheader("Patient Information")

            if selection == "-- Register New Patient --":

                c1, c2, c3 = st.columns(3)

                p_name = c1.text_input("Full Name")

                p_age = c2.number_input(
                    "Age",
                    min_value=1,
                    max_value=120,
                    value=30
                )

                p_contact = c3.text_input(
                    "Contact No"
                )

                is_new = True
                p_id = None

            else:

                selected_contact = selection.split(" | ")[-1]

                p_info = existing_patients[
                    existing_patients["contact_no"] ==
                    selected_contact
                ].iloc[0]

                st.info(
                    f"{p_info['name']} | Age: {p_info['age']}"
                )

                p_name = p_info["name"]
                p_age = p_info["age"]
                p_contact = p_info["contact_no"]
                p_id = p_info["id"]

                is_new = False

            st.write("---")

            st.subheader("Clinical Metrics")

            col1, col2 = st.columns(2)

            with col1:

                gender = st.selectbox(
                    "Gender",
                    list(GENDER_MAP.keys())
                )

                chest_pain = st.selectbox(
                    "Chest Pain Type",
                    list(CP_MAP.keys())
                )

                rbp = st.number_input(
                    "Resting Blood Pressure",
                    min_value=50,
                    max_value=300,
                    value=120
                )

                chol = st.number_input(
                    "Cholesterol",
                    min_value=50,
                    max_value=700,
                    value=200
                )

                fbs = st.selectbox(
                    "Fasting Blood Sugar > 120",
                    [0, 1]
                )

                restecg = st.selectbox(
                    "Rest ECG",
                    list(RESTECG_MAP.keys())
                )

            with col2:

                mhr = st.number_input(
                    "Max Heart Rate",
                    min_value=30,
                    max_value=250,
                    value=150
                )

                eia = st.selectbox(
                    "Exercise Induced Angina",
                    [0, 1]
                )

                st_dep = st.number_input(
                    "ST Depression",
                    value=0.0
                )

                slope = st.selectbox(
                    "ST Slope",
                    list(SLOPE_MAP.keys())
                )

                vessels = st.number_input(
                    "Major Vessels",
                    min_value=0,
                    max_value=4,
                    value=0
                )

                thal = st.selectbox(
                    "Thalassemia",
                    list(THAL_MAP.keys())
                )

            submitted = st.form_submit_button(
                "Run Analysis"
            )

            if submitted:

                valid, msg = validate_patient(
                    p_name,
                    p_contact
                )

                if not valid:

                    st.error(msg)

                else:

                    input_data = {
                        "Age": p_age,
                        "Gender": GENDER_MAP[gender],
                        "ChestPainType": CP_MAP[chest_pain],
                        "RestingBloodPressure": rbp,
                        "Cholesterol": chol,
                        "FastingBloodSugar": fbs,
                        "RestECG": RESTECG_MAP[restecg],
                        "MaxHeartRate": mhr,
                        "ExerciseInducedAngina": eia,
                        "ST_Depression": st_dep,
                        "ST_Slope": SLOPE_MAP[slope],
                        "MajorVessels": vessels,
                        "Thalassemia": THAL_MAP[thal]
                    }

                    with st.spinner(
                        "Analyzing cardiac risk..."
                    ):

                        try:

                            target, prob, category, status = mh.predict_heart_risk(
                                input_data
                            )

                            if status == "Success":

                                if is_new:

                                    existing = existing_patients[
                                        existing_patients["contact_no"] ==
                                        p_contact
                                    ]

                                    if existing.empty:

                                        p_id = db.create_patient(
                                            st.session_state.user_id,
                                            p_name,
                                            p_contact,
                                            p_age
                                        )

                                    else:

                                        p_id = existing.iloc[0]["id"]

                                db.create_medical_record(
                                    p_id,
                                    input_data,
                                    target,
                                    prob
                                )

                                st.success(
                                    f"""
                                    Analysis Complete

                                    Risk Category: {category}
                                    Probability: {prob * 100:.1f}%
                                    """
                                )

                                st.progress(min(prob, 1.0))

                            else:

                                st.error(status)

                        except Exception as e:

                            st.error(f"Prediction Error: {e}")

    # =====================================================
    # MEDICAL RECORDS (FIXED & OPTIMIZED)
    # =====================================================
    
    elif menu == "Medical Records":
    
        st.title("📋 Medical Records")
    
        # -------------------------------------------------
        # STEP 1: Fetch records directly by doctor
        # -------------------------------------------------
        all_records = db.get_all_medical_records_by_doctor(
            st.session_state.user_id
        )
    
        # -------------------------------------------------
        # STEP 2: Handle empty case
        # -------------------------------------------------
        if all_records is None or all_records.empty:
            st.info("No medical records found.")
            st.stop()
    
        # -------------------------------------------------
        # STEP 3: Safety check (prevents KeyError crash)
        # -------------------------------------------------
        if "id" not in all_records.columns:
            st.error("Database error: 'id' column missing in medical records")
            st.write(all_records.columns)
            st.stop()
    
        # -------------------------------------------------
        # STEP 4: Get patient details
        # -------------------------------------------------
        patients_df = db.get_patients(st.session_state.user_id)
    
        all_records = all_records.merge(
            patients_df[["id", "name", "contact_no"]],
            left_on="patient_id",
            right_on="id",
            how="left"
        )
    
        all_records.rename(columns={
            "name": "Patient",
            "contact_no": "Contact"
        }, inplace=True)
    
        # -------------------------------------------------
        # STEP 5: Decode values
        # -------------------------------------------------
        all_records["Gender"] = all_records["Gender"].map(REV_GENDER_MAP)
        all_records["ChestPainType"] = all_records["ChestPainType"].map(REV_CP_MAP)
        all_records["RestECG"] = all_records["RestECG"].map(REV_RESTECG_MAP)
        all_records["ST_Slope"] = all_records["ST_Slope"].map(REV_SLOPE_MAP)
        all_records["Thalassemia"] = all_records["Thalassemia"].map(REV_THAL_MAP)
    
        all_records["Probability"] = all_records["Probability"].apply(
            lambda x: f"{x * 100:.1f}%"
        )
    
        # -------------------------------------------------
        # STEP 6: Sort latest first
        # -------------------------------------------------
        all_records = all_records.sort_values(
            by="visit_date",
            ascending=False
        )
    
        # -------------------------------------------------
        # STEP 7: Show table
        # -------------------------------------------------
        st.dataframe(
            all_records,
            use_container_width=True,
            hide_index=True
        )
    
        st.write("---")
    
        # -------------------------------------------------
        # STEP 8: Select record
        # -------------------------------------------------
        if "record_id" not in all_records.columns:
            st.error("Missing record_id column")
            st.write(all_records.columns)
            st.stop()
        
        record_ids = all_records["record_id"].tolist()    

        selected_record = st.selectbox(
            "Select Medical Record",
            record_ids,
            format_func=lambda x: f"Record #{x}"
        )
    
        # -------------------------------------------------
        # STEP 9: Actions
        # -------------------------------------------------
        c1, c2 = st.columns(2)
    
        with c1:
            if st.button("✏ Edit Record"):
                st.session_state.editing_record_id = selected_record
    
        with c2:
            if st.button("🗑 Delete Record"):
    
                db.delete_medical_record(selected_record)
    
                st.success("Medical record deleted")
                st.rerun()
    
        # =================================================
        # STEP 10: EDIT RECORD SECTION
        # =================================================
        if st.session_state.get("editing_record_id"):
    
            rec = all_records[
                all_records["id"] == st.session_state.editing_record_id
            ].iloc[0]
    
            with st.expander(f"Edit Record #{rec['id']}", expanded=True):
    
                with st.form("edit_record_form"):
    
                    col1, col2 = st.columns(2)
    
                    with col1:
    
                        edit_age = st.number_input("Age", value=int(rec["Age"]))
                        edit_gender = st.selectbox("Gender", list(GENDER_MAP.keys()), index=int(rec["Gender"]))
                        edit_cp = st.selectbox("Chest Pain Type", list(CP_MAP.keys()), index=int(rec["ChestPainType"]))
                        edit_rbp = st.number_input("Blood Pressure", value=int(rec["RestingBloodPressure"]))
                        edit_chol = st.number_input("Cholesterol", value=int(rec["Cholesterol"]))
                        edit_fbs = st.selectbox("FBS", [0, 1], index=int(rec["FastingBloodSugar"]))
                        edit_restecg = st.selectbox("Rest ECG", list(RESTECG_MAP.keys()), index=int(rec["RestECG"]))
    
                    with col2:
    
                        edit_mhr = st.number_input("Max Heart Rate", value=int(rec["MaxHeartRate"]))
                        edit_eia = st.selectbox("Angina", [0, 1], index=int(rec["ExerciseInducedAngina"]))
                        edit_st_dep = st.number_input("ST Depression", value=float(rec["ST_Depression"]))
                        edit_slope = st.selectbox("ST Slope", list(SLOPE_MAP.keys()), index=int(rec["ST_Slope"]))
                        edit_vessels = st.number_input("Vessels", value=int(rec["MajorVessels"]))
                        edit_thal = st.selectbox("Thalassemia", list(THAL_MAP.keys()), index=int(rec["Thalassemia"]))
    
                    if st.form_submit_button("Update Record"):
    
                        updated_data = {
                            "Age": edit_age,
                            "Gender": GENDER_MAP[edit_gender],
                            "ChestPainType": CP_MAP[edit_cp],
                            "RestingBloodPressure": edit_rbp,
                            "Cholesterol": edit_chol,
                            "FastingBloodSugar": edit_fbs,
                            "RestECG": RESTECG_MAP[edit_restecg],
                            "MaxHeartRate": edit_mhr,
                            "ExerciseInducedAngina": edit_eia,
                            "ST_Depression": edit_st_dep,
                            "ST_Slope": SLOPE_MAP[edit_slope],
                            "MajorVessels": edit_vessels,
                            "Thalassemia": THAL_MAP[edit_thal]
                        }
    
                        target, prob, cat, status = mh.predict_heart_risk(updated_data)
    
                        db.update_medical_record(
                            st.session_state.editing_record_id,
                            updated_data,
                            target,
                            prob
                        )
    
                        st.success("Record updated successfully")
                        st.session_state.editing_record_id = None
                        st.rerun()
    
        else:
            st.info("No medical records found.")
