import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Divisional Pro-Forma", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Strides ABA: Multi-Divisional Financial Model")

# --- PERSISTENT PERSONNEL DATA ---
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
    ih_start = st.number_input("In-Home Starting Cases", value=40)
    ih_growth = st.slider("Monthly Home Growth", 0, 10, 2)
    ih_h = st.slider("Home Avg Hours/Week", 5, 25, 14)

    st.header("🏢 Clinic Division")
    st.info("Clinic launches M13. Ramps to 20 kids by M36.")
    cl_h = st.slider("Clinic Avg Hours/Week", 15, 45, 30)
    cl_rent = st.number_input("Monthly Clinic Rent", value=8000)

    st.header("💰 Global Economics")
    r_97153 = st.number_input("RBT Direct (97153) /unit", value=17.0)
    pay_rbt = st.number_input("RBT Hourly Pay", value=25.0)
    fringe = (st.slider("Fringe Benefits %", 10, 35, 20) / 100) + 1
    
    st.header("⚙️ View Settings")
    view_type = st.radio("Display Granularity:", ["Yearly", "Quarterly", "Monthly"])

# --- DIVISIONAL CALCULATOR ---
def run_model(hiring_data, ih_h_in, cl_h_in):
    months = 60
    data = []
    
    clean_hires = hiring_data.copy()
    for col in ['Count', 'Salary', 'Month']:
        clean_hires[col] = pd.to_numeric(clean_hires[col], errors='coerce').fillna(0)

    for m in range(1, months + 1):
        ih_cases = ih_start + (ih_growth * (m-1))
        cl_cases = 0
        if m >= 13:
            cl_ramp = min(m - 12, 24)
            cl_cases = (20 / 24) * cl_ramp

        active_staff = clean_hires[clean_hires['Month'] <= m]
        cc_required = max(1, int(np.ceil((ih_cases + cl_cases) / 50)))
        
        ih_fixed, cl_fixed = 0, 0
        for _, row in active_staff.iterrows():
            cnt = cc_required if "Care Coordinator" in row['Role'] else row['Count']
            cost = (row['Salary'] * cnt) / 12 * fringe
            if "Clinic" in row['Role']: cl_fixed += cost
            else: ih_fixed += cost
        
        # Revenue/COGS Math
        h_ih = ih_cases * ih_h_in * 4.33
        ih_rev = (h_ih * 4 * r_97153) + (ih_cases * 1100)
        ih_cogs = (h_ih * pay_rbt * fringe) + (ih_cases * 350 * fringe)
        ih_ebitda = ih_rev - ih_cogs - ih_fixed - (ih_rev * 0.05)
        
        cl_rev, cl_cogs, cl_ebitda = 0, 0, 0
        if m >= 13:
            h_cl = cl_cases * cl_h_in * 4.33
            cl_rev = (h_cl * 4 * r_97153) + (cl_cases * 1400)
            cl_cogs = (h_cl * pay_rbt * fringe) + (cl_cases
