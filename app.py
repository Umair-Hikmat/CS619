import streamlit as st
import database_helper as db
import auth
import model_handler as mh
import pandas as pd
import math
from datetime import datetime
import importlib
import pytz

# Page configuration
st.set_page_config(layout="wide", page_title="Deep Heart Pro")

# --- INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = "login"
# Initialize session state for editing
if 'editing_patient_id' not in st.session_state:
    st.session_state.editing_patient_id = None

importlib.reload(db)
db.init_db()

# --- AUTHENTICATION FLOW ---
if not st.session_state.logged_in:
    if st.session_state.auth_mode == "login":
        auth.login_page()
    elif st.session_state.auth_mode == "signup":
        auth.signup_page()
    elif st.session_state.auth_mode == "forgot":
        auth.forgot_password_page()

# --- MAIN CLINICAL DASHBOARD ---
else:
    st.sidebar.title(f"Dr. {st.session_state.user_name}")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Patients List", "Add New Patient", "Medical Records", "Logout"]) # Added "Medical Records"

    if menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.auth_mode = "login"
        st.rerun()

    elif menu == "Dashboard":
        st.title("📈 Clinical Insights")

        # --- FIXED: PAKISTANI TIME (PKT) ---
        pak_tz = pytz.timezone('Asia/Karachi')
        pkt_now = datetime.now(pak_tz).strftime("%I:%M %p")

        patients_df = db.get_patients(st.session_state.user_id)
        total_p = len(patients_df)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Patients", total_p)
        c2.metric("Screenings", "Live")
        c3.metric("System Status", "Ready")
        c4.metric("Last Update (PKT)", pkt_now)

    elif menu == "Patients List":
        st.title("Patients")

        # 1. FETCH IDENTITY DATA
        patients_df = db.get_patients(st.session_state.user_id)
        summary_list = []

        # 2. FETCH CLINICAL DATA FOR EACH PATIENT
        for _, p in patients_df.iterrows():
            # Get the history for this specific patient ID
            # Records are ordered by visit_date DESC in db.get_records, so iloc[0] is always the latest.
            medical_history = db.get_records(p['id'])

            # Default values if no medical record exists yet
            prob_val = 0.0 # Will store 0-100 percentage
            target_val = "N/A"
            visit_val = "No history"

            if not medical_history.empty:
                latest_rec = medical_history.iloc[0]

                # 'Probability' is already stored as a percentage (0-100) from model_handler.py's return
                prob_val = latest_rec.get('Probability', 0.0)
                target_val = latest_rec.get('Target', "N/A")
                visit_val = latest_rec.get('visit_date', "No history")

            # Combine Identity + Clinical Data into one dictionary
            summary_list.append({
                "ID": p['id'],
                "Name": p['name'],
                "Age": p['age'],
                "Contact": p['contact_no'],
                "Probability": prob_val,
                "Target": target_val,
                "Last Visit": visit_val
            })

        # Create the final DataFrame for the UI
        df = pd.DataFrame(summary_list)

        if df.empty:
            st.info("No patients found in your records.")
        else:
            # --- DISPLAY LOGIC ---
            col_search, col_config, col_export = st.columns([2, 1, 1])
            with col_search:
                search_term = st.text_input("🔍 Search Patients", placeholder="Filter by name...")
                if search_term:
                    df = df[df['Name'].str.contains(search_term, case=False)]

            with col_config:
                all_display_cols = ["Name", "Age", "Contact", "Probability", "Target", "Last Visit", "Status", "Actions"]
                selected_cols = st.multiselect("Columns", all_display_cols,
                                               default=["Name", "Status", "Probability", "Last Visit", "Actions"])

            with col_export:
                # NEW EXPORT LOGIC
                if not df.empty:
                    # Get IDs of currently filtered patients
                    patient_ids_to_export = df['ID'].tolist()
                    all_medical_records_list = []

                    # Fetch all medical records for these patients
                    for pid in patient_ids_to_export:
                        patient_records = db.get_records(pid)
                        if not patient_records.empty:
                            all_medical_records_list.append(patient_records)

                    if all_medical_records_list:
                        full_records_df = pd.concat(all_medical_records_list, ignore_index=True)

                        # Apply reverse mappings for categorical features for better readability
                        rev_gender_map = {1: "Male", 0: "Female/Other"}
                        rev_cp_map = {0: "Typical Angina", 1: "Atypical Angina", 2: "Non-Anginal Pain", 3: "Asymptomatic"}
                        rev_restecg_map = {0: "Normal", 1: "ST-T Wave Abnormality", 2: "Left Ventricular Hypertrophy"}
                        rev_slope_map = {0: "Up", 1: "Flat", 2: "Down"}
                        rev_thal_map = {1: "Normal", 2: "Fixed Defect", 3: "Reversible Defect", 0: "Unknown/N/A"}

                        if 'Gender' in full_records_df.columns:
                            full_records_df['Gender'] = full_records_df['Gender'].map(rev_gender_map).fillna(full_records_df['Gender'])
                        if 'ChestPainType' in full_records_df.columns:
                            full_records_df['ChestPainType'] = full_records_df['ChestPainType'].map(rev_cp_map).fillna(full_records_df['ChestPainType'])
                        if 'RestECG' in full_records_df.columns:
                            full_records_df['RestECG'] = full_records_df['RestECG'].map(rev_restecg_map).fillna(full_records_df['RestECG'])
                        if 'ST_Slope' in full_records_df.columns:
                            full_records_df['ST_Slope'] = full_records_df['ST_Slope'].map(rev_slope_map).fillna(full_records_df['ST_Slope'])
                        if 'Thalassemia' in full_records_df.columns:
                            full_records_df['Thalassemia'] = full_records_df['Thalassemia'].map(rev_thal_map).fillna(full_records_df['Thalassemia'])

                        # Format Probability as percentage for export
                        if 'Probability' in full_records_df.columns:
                            full_records_df['Probability'] = full_records_df['Probability'].round(2).astype(str) + '%'

                        csv_data = full_records_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Export All Records (Filtered Patients) to CSV",
                            data=csv_data,
                            file_name="all_patient_medical_records.csv",
                            mime="text/csv",
                            key="download_all_records",
                            use_container_width=True
                        )
                    else:
                        st.info("No records to export for the filtered patients.")
                else:
                    st.info("No patients found to export records for.")


            # Pagination
            items_per_page = 50
            total_pages = math.ceil(len(df) / items_per_page) if len(df) > 0 else 1
            page = st.sidebar.number_input("Page", min_value=1, max_value=total_pages, step=1)
            df_page = df.iloc[(page - 1) * items_per_page : page * items_per_page].copy()


            st.write("---")
            # Adjust column width for actions if 'Actions' is selected
            col_widths = [0.5] + [2 for _ in selected_cols if _ != "Actions"]
            if "Actions" in selected_cols:
                col_widths.append(3) # Give more space for buttons
            header_cols = st.columns(col_widths)

            select_all = header_cols[0].checkbox("All", key="master_check_patients")

            col_idx = 1
            for col_name in selected_cols:
                header_cols[col_idx].markdown(f"**{col_name}**")
                col_idx += 1

            # Store selected patient IDs for bulk actions
            selected_patient_ids = []

            for _, row in df_page.iterrows():
                row_cols = st.columns(col_widths)
                # Checkbox for selection
                if row_cols[0].checkbox("", value=select_all, key=f"p_select_{row['ID']}"):
                    selected_patient_ids.append(row['ID'])


                # Determine Status text based on the Probability fetched from Medical Records
                p_val_percent = row['Probability']

                if row['Last Visit'] == "No history":
                    status_text = "⚪ No Data"
                elif p_val_percent < 30:
                    status_text = "🟢 Low Risk"
                elif p_val_percent < 50:
                    status_text = "🟡 Moderate"
                elif p_val_percent < 75:
                    status_text = "🟠 High Risk"
                else:
                    status_text = "🔴 Critical"

                # Fill the columns
                row_col_idx = 1
                for col_name in selected_cols:
                    if col_name == "Status":
                        row_cols[row_col_idx].write(status_text)
                    elif col_name == "Probability":
                        val = f"{p_val_percent:.1f}%" if row['Last Visit'] != "No history" else "N/A"
                        row_cols[row_col_idx].write(val)
                    elif col_name == "Actions":
                        action_col_edit, action_col_delete = row_cols[row_col_idx].columns(2)
                        # Edit Button
                        if action_col_edit.button("Edit", key=f"edit_patient_{row['ID']}", use_container_width=True):
                            st.session_state.editing_patient_id = row['ID']
                            st.rerun()
                        # Delete Button
                        if action_col_delete.button("Delete", key=f"delete_patient_{row['ID']}", use_container_width=True):
                            db.delete_patient(row['ID'])
                            st.success(f"Patient {row['Name']} and all their records deleted.")
                            st.session_state.editing_patient_id = None # Clear any active edit form
                            st.rerun()
                    else:
                        row_cols[row_col_idx].write(row[col_name])
                    row_col_idx += 1

            # --- Edit Patient Form (Modal/Expander) ---
            if st.session_state.editing_patient_id is not None:
                patient_to_edit_df = db.get_patients(st.session_state.user_id, st.session_state.editing_patient_id)
                if not patient_to_edit_df.empty:
                    patient_to_edit = patient_to_edit_df.iloc[0]

                    with st.expander(f"Edit Patient: {patient_to_edit['name']}", expanded=True):
                        with st.form("edit_patient_form", clear_on_submit=False):
                            edit_name = st.text_input("Name", value=patient_to_edit['name'])
                            edit_contact = st.text_input("Contact No", value=patient_to_edit['contact_no'])
                            edit_age = st.number_input("Age", value=patient_to_edit['age'], min_value=1, max_value=120)

                            col_edit_submit, col_edit_cancel = st.columns(2)
                            with col_edit_submit:
                                if st.form_submit_button("Update Patient"):
                                    db.update_patient(st.session_state.editing_patient_id, edit_name, edit_contact, edit_age)
                                    st.success("Patient updated successfully!")
                                    st.session_state.editing_patient_id = None # Clear editing state
                                    st.rerun()
                            with col_edit_cancel:
                                if st.form_submit_button("Cancel"):
                                    st.session_state.editing_patient_id = None # Clear editing state
                                    st.rerun()
                else:
                    st.session_state.editing_patient_id = None # Patient not found, clear state

            # --- Bulk Actions ---
            st.write("---")
            if selected_patient_ids:
                if st.button(f"Delete {len(selected_patient_ids)} Selected Patients", key="bulk_delete_patients"):
                    for p_id in selected_patient_ids:
                        db.delete_patient(p_id)
                    st.success(f"Deleted {len(selected_patient_ids)} patients.")
                    st.rerun()

    elif menu == "Add New Patient":
        st.title("🩺 Cardiac Analysis")

        # 1. FETCH EXISTING PATIENTS
        existing_patients = db.get_patients(st.session_state.user_id)

        # Create search labels like "John Smith | 0300-1234567"
        patient_options = ["-- Register New Patient --"]
        if not existing_patients.empty:
            patient_options += (existing_patients['name'] + " | " + existing_patients['contact_no']).tolist()

        search_selection = st.selectbox("Search Existing Patient or Select 'New'", patient_options)

        with st.form("medical_form"):
            st.subheader("Patient Identity")

            if search_selection == "-- Register New Patient --":
                col1, col2, col3 = st.columns(3)
                p_name = col1.text_input("Full Name")
                p_age = col2.number_input("Age", min_value=1, max_value=120, value=30)
                p_contact = col3.text_input("Contact No (Unique ID)")
                is_new_patient = True
                # Pre-fill patient_id if it's a new patient (it will be created)
                p_id = None
            else:
                # Extract contact from the selection string "Name | Contact"
                selected_contact = search_selection.split(" | ")[-1]
                p_info = existing_patients[existing_patients['contact_no'] == selected_contact].iloc[0]

                # Display info as read-only for confirmation
                st.info(f"**Selected:** {p_info['name']} | **Age:** {p_info['age']} | **ID:** {p_info['id']}")
                p_name, p_age, p_contact = p_info['name'], p_info['age'], p_info['contact_no']
                p_id = p_info['id'] # Set p_id for existing patient
                is_new_patient = False

            st.subheader("Clinical Metrics")
            col_a, col_b = st.columns(2)
            with col_a:
                p_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                cp = st.selectbox("Chest Pain Type", ["Typical Angina", "Atypical Angina", "Non-Anginal Pain", "Asymptomatic"])
                rbp = st.number_input("Resting Blood Pressure", value=120)
                chol = st.number_input("Cholesterol", value=200)
                fbs = st.selectbox("Fasting Blood Sugar > 120 mg/dl", [0, 1])
                restecg = st.selectbox("Resting ECG", ["Normal", "ST-T Wave Abnormality", "Left Ventricular Hypertrophy"])
            with col_b:
                mhr = st.number_input("Max Heart Rate", value=150)
                eia = st.selectbox("Exercise Induced Angina", [0, 1])
                st_depression = st.number_input("ST Depression", value=0.0)
                st_slope = st.selectbox("ST Slope", ["Up", "Flat", "Down"])
                major_vessels = st.number_input("Major Vessels (0-4)", min_value=0, max_value=4)
                thal = st.selectbox("Thalassemia", ["Normal", "Fixed Defect", "Reversible Defect"])

            if st.form_submit_button("Run Analysis & Save"):
                # --- MAPPING LOGIC ---
                gender_map = {"Male": 1, "Female": 0, "Other": 0}
                cp_map = {"Typical Angina": 0, "Atypical Angina": 1, "Non-Anginal Pain": 2, "Asymptomatic": 3}
                restecg_map = {"Normal": 0, "ST-T Wave Abnormality": 1, "Left Ventricular Hypertrophy": 2}
                slope_map = {"Up": 0, "Flat": 1, "Down": 2}
                thal_map = {"Normal": 1, "Fixed Defect": 2, "Reversible Defect": 3}

                input_data = {
                    "Age": p_age, "Gender": gender_map.get(p_gender),
                    "ChestPainType": cp_map.get(cp), "RestingBloodPressure": rbp,
                    "Cholesterol": chol, "FastingBloodSugar": fbs,
                    "RestECG": restecg_map.get(restecg), "MaxHeartRate": mhr,
                    "ExerciseInducedAngina": eia, "ST_Depression": st_depression,
                    "ST_Slope": slope_map.get(st_slope), "MajorVessels": major_vessels,
                    "Thalassemia": thal_map.get(thal, 0)
                }

                target, prob, cat, status = mh.predict_heart_risk(input_data)

                if status == "Success":
                    # --- SAVE LOGIC ---
                    if is_new_patient:
                        # 1. Check if contact exists to prevent error
                        check_exist = existing_patients[existing_patients['contact_no'] == p_contact]
                        if not check_exist.empty:
                            st.warning("A patient with this contact already exists. Updating record for that patient instead.")
                            p_id = check_exist.iloc[0]['id']
                        else:
                            p_id = db.create_patient(st.session_state.user_id, p_name, p_contact, p_age)

                    # 2. Save medical record to the correct p_id
                    db.create_medical_record(p_id, input_data, target, prob)
                    st.success(f"Analysis complete for {p_name}! Risk: {cat} ({prob:.1f}%)")
                else:
                    st.error(f"Error: {status}")

    elif menu == "Medical Records":
        st.title("📋 All Medical Records")

        all_records = []
        # Fetch all patients for the logged-in doctor
        patients_df = db.get_patients(st.session_state.user_id)

        if not patients_df.empty:
            for _, patient in patients_df.iterrows():
                patient_records_df = db.get_records(patient['id'])
                if not patient_records_df.empty:
                    # Merge patient info with medical records
                    merged_df = patient_records_df.assign(patient_name=patient['name'], patient_contact=patient['contact_no'])
                    all_records.append(merged_df)

        if all_records:
            full_medical_records_df = pd.concat(all_records, ignore_index=True)
            # Sort by visit_date newest first
            full_medical_records_df['visit_date'] = pd.to_datetime(full_medical_records_df['visit_date'])
            full_medical_records_df = full_medical_records_df.sort_values(by='visit_date', ascending=False).reset_index(drop=True)

            # --- DISPLAY LOGIC FOR MEDICAL RECORDS ---
            col_search_rec, col_config_rec, col_export_rec = st.columns([2, 1, 1])
            with col_search_rec:
                search_term_rec = st.text_input("🔍 Search Medical Records", placeholder="Filter by patient name or contact...")
                if search_term_rec:
                    full_medical_records_df = full_medical_records_df[
                        full_medical_records_df['patient_name'].str.contains(search_term_rec, case=False) |
                        full_medical_records_df['patient_contact'].str.contains(search_term_rec, case=False)
                    ]

            with col_config_rec:
                record_display_cols = ["patient_name", "patient_contact", "Age", "Gender", "ChestPainType",
                                       "RestingBloodPressure", "Cholesterol", "FastingBloodSugar", "RestECG",
                                       "MaxHeartRate", "ExerciseInducedAngina", "ST_Depression", "ST_Slope",
                                       "MajorVessels", "Thalassemia", "Probability", "Target", "visit_date", "Actions"]
                selected_rec_cols = st.multiselect("Record Columns", record_display_cols,
                                                   default=["patient_name", "visit_date", "Probability", "Target", "Actions"])

            with col_export_rec:
                csv_data_rec = full_medical_records_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Export Filtered Records to CSV",
                    data=csv_data_rec,
                    file_name="filtered_medical_records.csv",
                    mime="text/csv",
                    key="download_filtered_records",
                    use_container_width=True
                )

            # Pagination
            items_per_page_rec = 50
            total_pages_rec = math.ceil(len(full_medical_records_df) / items_per_page_rec) if len(full_medical_records_df) > 0 else 1
            page_rec = st.sidebar.number_input("Record Page", min_value=1, max_value=total_pages_rec, step=1)
            df_page_rec = full_medical_records_df.iloc[(page_rec - 1) * items_per_page_rec : page_rec * items_per_page_rec].copy()

            # Initialize session state for editing medical records
            if 'editing_record_id' not in st.session_state:
                st.session_state.editing_record_id = None

            st.write("---")
            # Adjust column width for actions if 'Actions' is selected
            rec_col_widths = [0.5] + [2 for _ in selected_rec_cols if _ != "Actions"]
            if "Actions" in selected_rec_cols:
                rec_col_widths.append(3) # Give more space for buttons
            header_rec_cols = st.columns(rec_col_widths)

            select_all_rec = header_rec_cols[0].checkbox("All Records", key="master_check_records")

            rec_col_idx = 1
            for col_name in selected_rec_cols:
                header_rec_cols[rec_col_idx].markdown(f"**{col_name}**")
                rec_col_idx += 1

            selected_record_ids = []

            # Reverse mappings for display in edit form
            disp_gender_map = {1: "Male", 0: "Female"}
            disp_cp_map = {0: "Typical Angina", 1: "Atypical Angina", 2: "Non-Anginal Pain", 3: "Asymptomatic"}
            disp_restecg_map = {0: "Normal", 1: "ST-T Wave Abnormality", 2: "Left Ventricular Hypertrophy"}
            disp_slope_map = {0: "Up", 1: "Flat", 2: "Down"}
            disp_thal_map = {1: "Normal", 2: "Fixed Defect", 3: "Reversible Defect"}

            for _, row_rec in df_page_rec.iterrows():
                row_rec_cols = st.columns(rec_col_widths)
                if row_rec_cols[0].checkbox("", value=select_all_rec, key=f"rec_select_{row_rec['id']}"):
                    selected_record_ids.append(row_rec['id'])

                rec_col_idx = 1
                for col_name in selected_rec_cols:
                    if col_name == "Actions":
                        action_rec_col_edit, action_rec_col_delete = row_rec_cols[rec_col_idx].columns(2)
                        if action_rec_col_edit.button("Edit", key=f"edit_record_{row_rec['id']}", use_container_width=True):
                            st.session_state.editing_record_id = row_rec['id']
                            st.rerun()
                        if action_rec_col_delete.button("Delete", key=f"delete_record_{row_rec['id']}", use_container_width=True):
                            db.delete_medical_record(row_rec['id'])
                            st.success(f"Medical record for {row_rec['patient_name']} on {row_rec['visit_date']} deleted.")
                            st.session_state.editing_record_id = None # Clear any active edit form
                            st.rerun()
                    elif col_name == "Probability":
                         row_rec_cols[rec_col_idx].write(f"{row_rec[col_name]:.1f}%")
                    elif col_name == "Gender":
                         row_rec_cols[rec_col_idx].write(disp_gender_map.get(row_rec[col_name], "N/A"))
                    elif col_name == "ChestPainType":
                         row_rec_cols[rec_col_idx].write(disp_cp_map.get(row_rec[col_name], "N/A"))
                    elif col_name == "RestECG":
                         row_rec_cols[rec_col_idx].write(disp_restecg_map.get(row_rec[col_name], "N/A"))
                    elif col_name == "ST_Slope":
                         row_rec_cols[rec_col_idx].write(disp_slope_map.get(row_rec[col_name], "N/A"))
                    elif col_name == "Thalassemia":
                         row_rec_cols[rec_col_idx].write(disp_thal_map.get(row_rec[col_name], "N/A"))
                    else:
                        row_rec_cols[rec_col_idx].write(row_rec[col_name])
                    rec_col_idx += 1

            # --- Edit Medical Record Form ---
            if st.session_state.editing_record_id is not None:
                record_to_edit_df = full_medical_records_df[full_medical_records_df['id'] == st.session_state.editing_record_id]
                if not record_to_edit_df.empty:
                    record_to_edit = record_to_edit_df.iloc[0]

                    with st.expander(f"Edit Record for {record_to_edit['patient_name']} ({record_to_edit['visit_date']})", expanded=True):
                        with st.form("edit_medical_record_form", clear_on_submit=False):
                            st.subheader("Clinical Metrics")
                            col_a_rec, col_b_rec = st.columns(2)
                            with col_a_rec:
                                edit_age = st.number_input("Age", value=record_to_edit['Age'], min_value=1, max_value=120, key="edit_rec_age")
                                edit_gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=list(disp_gender_map.values()).index(disp_gender_map.get(record_to_edit['Gender'], "Male")), key="edit_rec_gender")
                                edit_cp = st.selectbox("Chest Pain Type", ["Typical Angina", "Atypical Angina", "Non-Anginal Pain", "Asymptomatic"], index=list(disp_cp_map.values()).index(disp_cp_map.get(record_to_edit['ChestPainType'], "Typical Angina")), key="edit_rec_cp")
                                edit_rbp = st.number_input("Resting Blood Pressure", value=record_to_edit['RestingBloodPressure'], key="edit_rec_rbp")
                                edit_chol = st.number_input("Cholesterol", value=record_to_edit['Cholesterol'], key="edit_rec_chol")
                                edit_fbs = st.selectbox("Fasting Blood Sugar > 120 mg/dl", [0, 1], index=record_to_edit['FastingBloodSugar'], key="edit_rec_fbs")
                                edit_restecg = st.selectbox("Resting ECG", ["Normal", "ST-T Wave Abnormality", "Left Ventricular Hypertrophy"], index=list(disp_restecg_map.values()).index(disp_restecg_map.get(record_to_edit['RestECG'], "Normal")), key="edit_rec_restecg")
                            with col_b_rec:
                                edit_mhr = st.number_input("Max Heart Rate", value=record_to_edit['MaxHeartRate'], key="edit_rec_mhr")
                                edit_eia = st.selectbox("Exercise Induced Angina", [0, 1], index=record_to_edit['ExerciseInducedAngina'], key="edit_rec_eia")
                                edit_st_depression = st.number_input("ST Depression", value=record_to_edit['ST_Depression'], key="edit_rec_stdep")
                                edit_st_slope = st.selectbox("ST Slope", ["Up", "Flat", "Down"], index=list(disp_slope_map.values()).index(disp_slope_map.get(record_to_edit['ST_Slope'], "Up")), key="edit_rec_stslope")
                                edit_major_vessels = st.number_input("Major Vessels (0-4)", min_value=0, max_value=4, value=record_to_edit['MajorVessels'], key="edit_rec_majves")
                                edit_thal = st.selectbox("Thalassemia", ["Normal", "Fixed Defect", "Reversible Defect"], index=list(disp_thal_map.values()).index(disp_thal_map.get(record_to_edit['Thalassemia'], "Normal")), key="edit_rec_thal")

                            col_rec_submit, col_rec_cancel = st.columns(2)
                            with col_rec_submit:
                                if st.form_submit_button("Update Record"):
                                    gender_map = {"Male": 1, "Female": 0, "Other": 0}
                                    cp_map = {"Typical Angina": 0, "Atypical Angina": 1, "Non-Anginal Pain": 2, "Asymptomatic": 3}
                                    restecg_map = {"Normal": 0, "ST-T Wave Abnormality": 1, "Left Ventricular Hypertrophy": 2}
                                    slope_map = {"Up": 0, "Flat": 1, "Down": 2}
                                    thal_map = {"Normal": 1, "Fixed Defect": 2, "Reversible Defect": 3}

                                    updated_input_data = {
                                        "Age": edit_age, "Gender": gender_map.get(edit_gender),
                                        "ChestPainType": cp_map.get(edit_cp), "RestingBloodPressure": edit_rbp,
                                        "Cholesterol": edit_chol, "FastingBloodSugar": edit_fbs,
                                        "RestECG": restecg_map.get(edit_restecg), "MaxHeartRate": edit_mhr,
                                        "ExerciseInducedAngina": edit_eia, "ST_Depression": edit_st_depression,
                                        "ST_Slope": slope_map.get(edit_st_slope), "MajorVessels": edit_major_vessels,
                                        "Thalassemia": thal_map.get(edit_thal, 0)
                                    }
                                    # Re-run prediction with updated data to get new target/probability
                                    new_target, new_prob, new_cat, new_status = mh.predict_heart_risk(updated_input_data)

                                    if new_status == "Success":
                                        db.update_medical_record(st.session_state.editing_record_id, updated_input_data, new_target, new_prob)
                                        st.success("Medical record updated successfully!")
                                        st.session_state.editing_record_id = None
                                        st.rerun()
                                    else:
                                        st.error(f"Error re-analyzing record: {new_status}")

                            with col_rec_cancel:
                                if st.form_submit_button("Cancel Edit"):
                                    st.session_state.editing_record_id = None
                                    st.rerun()
                else:
                    st.session_state.editing_record_id = None # Record not found, clear state

            # --- Bulk Delete Records ---
            st.write("---")
            if selected_record_ids:
                if st.button(f"Delete {len(selected_record_ids)} Selected Records", key="bulk_delete_records"):
                    for rec_id in selected_record_ids:
                        db.delete_medical_record(rec_id)
                    st.success(f"Deleted {len(selected_record_ids)} medical records.")
                    st.rerun()

        else:
            st.info("No medical records found for your patients.")
