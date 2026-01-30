import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Comprehensive Budget Model", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .audit-card { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Strides ABA: Full-Budget Investment Model")

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
    st.info("Clinic launches M13. Ramps to 20 kids by M36.")
    cl_h = st.slider("Clinic Avg Hours/Week", 15, 45, 30)
    cl_rent = st.number_input("Monthly Clinic Rent", value=8000)

    st.header("🛡️ Real-World Buffer")
    cancellation_rate = st.slider("Cancellation/No-Show %", 0, 30, 10) / 100
    buffer_mult = 1 - cancellation_rate

    st.header("💰 Global Economics")
    r_97153 = st.number_input("97153 (Direct) /unit", value=17.0)
    r_97155 = st.number_input("97155 (Super) /unit", value=23.0)
    r_97151 = st.number_input("97151 (Assess) /unit", value=29.0)
    pay_rbt = st.number_input("RBT Hourly Pay", value=25.0)
    pay_bcba = st.number_input("BCBA Billable Hourly", value=85.0)
    fringe = (st.slider("Fringe Benefits %", 10, 35, 20) / 100) + 1
    
    view_type = st.radio("Display Granularity:", ["Yearly", "Quarterly", "Monthly"])

# --- CORE CALCULATOR ---
def run_model(hiring_data, ih_h_in, cl_h_in):
    months = 60
    data = []
    cum_ebitda = 0
    clean_hires = hiring_data.copy()
    for col in ['Count', 'Salary', 'Month']:
        clean_hires[col] = pd.to_numeric(clean_hires[col], errors='coerce').fillna(0)

    for m in range(1, months + 1):
        # 1. VOLUME
        ih_cases = ih_start + (ih_growth * (m-1))
        cl_cases = 0 if m < 13 else (20 / 24) * min(m - 12, 24)
        total_cases = ih_cases + cl_cases

        # 2. PERSONNEL & HEADCOUNT TRACKING
        active_staff = clean_hires[clean_hires['Month'] <= m]
        cc_req = max(1, int(np.ceil(total_cases / 50)))
        
        ih_fixed, cl_fixed, ih_staff_list, cl_staff_list = 0, 0, [], []
        fixed_headcount = 0
        new_back_office_hires = 0
        
        for _, row in active_staff.iterrows():
            cnt = cc_req if "Care Coordinator" in row['Role'] else row['Count']
            cost = (row['Salary'] * cnt) / 12 * fringe
            fixed_headcount += cnt
            if row['Month'] == m: new_back_office_hires += cnt
            
            if "Clinic" in row['Role']: 
                cl_fixed += cost
                cl_staff_list.append({"Role": row['Role'], "Cost": cost})
            else: 
                ih_fixed += cost
                ih_staff_list.append({"Role": row['Role'], "Cost": cost})

        # 3. REVENUE MATH
        h_ih53 = (ih_cases * ih_h_in * 4.33) * buffer_mult
        h_ih55 = (ih_cases * 2 * 4.33) * buffer_mult
        h_ih51 = (((ih_growth if m > 1 else 0) + (ih_cases/6)) * 8)
        r_ih = (h_ih53 * 4 * r_97153) + (h_ih55 * 4 * r_97155) + (h_ih51 * 4 * r_97151)
        
        h_cl53, h_cl55, h_cl51, r_cl = 0, 0, 0, 0
        if m >= 13:
            h_cl53 = (cl_cases * cl_h_in * 4.33) * buffer_mult
            h_cl55 = (cl_cases * 2 * 4.33) * buffer_mult
            h_cl51 = (((20/24) + (cl_cases/6)) * 8)
            r_cl = (h_cl53 * 4 * r_97153) + (h_cl55 * 4 * r_97155) + (h_cl51 * 4 * r_97151)
        
        total_rev = r_ih + r_cl
        
        # 4. VARIABLE HEADCOUNT FOR EMR/IT
        # Estimating RBT/BCBA count based on 25 billable hours/week
        direct_labor_headcount = ((h_ih53 + h_cl53 + h_ih55 + h_cl55) / (25 * 4.33))
        total_headcount = fixed_headcount + direct_labor_headcount
        
        # 5. GRANULAR OPEX BUDGET
        mktg = 10000
        emr_it = (total_headcount * 90) + (total_headcount * 100) # $90 EMR + $100 IT/Email Avg
        ai_notes = np.ceil(total_cases / 30) * 1800
        legal = 10000 / 12
        billing = total_rev * 0.05
        leadtrap = 800
        ats = 400 # Avg ATS (Apploi)
        indeed = 5000
        hardware = new_back_office_hires * 1500 # $1500 per new back-office laptop
        
        # Accounting: 1% of Rev or CFO hire ($150k/yr) at $5M Annual Revenue
        annual_rev = total_rev * 12
        if annual_rev >= 5000000:
            acct_cost = (150000 / 12) * fringe
            cfo_active = True
        else:
            acct_cost = total_rev * 0.01
            cfo_active = False

        total_op_ex = mktg + emr_it + ai_notes + legal + billing + leadtrap + ats + indeed + hardware + acct_cost + (cl_rent if m >= 13 else 0)

        # 6. PROFIT
        cogs = (h_ih53 * pay_rbt * fringe) + (h_cl53 * pay_rbt * fringe) + ((h_ih55 + h_cl55) * pay_bcba * fringe)
        total_eb_pre = total_rev - cogs - ih_fixed - cl_fixed - total_op_ex
        p_share = (total_eb_pre * 0.05) if (m >= 13 and total_eb_pre > 0) else 0
        ebitda = total_eb_pre - p_share
        cum_ebitda += ebitda

        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "Revenue": total_rev, "EBITDA": ebitda, "Cum_EBITDA": cum_ebitda, "Total_Cases": total_cases,
            "IH_Cases": ih_cases, "CL_Cases": cl_cases, "Headcount": total_headcount,
            "OpEx_Billing": billing, "OpEx_Mktg": mktg, "OpEx_EMR_IT": emr_it, "OpEx_AI": ai_notes,
            "OpEx_Acct": acct_cost, "OpEx_Hardware": hardware, "CFO_Active": cfo_active,
            "IH_R": r_ih, "CL_R": r_cl, "COGS": cogs, "Fixed": ih_fixed + cl_fixed, "Rent": (cl_rent if m >= 13 else 0),
            "IH_H53": h_ih53, "CL_H53": h_cl53, "IH_H55": h_ih55, "CL_H55": h_cl55, "IH_H51": h_ih51, "CL_H51": h_cl51,
            "IH_Staff": ih_staff_list, "CL_Staff": cl_staff_list, "P_Share": p_share
        })
    return pd.DataFrame(data)

