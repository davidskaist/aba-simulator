import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Executive Pro-Forma", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
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

# --- SIDEBAR: DRIVERS ---
with st.sidebar:
    st.header("🏠 In-Home Division")
    ih_start = st.number_input("Existing Cases (Acquired)", value=40)
    ih_growth = st.slider("Monthly New Intake", 0, 10, 2)
    ih_h = st.slider("Home Avg Hours/Week", 5, 25, 14)

    st.header("🏢 Clinic Division")
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
    clean_hires = hiring_data.copy()
    for col in ['Count', 'Salary', 'Month']:
        clean_hires[col] = pd.to_numeric(clean_hires[col], errors='coerce').fillna(0)

    for m in range(1, months + 1):
        # 1. VOLUME
        new_ih = ih_growth if m > 1 else 0
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
            staff_obj = {"Role": row['Role'], "Cost": cost, "Month": m}
            if "Clinic" in row['Role']: 
                cl_fixed += cost
                cl_staff_list.append(staff_obj)
            else: 
                ih_fixed += cost
                ih_staff_list.append(staff_obj)

        # 3. REVENUE MATH (IN-HOME)
        h_ih_53 = (ih_cases * ih_h_in * 4.33) * buffer_mult
        h_ih_55 = (ih_cases * 2 * 4.33) * buffer_mult
        h_ih_51 = ((new_ih + (ih_cases/6)) * 8)
        
        r_ih_53, r_ih_55, r_ih_51 = h_ih_53 * 4 * r_97153, h_ih_55 * 4 * r_97155, h_ih_51 * 4 * r_97151
        ih_rev = r_ih_53 + r_ih_55 + r_ih_51
        ih_cogs = (h_ih_53 * pay_rbt * fringe) + (h_ih_55 * pay_bcba * fringe)
        ih_ebitda = ih_rev - ih_cogs - ih_fixed - (ih_rev * 0.05)

        # 4. REVENUE MATH (CLINIC) - PRE-DEFINED TO PREVENT ERRORS
        cl_rev, cl_cogs, cl_ebitda = 0, 0, 0
        h_cl_53, h_cl_55, h_cl_51 = 0, 0, 0
        r_cl_53, r_cl_55, r_cl_51 = 0, 0, 0
        
        if m >= 13:
            h_cl_53 = (cl_cases * cl_h_in * 4.33) * buffer_mult
            h_cl_55 = (cl_cases * 2 * 4.33) * buffer_mult
            h_cl_51 = (((20/24) + (cl_cases/6)) * 8)
            r_cl_53, r_cl_55, r_cl_51 = h_cl_53 * 4 * r_97153, h_cl_55 * 4 * r_97155, h_cl_51 * 4 * r_97151
            cl_rev = r_cl_53 + r_cl_55 + r_cl_51
            cl_cogs = (h_cl_53 * pay_rbt * fringe) + (h_cl_55 * pay_bcba * fringe)
            cl_ebitda = cl_rev - cl_cogs - cl_fixed - cl_rent - (cl_rev * 0.05)

        total_ebitda_pre = ih_ebitda + cl_ebitda
        p_share = (total_ebitda_pre * 0.05) if (m >= 13 and total_ebitda_pre > 0) else 0

        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "IH_Cases": ih_cases, "IH_Rev": ih_rev, "IH_EBITDA": ih_ebitda, 
            "IH_H53": h_ih_53, "IH_H55": h_ih_55, "IH_H51": h_ih_51,
            "IH_R53": r_ih_53, "IH_R55": r_ih_55, "IH_R51": r_ih_51, "IH_Staff": ih_staff_list,
            "CL_Cases": cl_cases, "CL_Rev": cl_rev, "CL_EBITDA": cl_ebitda,
            "CL_H53": h_cl_53, "CL_H55": h_cl_55, "CL_H51": h_cl_51,
            "CL_R53": r_cl_53, "CL_R55": r_cl_55, "CL_R51": r_cl_51, "CL_Staff": cl_staff_list,
            "Total_Rev": ih_rev + cl_rev, "Total_EBITDA": total_ebitda_pre - p_share, "P_Share": p_share
        })
    return pd.DataFrame(data)

# Process Data
df = run_model(st.session_state.manual_hires, ih_h, cl_h)

