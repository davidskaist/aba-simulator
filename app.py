import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Final Investor Suite", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .audit-card { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
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

# --- SIDEBAR: ALL DRIVERS RESTORED ---
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

        # 2. PERSONNEL
        active_staff = clean_hires[clean_hires['Month'] <= m]
        cc_req = max(1, int(np.ceil(total_cases / 50)))
        ih_fixed, cl_fixed, ih_staff_list, cl_staff_list = 0, 0, [], []
        
        for _, row in active_staff.iterrows():
            cnt = cc_req if "Care Coordinator" in row['Role'] else row['Count']
            cost = (row['Salary'] * cnt) / 12 * fringe
            if "Clinic" in row['Role']: 
                cl_fixed += cost
                cl_staff_list.append({"Role": row['Role'], "Cost": cost})
            else: 
                ih_fixed += cost
                ih_staff_list.append({"Role": row['Role'], "Cost": cost})

        # 3. DIVISIONAL MATH
        # In-Home
        h_ih53 = (ih_cases * ih_h_in * 4.33) * buffer_mult
        h_ih55 = (ih_cases * 2 * 4.33) * buffer_mult
        h_ih51 = (((ih_growth if m > 1 else 0) + (ih_cases/6)) * 8)
        r_ih = (h_ih53 * 4 * r_97153) + (h_ih55 * 4 * r_97155) + (h_ih51 * 4 * r_97151)
        c_ih = (h_ih53 * pay_rbt * fringe) + (h_ih55 * pay_bcba * fringe)
        eb_ih = r_ih - c_ih - ih_fixed - (r_ih * 0.05)

        # Clinic
        eb_cl, r_cl, h_cl53, h_cl55, h_cl51 = 0, 0, 0, 0, 0
        if m >= 13:
            h_cl53 = (cl_cases * cl_h_in * 4.33) * buffer_mult
            h_cl55 = (cl_cases * 2 * 4.33) * buffer_mult
            h_cl51 = (((20/24) + (cl_cases/6)) * 8)
            r_cl = (h_cl53 * 4 * r_97153) + (h_cl55 * 4 * r_97155) + (h_cl51 * 4 * r_97151)
            c_cl = (h_cl53 * pay_rbt * fringe) + (h_cl55 * pay_bcba * fringe)
            eb_cl = r_cl - c_cl - cl_fixed - cl_rent - (r_cl * 0.05)

        total_eb_pre = eb_ih + eb_cl
        p_share = (total_eb_pre * 0.05) if (m >= 13 and total_eb_pre > 0) else 0
        ebitda = total_eb_pre - p_share
        cum_ebitda += ebitda

        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "IH_Cases": ih_cases, "CL_Cases": cl_cases, "Revenue": r_ih + r_cl, "EBITDA": ebitda, "Cum_EBITDA": cum_ebitda,
            "IH_H53": h_ih53, "IH_H55": h_ih55, "IH_H51": h_ih51, "IH_R": r_ih, "IH_EB": eb_ih, "IH_Staff": ih_staff_list,
            "CL_H53": h_cl53, "CL_H55": h_cl55, "CL_H51": h_cl51, "CL_R": r_cl, "CL_EB": eb_cl, "CL_Staff": cl_staff_list,
            "P_Share": p_share
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
m3.metric("🏛️ Year 5 Total EBITDA", f"${df.iloc[-12:]['EBITDA'].sum():,.0f}")
m4.metric("📊 Total Year 5 Hours", f"{int(df.iloc[-12:][['IH_H53', 'CL_H53']].sum().sum()):,} hrs")

# --- VIEW FORMATTING ---
def get_view(prefix, is_total=False):
    g_map = {"Monthly": ["Month"], "Quarterly": ["Year", "Quarter"], "Yearly": ["Year"]}
    aggs = {'IH_Cases':'max','CL_Cases':'max','Revenue':'sum','EBITDA':'sum','IH_H53':'sum','IH_H55':'sum','IH_H51':'sum','CL_H53':'sum','CL_H55':'sum','CL_H51':'sum','IH_R':'sum','CL_R':'sum','IH_EB':'sum','CL_EB':'sum'}
    board = df.groupby(g_map[view_type]).agg(aggs).reset_index()
    if view_type == "Monthly": board['Period'] = board['Month'].apply(lambda x: f"Month {x}")
    elif view_type == "Quarterly": board['Period'] = board.apply(lambda x: f"Y{int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    else: board['Period'] = board['Year'].apply(lambda x: f"Year {x}")
    
    board['Disp_Cases'] = board['IH_Cases'] + board['CL_Cases'] if is_total else board[f'{prefix}_Cases']
    board['Disp_Rev'] = board['Revenue'] if is_total else board[f'{prefix}_R']
    board['Disp_EB'] = board['EBITDA'] if is_total else board[f'{prefix}_EB']
    board['Margin %'] = (board['Disp_EB'] / board['Disp_Rev'] * 100).fillna(0)
    return board

# --- DASHBOARD TABS ---
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
        st.write("**CPT Revenue & Hours**")
        if is_total:
            st.write(f"In-Home Revenue: ${a['IH_R']:,.0f} | Clinic Revenue: ${a['CL_R']:,.0f}")
        else:
            cpt = pd.DataFrame([
                {"Code": "97153 (Direct)", "Hours": a[f'{prefix}_H53'], "Revenue": a[f'{prefix}_H53']*4*r_97153},
                {"Code": "97155 (Super)", "Hours": a[f'{prefix}_H55'], "Revenue": a[f'{prefix}_H55']*4*r_97155},
                {"Code": "97151 (Assess)", "Hours": a[f'{prefix}_H51'], "Revenue": a[f'{prefix}_H51']*4*r_97151}
            ])
            st.table(cpt.set_index('Code').style.format(precision=0, thousands=","))
    with c2:
        st.write("**Personnel Audit**")
        if is_total: st.write("See individual tabs for staff list.")
        else:
            m_list = [a['Month']] if view_type == "Monthly" else df[df['Year'] == a['Year']]['Month'].tolist()
            staff = []
            for m in m_list: staff.extend(df[df['Month'] == m].iloc[0][f'{prefix}_Staff'])
            if staff:
                s_sum = pd.DataFrame(staff).groupby("Role")['Cost'].sum().reset_index()
                for _, row in s_sum.iterrows(): st.write(f"- {row['Role']}: ${row['Cost']:,.0f}")
        st.write(f"**Margin:** {a['Margin %']:.1f}%")

with t1:
    v = get_view("", is_total=True)
    st.dataframe(v[['Period', 'Disp_Cases', 'Disp_Rev', 'Disp_EB', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v, "Enterprise", is_total=True)

with t2:
    v_ih = get_view("IH")
    st.dataframe(v_ih[['Period', 'Disp_Cases', 'Disp_Rev', 'Disp_EB', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v_ih, "IH")

with t3:
    v_cl = get_view("CL")
    st.dataframe(v_cl[['Period', 'Disp_Cases', 'Disp_Rev', 'Disp_EB', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v_cl, "CL")