df = run_model(st.session_state.manual_hires, ih_h, cl_h)

# --- MILESTONES HEADER ---
m1, m2, m3, m4 = st.columns(4)
def find_m(target):
    match = df[df['Cum_EBITDA'] >= target]
    return f"Month {match.iloc[0]['Month']}" if not match.empty else "N/A"

m1.metric("🎯 $500k Profit", find_m(500000))
m2.metric("🚀 $1M Profit", find_m(1000000))
m3.metric("🏛️ Year 5 EBITDA", f"${df.iloc[-12:]['EBITDA'].sum():,.0f}")
m4.metric("👥 Peak Headcount", f"{int(df['Headcount'].max())} Staff")

# --- VIEW FORMATTING ---
def get_view():
    g_map = {"Monthly": ["Month"], "Quarterly": ["Year", "Quarter"], "Yearly": ["Year"]}
    aggs = {'Total_Cases':'max', 'Revenue':'sum', 'EBITDA':'sum', 'Headcount':'max', 'OpEx_Billing':'sum', 'OpEx_Mktg':'sum', 'OpEx_EMR_IT':'sum', 'OpEx_AI':'sum', 'OpEx_Acct':'sum', 'COGS':'sum', 'Fixed':'sum'}
    board = df.groupby(g_map[view_type]).agg(aggs).reset_index()
    if view_type == "Monthly": board['Period'] = board['Month'].apply(lambda x: f"Month {x}")
    elif view_type == "Quarterly": board['Period'] = board.apply(lambda x: f"Y{int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    else: board['Period'] = board['Year'].apply(lambda x: f"Year {x}")
    board['Margin %'] = (board['EBITDA'] / board['Revenue'] * 100).fillna(0)
    return board

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["🌎 Consolidated", "🏠 In-Home", "🏢 Clinic", "📋 Personnel Roadmap"])

with t4:
    st.subheader("Hiring Roadmap Manager")
    with st.form("h_shield"):
        edited = st.data_editor(st.session_state.manual_hires, num_rows="dynamic", use_container_width=True)
        if st.form_submit_button("🚀 Sync Roadmap"):
            st.session_state.manual_hires = edited
            st.rerun()

def render_audit(view_df, prefix, is_total=False):
    st.markdown("---")
    drill = st.selectbox(f"Select Period ({prefix}):", view_df['Period'].tolist(), key=f"d_{prefix}")
    a = view_df[view_df['Period'] == drill].iloc[0]
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write("**💰 Divisional Expense Audit**")
        budget = pd.DataFrame([
            {"Line Item": "Medical Billing (5%)", "Cost": a['OpEx_Billing']},
            {"Line Item": "Marketing ($10k/mo)", "Cost": a['OpEx_Mktg']},
            {"Line Item": "Indeed Ads ($5k/mo)", "Cost": a['OpEx_Mktg']/2}, # Representing 5k
            {"Line Item": "EMR & IT ($190/hc)", "Cost": a['OpEx_EMR_IT']},
            {"Line Item": "AI Notechecker", "Cost": a['OpEx_AI']},
            {"Line Item": "Accounting/CFO", "Cost": a['OpEx_Acct']},
        ])
        st.table(budget.set_index('Line Item').style.format(precision=0, thousands=","))
    with c2:
        st.write("**📊 Operations**")
        st.write(f"Total Cases: {int(a['Total_Cases'])}")
        st.write(f"Total Headcount: {int(a['Headcount'])} staff")
        st.write(f"EBITDA Margin: {a['Margin %']:.1f}%")

with t1:
    v = get_view()
    st.dataframe(v[['Period', 'Total_Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v, "Enterprise", is_total=True)

with t2:
    st.write("*(Detail available in Consolidated Deep Dive)*")

with t3:
    st.write("*(Detail available in Consolidated Deep Dive)*")
