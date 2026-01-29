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
    .audit-card { background-color: #f1f5f9; padding: 15px; border-radius: 8px; border-left: 5px solid #1e3a8a; margin-bottom: 10px; min-height: 120px; }
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

# --- SIDEBAR: ALL TOGGLES RESTORED ---
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
    pay_bcba_billable = st.number_input("BCBA Billable Hourly", value=85.0)
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
        # 1. CASE FLOW
        ih_cases = ih_start + (ih_growth * (m-1))
        cl_cases = 0
        if m >= 13:
            cl_ramp = min(m - 12, 24)
            cl_cases = (20 / 24) * cl_ramp

        # 2. PERSONNEL ALLOCATION
        active_staff = clean_hires[clean_hires['Month'] <= m]
        cc_required = max(1, int(np.ceil((ih_cases + cl_cases) / 50)))
        
        ih_fixed = 0
        cl_fixed = 0
        for _, row in active_staff.iterrows():
            cnt = cc_required if "Care Coordinator" in row['Role'] else row['Count']
            cost = (row['Salary'] * cnt) / 12 * fringe
            if "Clinic" in row['Role']: cl_fixed += cost
            else: ih_fixed += cost
        
        # 3. IN-HOME DIV MATH
        h_ih = ih_cases * ih_h_in * 4.33
        ih_rev = (h_ih * 4 * r_97153) + (ih_cases * 1100)
        ih_cogs = (h_ih * pay_rbt * fringe) + (ih_cases * 350 * fringe)
        ih_ebitda = ih_rev - ih_cogs - ih_fixed - (ih_rev * 0.05)
        
        # 4. CLINIC DIV MATH
        cl_rev, cl_cogs, cl_ebitda, h_cl = 0, 0, 0, 0
        if m >= 13:
            h_cl = cl_cases * cl_h_in * 4.33
            cl_rev = (h_cl * 4 * r_97153) + (cl_cases * 1400)
            cl_cogs = (h_cl * pay_rbt * fringe) + (cl_cases * 350 * fringe)
            cl_ebitda = cl_rev - cl_cogs - cl_fixed - cl_rent - (cl_rev * 0.05)

        # 5. PROFIT SHARE
        total_ebitda_pre = ih_ebitda + cl_ebitda
        p_share = (total_ebitda_pre * 0.05) if (m >= 13 and total_ebitda_pre > 0) else 0
        final_total_ebitda = total_ebitda_pre - p_share

        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "IH_Cases": ih_cases, "IH_Revenue": ih_rev, "IH_EBITDA": ih_ebitda, "IH_Hours": h_ih,
            "CL_Cases": cl_cases, "CL_Revenue": cl_rev, "CL_EBITDA": cl_ebitda, "CL_Hours": h_cl,
            "Total_Revenue": ih_rev + cl_rev, "Total_EBITDA": final_total_ebitda, "P_Share": p_share
        })
    return pd.DataFrame(data)

df = run_model(st.session_state.manual_hires, ih_h, cl_h)

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🌎 Consolidated", "🏠 In-Home Division", "🏢 Clinic Division", "📋 Personnel Roadmap"])

with tab4:
    st.subheader("Division-Specific Personnel Roadmap")
    with st.form("hiring_shield"):
        edited = st.data_editor(st.session_state.manual_hires, num_rows="dynamic", use_container_width=True)
        if st.form_submit_button("🚀 Sync Roadmap to All Divisions"):
            st.session_state.manual_hires = edited
            st.rerun()

def get_board_view(df, prefix, is_total=False):
    group_cols = ["Year"]
    if view_type == "Quarterly": group_cols.append("Quarter")
    
    if is_total:
        board = df.groupby(group_cols).agg({'Total_Revenue':'sum','Total_EBITDA':'sum','IH_Cases':'max','CL_Cases':'max'}).reset_index()
        board['Revenue'] = board['Total_Revenue']
        board['EBITDA'] = board['Total_EBITDA']
        board['Cases'] = board['IH_Cases'] + board['CL_Cases']
    else:
        board = df.groupby(group_cols).agg({f'{prefix}_Cases':'max', f'{prefix}_Revenue':'sum', f'{prefix}_EBITDA':'sum'}).reset_index()
        board['Revenue'] = board[f'{prefix}_Revenue']
        board['EBITDA'] = board[f'{prefix}_EBITDA']
        board['Cases'] = board[f'{prefix}_Cases']
    
    if view_type == "Yearly": board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])}", axis=1)
    else: board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    
    board['Margin %'] = (board['EBITDA'] / board['Revenue'] * 100).fillna(0)
    return board[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T

with tab1:
    st.markdown("<div class='division-header'><h3>Total Enterprise Summary</h3></div>", unsafe_allow_html=True)
    st.dataframe(get_board_view(df, "", is_total=True).style.format(precision=0, thousands=","), use_container_width=True)

with tab2:
    st.markdown("<div class='division-header'><h3>In-Home Division Only</h3></div>", unsafe_allow_html=True)
    st.dataframe(get_board_view(df, "IH").style.format(precision=0, thousands=","), use_container_width=True)

with tab3:
    st.markdown("<div class='division-header'><h3>Clinic Division Only</h3></div>", unsafe_allow_html=True)
    st.dataframe(get_board_view(df, "CL").style.format(precision=0, thousands=","), use_container_width=True)
