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
# Initialize session state for editing medical record
if 'editing_record_id' not in st.session_state:
    st.session_state.editing_record_id = None

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
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Patients List", "Add New Patient", "Medical Records", "Logout"])

    if menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.auth_mode = "login"
        st.rerun()

    elif menu == "Dashboard":
        st.title("📈 Clinical Insights")

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

        patients_df = db.get_patients(st.session_state.user_id)
        summary_list = []

        # Define consistent thresholds for display to match model_handler.py
        low_risk_threshold = 0.30
        moderate_risk_threshold = 0.45 # This matches the model's default clinical threshold for "Borderline / Moderate Risk"
        high_risk_threshold = 0.75

        for _, p in patients_df.iterrows():
            medical_history = db.get_records(p['id'])

            prob_val = 0.0 # Will store 0-100 percentage
            target_val = "N/A"
            visit_val = "No history"
            status_text = "⚪ No Data"

            if not medical_history.empty:
                latest_rec = medical_history.iloc[0]
                prob_val = latest_rec.get('Probability', 0.0)
                target_val = latest_rec.get('Target', "N/A")
                visit_val = latest_rec.get('visit_date', "No history")

                if prob_val < low_risk_threshold:
                    status_text = "🟢 Low Risk"
                elif prob_val < moderate_risk_threshold:
                    category = "Borderline / Moderate Risk"
                    status_text = "🟡 Borderline / Moderate Risk"
                elif prob_val < high_risk_threshold:
                    status_text = "🟠 High Risk"
                else:
                    status_text = "🔴 Critical Risk"

            summary_list.append({
                "ID": p['id'],
                "Name": p['name'],
                "Age": p['age'],
                "Contact": p['contact_no'],
                "Probability": f"{prob_val:.1f}%" if visit_val != "No history" else "N/A",
                "Target": target_val,
                "Last Visit": visit_val,
                "Status": status_text
            })

        df = pd.DataFrame(summary_list)

        if df.empty:
            st.info("No patients found in your records.")
        else:
            col_search, col_export = st.columns([3, 1])
            with col_search:
                search_term = st.text_input("🔍 Search Patients", placeholder="Filter by name or contact...", key="patient_search")
                if search_term:
                    df = df[df['Name'].str.contains(search_term, case=False) | df['Contact'].str.contains(search_term, case=False)]

            with col_export:
                if not df.empty:
                    patient_ids_to_export = df['ID'].tolist()
                    all_medical_records_list = []

                    for pid in patient_ids_to_export:
                        patient_records = db.get_records(pid)
                        if not patient_records.empty:
                            all_medical_records_list.append(patient_records)

                    if all_medical_records_list:
                        full_records_df = pd.concat(all_medical_records_list, ignore_index=True)

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

                        if 'Probability' in full_records_df.columns:
                            full_records_df['Probability'] = full_records_df['Probability'].round(2).astype(str) + '%'

                        csv_data = full_records_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Export All Records (Filtered Patients) to CSV",
                            data=csv_data,
                            file_name="all_patient_medical_records.csv",
                            mime="text/csv",
                            key="download_all_records",
                            width='full'
                        )
                    else:
                        st.info("No records to export for the filtered patients.")
                else:
                    st.info("No patients found to export records for.")

            st.write("---")

            # Display DataFrame with selection capabilities
            edited_df = st.dataframe(
                df,
                column_order=["Name", "Status", "Probability", "Last Visit", "Age", "Contact", "ID", "Target"],
                column_config={
                    "ID": st.column_config.Column(disabled=True),
                    "Target": st.column_config.Column(disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                on_select="rerun", # Rerun on selection change to update buttons
                selection_mode="multi-row"
            )

            selected_rows = edited_df.selection.rows
            selected_patient_ids = df.loc[selected_rows, 'ID'].tolist()

            # --- Action Buttons for Selected Patients ---
            st.write("---")
            if selected_patient_ids:
                col_edit_selected, col_delete_selected, col_bulk_edit_placeholder = st.columns(3)

                if len(selected_patient_ids) == 1:
                    patient_id_to_edit = selected_patient_ids[0]
                    if col_edit_selected.button(f"Edit Patient {df[df['ID'] == patient_id_to_edit]['Name'].iloc[0]}", key="edit_single_patient_btn", width='full'):
                        st.session_state.editing_patient_id = patient_id_to_edit
                        st.rerun()
                    if col_delete_selected.button(f"Delete Patient {df[df['ID'] == patient_id_to_edit]['Name'].iloc[0]}", key="delete_single_patient_btn", width='full'):
                        db.delete_patient(patient_id_to_edit)
                        st.success(f"Patient {df[df['ID'] == patient_id_to_edit]['Name'].iloc[0]} and all their records deleted.")
                        st.rerun()
                elif len(selected_patient_ids) > 1:
                    if col_delete_selected.button(f"Delete {len(selected_patient_ids)} Selected Patients", key="bulk_delete_patients_btn", width='full'):
                        for p_id in selected_patient_ids:
                            db.delete_patient(p_id)
                        st.success(f"Deleted {len(selected_patient_ids)} patients.")
                        st.rerun()
                    # Placeholder for bulk edit
                    if col_bulk_edit_placeholder.button(f"Bulk Update {len(selected_patient_ids)} Patients", key="bulk_edit_patients_placeholder_btn", width='full'):
                        st.info("Bulk edit functionality will be added here. Please specify which fields you'd like to bulk update!")

            # --- Edit Patient Form (Expander) ---
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
                                if st.form_submit_button("Update Patient", width='full'):
                                    db.update_patient(st.session_state.editing_patient_id, edit_name, edit_contact, edit_age)
                                    st.success("Patient updated successfully!")
                                    st.session_state.editing_patient_id = None
                                    st.rerun()
                            with col_edit_cancel:
                                if st.form_submit_button("Cancel", width='full'):
                                    st.session_state.editing_patient_id = None
                                    st.rerun()
                else:
                    st.session_state.editing_patient_id = None

    elif menu == "Add New Patient":
        st.title("🩺 Cardiac Analysis")

        existing_patients = db.get_patients(st.session_state.user_id)

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
                p_id = None
            else:
                selected_contact = search_selection.split(" | ")[-1]
                p_info = existing_patients[existing_patients['contact_no'] == selected_contact].iloc[0]

                st.info(f"**Selected:** {p_info['name']} | **Age:** {p_info['age']} | **ID:** {p_info['id']}")
                p_name, p_age, p_contact = p_info['name'], p_info['age'], p_info['contact_no']
                p_id = p_info['id']
                is_new_patient = False

            st.subheader("Clinical Metrics")
            col_a, col_b = st.columns(2)
            with col_a:
                p_gender = st.selectbox("Gender", ["Male", "Female"])
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

            if st.form_submit_button("Run Analysis & Save", width='full'):
                gender_map = {"Male": 1, "Female": 0}
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
                    if is_new_patient:
                        check_exist = existing_patients[existing_patients['contact_no'] == p_contact]
                        if not check_exist.empty:
                            st.warning("A patient with this contact already exists. Updating record for that patient instead.")
                            p_id = check_exist.iloc[0]['id']
                        else:
                            p_id = db.create_patient(st.session_state.user_id, p_name, p_contact, p_age)

                    db.create_medical_record(p_id, input_data, target, prob)
                    st.success(f"Analysis complete for {p_name}! Risk: {cat} ({prob:.1f}%)")
                else:
                    st.error(f"Error: {status}")

    elif menu == "Medical Records":
        st.title("📋 All Medical Records")

        all_records = []
        patients_df = db.get_patients(st.session_state.user_id)

        disp_gender_map = {1: "Male", 0: "Female"}
        disp_cp_map = {0: "Typical Angina", 1: "Atypical Angina", 2: "Non-Anginal Pain", 3: "Asymptomatic"}
        disp_restecg_map = {0: "Normal", 1: "ST-T Wave Abnormality", 2: "Left Ventricular Hypertrophy"}
        disp_slope_map = {0: "Up", 1: "Flat", 2: "Down"}
        disp_thal_map = {1: "Normal", 2: "Fixed Defect", 3: "Reversible Defect"}

        if not patients_df.empty:
            for _, patient in patients_df.iterrows():
                patient_records_df = db.get_records(patient['id'])
                if not patient_records_df.empty:
                    merged_df = patient_records_df.assign(patient_name=patient['name'], patient_contact=patient['contact_no'])
                    all_records.append(merged_df)

        if all_records:
            full_medical_records_df = pd.concat(all_records, ignore_index=True)
            full_medical_records_df['visit_date'] = pd.to_datetime(full_medical_records_df['visit_date'])
            full_medical_records_df = full_medical_records_df.sort_values(by='visit_date', ascending=False).reset_index(drop=True)

            # Apply reverse mappings for display
            full_medical_records_df['Gender_Display'] = full_medical_records_df['Gender'].map(disp_gender_map).fillna(full_medical_records_df['Gender'])
            full_medical_records_df['ChestPainType_Display'] = full_medical_records_df['ChestPainType'].map(disp_cp_map).fillna(full_medical_records_df['ChestPainType'])
            full_medical_records_df['RestECG_Display'] = full_medical_records_df['RestECG'].map(disp_restecg_map).fillna(full_medical_records_df['RestECG'])
            full_medical_records_df['ST_Slope_Display'] = full_medical_records_df['ST_Slope'].map(disp_slope_map).fillna(full_medical_records_df['ST_Slope'])
            full_medical_records_df['Thalassemia_Display'] = full_medical_records_df['Thalassemia'].map(disp_thal_map).fillna(full_medical_records_df['Thalassemia'])
            full_medical_records_df['Probability_Display'] = full_medical_records_df['Probability'].apply(lambda x: f"{x:.1f}%")


            col_search_rec, col_export_rec = st.columns([3, 1])
            with col_search_rec:
                search_term_rec = st.text_input("🔍 Search Medical Records", placeholder="Filter by patient name or contact...", key="record_search")
                if search_term_rec:
                    full_medical_records_df = full_medical_records_df[
                        full_medical_records_df['patient_name'].str.contains(search_term_rec, case=False) |
                        full_medical_records_df['patient_contact'].str.contains(search_term_rec, case=False)
                    ]

            with col_export_rec:
                csv_data_rec = full_medical_records_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Export Filtered Records to CSV",
                    data=csv_data_rec,
                    file_name="filtered_medical_records.csv",
                    mime="text/csv",
                    key="download_filtered_records",
                    width='full'
                )

            st.write("---")

            # Display DataFrame with selection capabilities
            edited_records_df = st.dataframe(
                full_medical_records_df,
                column_order=["patient_name", "patient_contact", "visit_date", "Probability_Display", "Target",
                              "Age", "Gender_Display", "ChestPainType_Display", "RestingBloodPressure",
                              "Cholesterol", "FastingBloodSugar", "RestECG_Display", "MaxHeartRate",
                              "ExerciseInducedAngina", "ST_Depression", "ST_Slope_Display", "MajorVessels",
                              "Thalassemia_Display", "id", "patient_id"],
                column_config={
                    "id": st.column_config.Column("Record ID", disabled=True),
                    "patient_id": st.column_config.Column(disabled=True),
                    "Gender": st.column_config.Column(disabled=True, width="hidden"), # Hide original numeric gender
                    "ChestPainType": st.column_config.Column(disabled=True, width="hidden"),
                    "RestECG": st.column_config.Column(disabled=True, width="hidden"),
                    "ST_Slope": st.column_config.Column(disabled=True, width="hidden"),
                    "Thalassemia": st.column_config.Column(disabled=True, width="hidden"),
                    "Probability": st.column_config.Column(disabled=True, width="hidden"), # Hide original numeric probability
                    "Gender_Display": st.column_config.Column("Gender"),
                    "ChestPainType_Display": st.column_config.Column("Chest Pain Type"),
                    "RestECG_Display": st.column_config.Column("Rest ECG"),
                    "ST_Slope_Display": st.column_config.Column("ST Slope"),
                    "Thalassemia_Display": st.column_config.Column("Thalassemia"),
                    "Probability_Display": st.column_config.Column("Probability"),
                    "Target": st.column_config.Column(disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                on_select="rerun",
                selection_mode="multi-row"
            )

            selected_record_indices = edited_records_df.selection.rows
            selected_record_ids = full_medical_records_df.loc[selected_record_indices, 'id'].tolist()

            # --- Action Buttons for Selected Records ---
            st.write("---")
            if selected_record_ids:
                col_edit_rec_selected, col_delete_rec_selected, col_bulk_edit_rec_placeholder = st.columns(3)

                if len(selected_record_ids) == 1:
                    record_id_to_edit = selected_record_ids[0]
                    rec_name = full_medical_records_df[full_medical_records_df['id'] == record_id_to_edit]['patient_name'].iloc[0]
                    rec_date = full_medical_records_df[full_medical_records_df['id'] == record_id_to_edit]['visit_date'].iloc[0].strftime("%Y-%m-%d")
                    if col_edit_rec_selected.button(f"Edit Record for {rec_name} ({rec_date})", key="edit_single_record_btn", width='full'):
                        st.session_state.editing_record_id = record_id_to_edit
                        st.rerun()
                    if col_delete_rec_selected.button(f"Delete Record for {rec_name} ({rec_date})", key="delete_single_record_btn", width='full'):
                        db.delete_medical_record(record_id_to_edit)
                        st.success(f"Medical record for {rec_name} on {rec_date} deleted.")
                        st.rerun()
                elif len(selected_record_ids) > 1:
                    if col_delete_rec_selected.button(f"Delete {len(selected_record_ids)} Selected Records", key="bulk_delete_records_btn", width='full'):
                        for rec_id in selected_record_ids:
                            db.delete_medical_record(rec_id)
                        st.success(f"Deleted {len(selected_record_ids)} medical records.")
                        st.rerun()
                    # Placeholder for bulk edit
                    if col_bulk_edit_rec_placeholder.button(f"Bulk Update {len(selected_record_ids)} Records", key="bulk_edit_records_placeholder_btn", width='full'):
                        st.info("Bulk edit functionality for medical records will be added here. Please specify which fields you'd like to bulk update!")


            # --- Edit Medical Record Form (Expander) ---
            if st.session_state.editing_record_id is not None:
                record_to_edit_df = full_medical_records_df[full_medical_records_df['id'] == st.session_state.editing_record_id]
                if not record_to_edit_df.empty:
                    record_to_edit = record_to_edit_df.iloc[0]

                    with st.expander(f"Edit Record for {record_to_edit['patient_name']} ({record_to_edit['visit_date'].strftime('%Y-%m-%d')})", expanded=True):
                        with st.form("edit_medical_record_form", clear_on_submit=False):
                            st.subheader("Clinical Metrics")
                            col_a_rec, col_b_rec = st.columns(2)
                            with col_a_rec:
                                edit_age = st.number_input("Age", value=int(record_to_edit['Age']), min_value=1, max_value=120, key="edit_rec_age")

                                current_gender_value = record_to_edit['Gender']
                                current_gender_str = disp_gender_map.get(current_gender_value)
                                gender_options = ["Male", "Female"]
                                initial_gender_index = gender_options.index(current_gender_str) if current_gender_str in gender_options else 0
                                edit_gender = st.selectbox("Gender", gender_options, index=initial_gender_index, key="edit_rec_gender")

                                current_cp_value = record_to_edit['ChestPainType']
                                current_cp_str = disp_cp_map.get(current_cp_value)
                                cp_options = ["Typical Angina", "Atypical Angina", "Non-Anginal Pain", "Asymptomatic"]
                                initial_cp_index = cp_options.index(current_cp_str) if current_cp_str in cp_options else 0
                                edit_cp = st.selectbox("Chest Pain Type", cp_options, index=initial_cp_index, key="edit_rec_cp")

                                edit_rbp = st.number_input("Resting Blood Pressure", value=int(record_to_edit['RestingBloodPressure']), key="edit_rec_rbp")
                                edit_chol = st.number_input("Cholesterol", value=int(record_to_edit['Cholesterol']), key="edit_rec_chol")

                                edit_fbs_value = record_to_edit['FastingBloodSugar']
                                initial_fbs_index = int(edit_fbs_value) if pd.notna(edit_fbs_value) else 0
                                edit_fbs = st.selectbox("Fasting Blood Sugar > 120 mg/dl", [0, 1], index=initial_fbs_index, key="edit_rec_fbs")

                                current_restecg_value = record_to_edit['RestECG']
                                current_restecg_str = disp_restecg_map.get(current_restecg_value)
                                restecg_options = ["Normal", "ST-T Wave Abnormality", "Left Ventricular Hypertrophy"]
                                initial_restecg_index = restecg_options.index(current_restecg_str) if current_restecg_str in restecg_options else 0
                                edit_restecg = st.selectbox("Resting ECG", restecg_options, index=initial_restecg_index, key="edit_rec_restecg")
                            with col_b_rec:
                                edit_mhr = st.number_input("Max Heart Rate", value=int(record_to_edit['MaxHeartRate']), key="edit_rec_mhr")
                                edit_eia = st.selectbox("Exercise Induced Angina", [0, 1], index=int(record_to_edit['ExerciseInducedAngina']), key="edit_rec_eia")
                                edit_st_depression = st.number_input("ST Depression", value=float(record_to_edit['ST_Depression']), key="edit_rec_stdep")

                                current_st_slope_value = record_to_edit['ST_Slope']
                                current_st_slope_str = disp_slope_map.get(current_st_slope_value)
                                slope_options = ["Up", "Flat", "Down"]
                                initial_slope_index = slope_options.index(current_st_slope_str) if current_st_slope_str in slope_options else 0
                                edit_st_slope = st.selectbox("ST Slope", slope_options, index=initial_slope_index, key="edit_rec_stslope")

                                edit_major_vessels = st.number_input("Major Vessels (0-4)", min_value=0, max_value=4, value=int(record_to_edit['MajorVessels']), key="edit_rec_majves")

                                current_thal_value = record_to_edit['Thalassemia']
                                current_thal_str = disp_thal_map.get(current_thal_value)
                                thal_options = ["Normal", "Fixed Defect", "Reversible Defect"]
                                initial_thal_index = thal_options.index(current_thal_str) if current_thal_str in thal_options else 0
                                edit_thal = st.selectbox("Thalassemia", thal_options, index=initial_thal_index, key="edit_rec_thal")

                            col_rec_submit, col_rec_cancel = st.columns(2)

                            # Place submit buttons directly within the form context
                            with col_rec_submit:
                                if st.form_submit_button("Update Record", width='full'):
                                    gender_map = {"Male": 1, "Female": 0}
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
                                    new_target, new_prob, new_cat, new_status = mh.predict_heart_risk(updated_input_data)

                                    if new_status == "Success":
                                        db.update_medical_record(st.session_state.editing_record_id, updated_input_data, new_target, new_prob)
                                        st.success("Medical record updated successfully!")
                                        st.session_state.editing_record_id = None
                                        st.rerun()
                                    else:
                                        st.error(f"Error re-analyzing record: {new_status}")

                            with col_rec_cancel:
                                # A regular button is used for cancel, it does not need to be a form_submit_button
                                if st.button("Cancel Edit", key="cancel_edit_rec_button", width='full'):
                                    st.session_state.editing_record_id = None
                                    st.rerun()
                else:
                    st.session_state.editing_record_id = None

        else:
            st.info("No medical records found for your patients.")
