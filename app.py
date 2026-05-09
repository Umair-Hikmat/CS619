%%writefile app.py
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
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Patients List", "Add New Patient", "Logout"])

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
            medical_history = db.get_records(p['id'])

            # Default values if no medical record exists yet
            prob_val = 0.0 # Will store 0-100 percentage
            target_val = "N/A"
            visit_val = "No history"

            if not medical_history.empty:
                # Assuming the first row [0] is the most recent record
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
                "Probability": prob_val, # This is 0-100 already
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
                all_display_cols = ["Name", "Age", "Contact", "Probability", "Target", "Last Visit", "Status"]
                selected_cols = st.multiselect("Columns", all_display_cols,
                                               default=["Name", "Status", "Probability", "Last Visit"])

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
            header_cols = st.columns([0.5] + [2 for _ in selected_cols])
            select_all = header_cols[0].checkbox("All", key="master_check")

            for i, col_name in enumerate(selected_cols):
                header_cols[i+1].markdown(f"**{col_name}**")

            for _, row in df_page.iterrows():
                r_cols = st.columns([0.5] + [2 for _ in selected_cols])
                r_cols[0].checkbox("", value=select_all, key=f"p_{row['ID']}")

                # Determine Status text based on the Probability fetched from Medical Records
                # row['Probability'] is already 0-100 percentage from summary_list
                p_val_percent = row['Probability'] # Corrected: Removed '* 100'

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
                for i, col_name in enumerate(selected_cols):
                    if col_name == "Status":
                        r_cols[i+1].write(status_text)
                    elif col_name == "Probability":
                        val = f"{p_val_percent:.1f}%" if row['Last Visit'] != "No history" else "N/A"
                        r_cols[i+1].write(val)
                    else:
                        r_cols[i+1].write(row[col_name])

    # ... rest of the code ...
