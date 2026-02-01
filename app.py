import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Investment Suite", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .audit-card { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; min-height: 300px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Strides ABA: Multi-Divisional Investment Model")

# --- PERSONNEL DATA ---
if 'manual_hires' not in st.session_state:
    st.session_state.manual_hires = pd.DataFrame([
        {"Month": 1, "Role": "Clinical Director (General)", "Salary": 140000, "Count": 1},
        {"Month": 1, "Role": "Intake Coordinator", "Salary": 25000, "Count": 1},
        {"Month": 1, "Role": "Recruiter", "Salary": 55000, "Count": 1},
        {"Month": 1, "Role": "Scheduler", "Salary": 55000, "Count": 1},
        {"Month": 1, "Role": "Director of HR/Payroll", "Salary": 85000, "Count": 1},
        {"Month": 1, "Role": "Compliance Officer", "Salary": 55000, "Count": 1},
        {"Month": 1, "Role": "Care Coordinator", "Salary": 55000, "Count": 1},
        {"Month": 13, "Role": "State Director", "Salary": 130000, "Count": 1},
        {"Month": 13, "Role": "Clinic Clinical Director", "Salary": 120000, "Count": 1},
        {"Month": 13, "Role": "Clinic Program Director", "Salary": 85000, "Count": 1},
    ])

# --- SIDEBAR: DRIVERS ---
with st.sidebar:
    st.header("🏠 In-Home Division")
    ih_start = st.number_input("Acquired Cases (M1)", value=40)
    ih_growth = st.slider("Monthly New Intake", 0, 10, 2)
    ih_h = st.slider("Home Avg Hours/Week", 5, 25, 14)

    st.header("🏢 Clinic Division")
    cl_h = st.slider("Clinic Avg Hours/Week", 15, 45, 30)
    cl_rent = st.number_input("Monthly Clinic Rent", value=8000)

    st.header("🛡️ Real-World Buffer")
    cancellation_rate = st.slider("Cancellation/No-Show %", 0, 30, 10) / 100
    buffer_mult = 1 - cancellation_rate

    st.header("💰 Global Economics")
    r_97153, r_97155, r_97151 = 17.0, 23.0, 29.0
    pay_rbt, pay_bcba = 25.0, 85.0
    fringe = (st.slider("Fringe Benefits %", 10, 35, 20) / 100) + 1
    
    view_type = st.radio("Display Granularity:", ["Yearly", "Quarterly", "Monthly"])

# --- CORE CALCULATOR ---
def run_model(hiring_data, ih_h_in, cl_h_in):
    months = 60
    data = []
