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
    r_97155 = st.number_input("BCBA Super (97155) /unit", value=23.0)
    pay_rbt = st.number_input("RBT Hourly Pay", value=25.0)
    pay_bcba = st.number_input("BCBA Billable Hourly", value=85.0)
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
        cl_cases = 0 if m < 13 else (20 / 24) * min(m - 12, 24)

        active_staff = clean_hires[clean_hires['Month'] <= m]
        cc_required = max(1, int(np.ceil((ih_cases + cl_cases) / 50)))
        
        ih_fixed, cl_fixed = 0, 0
        ih_staff_list, cl_staff_list = [], []
        
        for _, row in active_staff.iterrows():
            cnt = cc_required if "Care Coordinator" in row['Role'] else row['Count']
            cost = (row['Salary'] * cnt) / 12 * fringe
            if "Clinic" in row['Role']: 
                cl_fixed += cost
                cl_staff_list.append({"Role": row['Role'], "Cost": cost})
            else: 
                ih_fixed += cost
                ih_staff_list.append({"Role": row['Role'], "Cost": cost})
        
        h_ih = ih_cases * ih_h_in * 4.33
        s_ih = ih_cases * 2 * 4.33
        ih_rev = (h_ih * 4 * r_97153) + (s_ih * 4 * r_97155) + (ih_cases * 150)
        ih_cogs = (h_ih * pay_rbt * fringe) + (s_ih * pay_bcba * fringe)
        ih_ebitda = ih_rev - ih_cogs - ih_fixed - (ih_rev * 0.05)
        
        cl_rev, cl_cogs, cl_ebitda, h_cl, s_cl = 0, 0, 0, 0, 0
        if m >= 13:
            h_cl = cl_cases * cl_h_in * 4.33
            s_cl = cl_cases * 2 * 4.33
            cl_rev = (h_cl * 4 * r_97153) + (s_cl * 4 * r_97155) + (cl_cases * 150)
            cl_cogs = (h_cl * pay_rbt * fringe) + (s_cl * pay_bcba * fringe)
            cl_ebitda = cl_rev - cl_cogs - cl_fixed - cl_rent - (cl_rev * 0.05)

        total_ebitda_pre = ih_ebitda + cl_ebitda
        p_share = (total_ebitda_pre * 0.05) if (m >= 13 and total_ebitda_pre > 0) else 0
        
        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "IH_Cases": ih_cases, "IH_Revenue": ih_rev, "IH_EBITDA": ih_ebitda, "IH_Hours": h_ih, "IH_Staff": ih_staff_list,
            "CL_Cases": cl_cases, "CL_Revenue": cl_rev, "CL_EBITDA": cl_ebitda, "CL_Hours": h_cl, "CL_Staff": cl_staff_list,
            "Total_Revenue": ih_rev + cl_rev, "Total_EBITDA": total_ebitda_pre - p_share, "P_Share": p_share
        })
    return pd.DataFrame(data)

df = run_model(st.session_state.manual_hires, ih_h, cl_h)

def get_board_view(df_in, prefix, is_total=False):
    if view_type == "Monthly":
        board = df_in.copy()
        board['Period'] = board.apply(lambda x: f"Month {int(x['Month'])}", axis=1)
    elif view_type == "Quarterly":
        board = df_in.groupby(["Year", "Quarter"]).agg({'IH_Cases':'max','CL_Cases':'max','IH_Revenue':'sum','IH_EBITDA':'sum','CL_Revenue':'sum','CL_EBITDA':'sum','Total_Revenue':'sum','Total_EBITDA':'sum','IH_Hours':'sum','CL_Hours':'sum','P_Share':'sum'}).reset_index().sort_values(['Year','Quarter'])
        board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    else:
        board = df_in.groupby("Year").agg({'IH_Cases':'max','CL_Cases':'max','IH_Revenue':'sum','IH_EBITDA':'sum','CL_Revenue':'sum','CL_EBITDA':'sum','Total_Revenue':'sum','Total_EBITDA':'sum','IH_Hours':'sum','CL_Hours':'sum','P_Share':'sum'}).reset_index().sort_values('Year')
        board['Period'] = board.apply(lambda x: f"Year {int(x['Year'])}", axis=1)

    if is_total:
        board['Cases'], board['Revenue'], board['EBITDA'] = board['IH_Cases'] + board['CL_Cases'], board['Total_Revenue'], board['Total_EBITDA']
    else:
        board['Cases'], board['Revenue'], board['EBITDA'] = board[f'{prefix}_Cases'], board[f'{prefix}_Revenue'], board[f'{prefix}_EBITDA']
    
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

