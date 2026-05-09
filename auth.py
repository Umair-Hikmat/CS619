import streamlit as st
import database_helper as db

def login_page():
    st.markdown("<h1 style='text-align: center;'>🏥 Deep Heart Pro</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Doctor Login Portal</h3>", unsafe_allow_html=True)

    # Using a container to center the login form slightly
    with st.container():
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login", use_container_width=True):
                user = db.verify_login(email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = f"{user[1]} {user[2]}"
                    st.success(f"Welcome Dr. {user[1]}")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

        with col2:
            if st.button("Sign Up", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()

        st.write("---")
        if st.button("Forgot Password?", use_container_width=True):
            st.session_state.auth_mode = "forgot"
            st.rerun()

def signup_page():
    st.subheader("👨‍⚕️ Create Doctor Account")
    with st.form("signup_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            f_name = st.text_input("First Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
        with col_b:
            l_name = st.text_input("Last Name")
            contact = st.text_input("Contact No")
            qual = st.text_input("Qualification (MBBS/MD)")

        dob = st.date_input("Date of Birth")

        submit = st.form_submit_button("Complete Registration")
        if submit:
            if email and password and f_name:
                success = db.create_doctor(f_name, l_name, email, contact, password, qual, str(dob))
                if success:
                    st.success("Account created! Please log in.")
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error("Email already registered.")
            else:
                st.warning("Please fill in all required fields.")

    if st.button("← Back to Login"):
        st.session_state.auth_mode = "login"
        st.rerun()

def forgot_password_page():
    st.subheader("🔑 Reset Password")
    st.info("Enter your registered email to reset your credentials.")
    email = st.text_input("Registered Email")
    if st.button("Send Reset Instructions"):
        st.success(f"If {email} is in our database, instructions have been sent.")

    if st.button("← Back to Login"):
        st.session_state.auth_mode = "login"
        st.rerun()
