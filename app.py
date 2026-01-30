import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Audit-Ready Model", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .audit-card { background-color: #f1f5f9; padding: 15px; border-radius: 8px; border-left: 5px solid #1e3a8a; margin-bottom: 10px; min-height: 150px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Strides ABA: Multi-Divisional Financial Model")

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
    # This reduces revenue to account for sick days, cancellations, etc.
    cancellation_rate = st.slider("Cancellation/No-Show %", 0, 30, 10) / 100
    buffer_mult = 1 - cancellation_rate

    st.header("💰 Global Economics")
    r_97153 = st.number_input("RBT Direct (97153) /unit", value=17.0)
    r_97155 = st.number_input("BCBA Super (97155) /unit", value=23.0)
    r_97151 = st.number_input("Assessment (97151) /unit", value=29.0)
    pay_rbt = st.number_input("RBT Hourly Pay", value=25.0)
    pay_bcba = st.number_input("BCBA Billable Hourly", value=85.0)
    fringe = (st.slider("Fringe Benefits %", 10, 35, 20) / 100) + 1
    
    view_type = st.radio("Display Granularity:", ["Yearly", "Quarterly", "Monthly"])

# --- CALCULATOR ---
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

        # 2. FIXED LABOR
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
        # IN-HOME
        h_ih = (ih_cases * ih_h_in * 4.33) * buffer_mult
        s_ih = (ih_cases * 2 * 4.33) * buffer_mult
        # Re-assess 1/6th of total kids each month
        assess_h_ih = ((new_ih + (ih_cases/6)) * 8)
        
        r_ih_53, r_ih_55, r_ih_51 = h_ih * 4 * r_97153, s_ih * 4 * r_97155, assess_h_ih * 4 * r_97151
        ih_rev = r_ih_53 + r_ih_55 + r_ih_51
        ih_cogs = (h_ih * pay_rbt * fringe) + (s_ih * pay_bcba * fringe)
        ih_ebitda = ih_rev - ih_cogs - ih_fixed - (ih_rev * 0.05)

        # CLINIC
        cl_rev, cl_cogs, cl_ebitda, h_cl, s_cl, r_cl_51 = 0, 0, 0, 0, 0, 0
        if m >= 13:
            h_cl = (cl_cases * cl_h_in * 4.33) * buffer_mult
            s_cl = (cl_cases * 2 * 4.33) * buffer_mult
            assess_h_cl = (( (20/24) + (cl_cases/6) ) * 8)
            r_cl_53, r_cl_55, r_cl_51 = h_cl * 4 * r_97153, s_cl * 4 * r_97155, assess_h_cl * 4 * r_97151
            cl_rev = r_cl_53 + r_cl_55 + r_cl_51
            cl_cogs = (h_cl * pay_rbt * fringe) + (s_cl * pay_bcba * fringe)
            cl_ebitda = cl_rev - cl_cogs - cl_fixed - cl_rent - (cl_rev * 0.05)

        total_ebitda_pre = ih_ebitda + cl_ebitda
        p_share = (total_ebitda_pre * 0.05) if (m >= 13 and total_ebitda_pre > 0) else 0

        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "IH_Cases": ih_cases, "IH_Revenue": ih_rev, "IH_EBITDA": ih_ebitda, "IH_Hours": h_ih, "IH_Staff": ih_staff_list, "IH_51": r_ih_51,
            "CL_Cases": cl_cases, "CL_Revenue": cl_rev, "CL_EBITDA": cl_ebitda, "CL_Hours": h_cl, "CL_Staff": cl_staff_list, "CL_51": r_cl_51,
            "Total_Revenue": ih_rev + cl_rev, "Total_EBITDA": total_ebitda_pre - p_share, "P_Share": p_share
        })
    return pd.DataFrame(data)

df = run_model(st.session_state.manual_hires, ih_h, cl_h)