def render_deep_dive(df_source, period_list, prefix, is_total=False):
    st.markdown("---")
    st.subheader(f"🔍 Deep Dive Audit: {prefix if not is_total else 'Enterprise'}")
    drill = st.selectbox(f"Select Period ({prefix}):", period_list, key=f"drill_{prefix}")
    audit = df_source[df_source['Period'] == drill].iloc[0]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='audit-card'><b>📊 Revenue & Volume</b>", unsafe_allow_html=True)
        if is_total:
            st.write(f"Total Revenue: ${audit['Total_Revenue']:,.0f}")
            st.write(f"Blended Cases: {int(audit['IH_Cases'] + audit['CL_Cases'])}")
        else:
            st.write(f"Revenue: ${audit[f'{prefix}_Revenue']:,.0f}")
            st.write(f"Total Hours: {int(audit[f'{prefix}_Hours']):,}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='audit-card'><b>💸 Profitability</b>", unsafe_allow_html=True)
        ebitda_val = audit['Total_EBITDA'] if is_total else audit[f'{prefix}_EBITDA']
        rev_val = audit['Total_Revenue'] if is_total else audit[f'{prefix}_Revenue']
        st.write(f"EBITDA: ${ebitda_val:,.0f}")
        st.write(f"Margin: {(ebitda_val/rev_val*100):.1f}%")
        if is_total and audit['P_Share'] > 0: st.write(f"Partner Share: -${audit['P_Share']:,.0f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='audit-card'><b>🏛️ Staffing</b>", unsafe_allow_html=True)
        if view_type == "Monthly" and not is_total:
            m_idx = int(drill.split(" ")[1])
            staff = df[df['Month'] == m_idx].iloc[0][f'{prefix}_Staff']
            for s in staff: st.write(f"- {s['Role']}: ${s['Cost']:,.0f}")
        else:
            st.write("Summary view active.")
            st.write("*(Switch to Monthly for role list)*")
        st.markdown("</div>", unsafe_allow_html=True)

with tab1:
    view_df = get_board_view(df, "", is_total=True)
    st.markdown("<div class='division-header'><h3>Combined Enterprise Summary</h3></div>", unsafe_allow_html=True)
    st.dataframe(view_df[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_deep_dive(view_df, view_df['Period'].tolist(), "Total", is_total=True)

with tab2:
    view_df_ih = get_board_view(df, "IH")
    st.markdown("<div class='division-header'><h3>In-Home Division Only</h3></div>", unsafe_allow_html=True)
    st.dataframe(view_df_ih[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_deep_dive(view_df_ih, view_df_ih['Period'].tolist(), "IH")

with tab3:
    view_df_cl = get_board_view(df, "CL")
    st.markdown("<div class='division-header'><h3>Clinic Division Only (Starts Y2)</h3></div>", unsafe_allow_html=True)
    st.dataframe(view_df_cl[['Period', 'Cases', 'Revenue', 'EBITDA', 'Margin %']].set_index('Period').T.style.format(precision=0, thousands=","), use_container_width=True)
    render_deep_dive(view_df_cl, view_df_cl['Period'].tolist(), "CL")