# --- VIEW FORMATTING ---
def get_view(df_in, prefix, is_total=False):
    group_map = {"Monthly": ["Month"], "Quarterly": ["Year", "Quarter"], "Yearly": ["Year"]}
    aggs = {
        'IH_Cases':'max','CL_Cases':'max','IH_Rev':'sum','IH_EBITDA':'sum','CL_Rev':'sum','CL_EBITDA':'sum',
        'Total_Rev':'sum','Total_EBITDA':'sum','IH_H53':'sum','IH_H55':'sum','IH_H51':'sum',
        'IH_R53':'sum','IH_R55':'sum','IH_R51':'sum','CL_H53':'sum','CL_H55':'sum','CL_H51':'sum',
        'CL_R53':'sum','CL_R55':'sum','CL_R51':'sum','P_Share':'sum'
    }
    board = df_in.groupby(group_map[view_type]).agg(aggs).reset_index()
    
    if view_type == "Monthly": board['Period'] = board.apply(lambda x: f"Month {int(x['Month'])}", axis=1)
    elif view_type == "Quarterly": board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    else: board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])}", axis=1)

    board['Cases'] = board['IH_Cases'] + board['CL_Cases'] if is_total else board[f'{prefix}_Cases']
    board['Revenue'] = board['Total_Rev'] if is_total else board[f'{prefix}_Rev']
    board['EBITDA'] = board['Total_EBITDA'] if is_total else board[f'{prefix}_EBITDA']
    board['Margin %'] = (board['EBITDA'] / board['Revenue'] * 100).fillna(0)
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

def render_audit(df_view, prefix, is_total=False):
    st.markdown("---")
    st.subheader(f"🔍 Audit Trail: {prefix}")
    drill = st.selectbox(f"Select Period:", df_view['Period'].tolist(), key=f"d_{prefix}")
    a = df_view[df_view['Period'] == drill].iloc[0]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<div class='audit-card'><b>💰 CPT Revenue Breakdown</b>", unsafe_allow_html=True)
        if is_total:
            st.write(f"In-Home Revenue: ${a['IH_Rev']:,.0f}")
            st.write(f"Clinic Revenue: ${a['CL_Rev']:,.0f}")
            if a['P_Share'] > 0: st.write(f"Profit Share: -${a['P_Share']:,.0f}")
        else:
            cpt_data = [
                {"Code": "97153 (Direct)", "Hours": a[f'{prefix}_H53'], "Units": a[f'{prefix}_H53']*4, "Revenue": a[f'{prefix}_R53']},
                {"Code": "97155 (Super)", "Hours": a[f'{prefix}_H55'], "Units": a[f'{prefix}_H55']*4, "Revenue": a[f'{prefix}_R55']},
                {"Code": "97151 (Assess)", "Hours": a[f'{prefix}_H51'], "Units": a[f'{prefix}_H51']*4, "Revenue": a[f'{prefix}_R51']},
            ]
            st.table(pd.DataFrame(cpt_data).set_index('Code').style.format({"Hours": "{:,.0f}", "Units": "{:,.0f}", "Revenue": "${:,.0f}"}))
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<div class='audit-card'><b>🏛️ Personnel Expense</b>", unsafe_allow_html=True)
        if is_total:
            st.write("Drill down into individual tabs for role list.")
        else:
            if view_type == "Monthly": m_list = [a['Month']]
            elif view_type == "Quarterly": m_list = df[(df['Year'] == a['Year']) & (df['Quarter'] == a['Quarter'])]['Month'].tolist()
            else: m_list = df[df['Year'] == a['Year']]['Month'].tolist()
            
            p_staff = []
            for m in m_list: p_staff.extend(df[df['Month'] == m].iloc[0][f'{prefix}_Staff'])
            
            if p_staff:
                s_sum = pd.DataFrame(p_staff).groupby("Role")['Cost'].sum().reset_index()
                for _, s in s_sum.iterrows(): st.write(f"- {s['Role']}: ${s['Cost']:,.0f}")
            else:
                st.write("No staff costs assigned to this division.")
        st.markdown("</div>", unsafe_allow_html=True)

with t1:
    v_total = get_view(df, "", is_total=True)
    st.markdown("<div class='division-header'><h3>Total Enterprise Summary</h3></div>", unsafe_allow_html=True)
    st.dataframe(v_total[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v_total, "Enterprise", is_total=True)

with t2:
    v_ih = get_view(df, "IH")
    st.markdown("<div class='division-header'><h3>In-Home Division Only</h3></div>", unsafe_allow_html=True)
    st.dataframe(v_ih[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v_ih, "IH")

with t3:
    v_cl = get_view(df, "CL")
    st.markdown("<div class='division-header'><h3>Clinic Division Only</h3></div>", unsafe_allow_html=True)
    st.dataframe(v_cl[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_audit(v_cl, "CL")