def get_board_view(df_in, prefix, is_total=False):
    if view_type == "Monthly":
        board = df_in.copy()
        board['Period'] = board.apply(lambda x: f"Month {int(x['Month'])}", axis=1)
    elif view_type == "Quarterly":
        board = df_in.groupby(["Year", "Quarter"]).agg({'IH_Cases':'max','CL_Cases':'max','IH_Revenue':'sum','IH_EBITDA':'sum','CL_Revenue':'sum','CL_EBITDA':'sum','Total_Revenue':'sum','Total_EBITDA':'sum','IH_Hours':'sum','CL_Hours':'sum','P_Share':'sum','IH_51':'sum','CL_51':'sum'}).reset_index()
        board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    else:
        board = df_in.groupby("Year").agg({'IH_Cases':'max','CL_Cases':'max','IH_Revenue':'sum','IH_EBITDA':'sum','CL_Revenue':'sum','CL_EBITDA':'sum','Total_Revenue':'sum','Total_EBITDA':'sum','IH_Hours':'sum','CL_Hours':'sum','P_Share':'sum','IH_51':'sum','CL_51':'sum'}).reset_index()
        board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])}", axis=1)

    board['Cases'] = board['IH_Cases'] + board['CL_Cases'] if is_total else board[f'{prefix}_Cases']
    board['Revenue'] = board['Total_Revenue'] if is_total else board[f'{prefix}_Revenue']
    board['EBITDA'] = board['Total_EBITDA'] if is_total else board[f'{prefix}_EBITDA']
    board['Margin %'] = (board['EBITDA'] / board['Revenue'] * 100).fillna(0)
    return board

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🌎 Consolidated", "🏠 In-Home", "🏢 Clinic", "📋 Personnel Roadmap"])

with tab4:
    st.subheader("Personnel Manager")
    with st.form("hiring_shield"):
        edited = st.data_editor(st.session_state.manual_hires, num_rows="dynamic", use_container_width=True)
        if st.form_submit_button("🚀 Sync Roadmap"):
            st.session_state.manual_hires = edited
            st.rerun()

def render_deep_dive(df_source, prefix, is_total=False):
    st.markdown("---")
    st.subheader(f"🔍 Deep Dive Audit: {prefix if not is_total else 'Enterprise'}")
    drill = st.selectbox(f"Select Period to Audit ({prefix}):", df_source['Period'].tolist(), key=f"drill_{prefix}")
    audit = df_source[df_source['Period'] == drill].iloc[0]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='audit-card'><b>💰 Revenue Breakdown</b>", unsafe_allow_html=True)
        if is_total:
            st.write(f"In-Home 97151: ${audit['IH_51']:,.0f}")
            st.write(f"Clinic 97151: ${audit['CL_51']:,.0f}")
        else:
            st.write(f"Assessment (97151) Rev: ${audit[f'{prefix}_51']:,.0f}")
            st.write(f"Total Direct Hours: {int(audit[f'{prefix}_Hours']):,}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='audit-card'><b>💸 Profitability</b>", unsafe_allow_html=True)
        st.write(f"EBITDA: ${audit['Total_EBITDA'] if is_total else audit[f'{prefix}_EBITDA']:,.0f}")
        st.write(f"Margin: {audit['Margin %']:.1f}%")
        if is_total and audit['P_Share'] > 0: st.write(f"Partner Share: -${audit['P_Share']:,.0f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='audit-card'><b>🏛️ Monthly Personnel</b>", unsafe_allow_html=True)
        if view_type == "Monthly" and not is_total:
            m_idx = int(drill.split(" ")[1])
            staff = df[df['Month'] == m_idx].iloc[0][f'{prefix}_Staff']
            for s in staff: st.write(f"- {s['Role']}: ${s['Cost']:,.0f}")
        else:
            st.write("Switch to Monthly view to see role list.")
        st.markdown("</div>", unsafe_allow_html=True)

with tab1:
    v_total = get_board_view(df, "", is_total=True)
    st.dataframe(v_total[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_deep_dive(v_total, "Total", is_total=True)

with tab2:
    v_ih = get_board_view(df, "IH")
    st.dataframe(v_ih[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_deep_dive(v_ih, "IH")

with tab3:
    v_cl = get_board_view(df, "CL")
    st.dataframe(v_cl[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_deep_dive(v_cl, "CL")
