import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="ABA Executive Financial Suite", layout="wide")

# Professional Styling
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 20px; color: #1e3a8a; font-weight: bold; }
    .audit-card { background-color: #f1f5f9; padding: 15px; border-radius: 8px; border-left: 5px solid #1e3a8a; margin-bottom: 10px; min-height: 150px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 ABA 5-Year Executive Board Model")

# --- PERSISTENT DATA LOGIC ---
if 'manual_hires' not in st.session_state:
    st.session_state.manual_hires = pd.DataFrame([
        {"Month": 1, "Role": "Clinical Director", "Salary": 140000, "Count": 1},
        {"Month": 1, "Role": "Admin/Billing", "Salary": 60000, "Count": 1},
        {"Month": 13, "Role": "State Director", "Salary": 150000, "Count": 0},
    ])

# --- SIDEBAR: DRIVERS ---
with st.sidebar:
    st.header("💰 Reimbursement Rates")
    r_97153 = st.number_input("RBT Direct (97153) /unit", value=17.0)
    r_97155 = st.number_input("BCBA Super (97155) /unit", value=23.0)
    r_97151 = st.number_input("Assessment (97151) /unit", value=29.0)
    
    st.header("💸 Payroll & Fringe")
    pay_rbt = st.number_input("RBT Hourly Pay", value=25.0)
    pay_bcba_billable = st.number_input("BCBA Billable Hourly", value=85.0)
    fringe = (st.slider("Fringe Benefits %", 10, 35, 20) / 100) + 1

    st.header("📈 Growth Engine")
    start_cases = st.number_input("Starting Case Load", value=40)
    growth_mo = st.slider("Monthly Net Growth", 0, 20, 5)
    
    st.header("🏥 Clinical Intensity")
    ih_hours = st.slider("Avg In-Home Hours/Week", 5, 40, 14)
    cl_hours = st.slider("Avg Clinic Hours/Week", 5, 45, 30)

    # --- NEW: HEADCOUNT TRACKER ---
    st.header("👥 Team Summary")
    # Pre-clean for sidebar metric
    temp_hiring = st.session_state.manual_hires.copy()
    for col in ['Count', 'Salary', 'Month']:
        temp_hiring[col] = pd.to_numeric(temp_hiring[col], errors='coerce').fillna(0)
    total_hc = temp_hiring['Count'].sum()
    st.metric("Fixed Salary Headcount", f"{int(total_hc)} Staff")
    
    st.header("⚙️ View Settings")
    view_type = st.radio("Select P&L Granularity:", ["Monthly", "Quarterly", "Yearly"], horizontal=True)

# --- THE CALCULATOR ---
def run_board_model(hiring_data, ih_h, cl_h):
    months = 60
    data = []
    cumulative_ebitda = 0
    
    # Defensive Logic: Clean the data before math
    clean_hires = hiring_data.copy()
    for col in ['Count', 'Salary', 'Month']:
        clean_hires[col] = pd.to_numeric(clean_hires[col], errors='coerce').fillna(0)

    for m in range(1, months + 1):
        cases = int(start_cases + (growth_mo * (m-1)))
        
        # Blended Unit calculations (60% In-Home / 40% Clinic)
        ih_cases = cases * 0.6
        cl_cases = cases * 0.4
        
        # Monthly Direct Hours (Weekly * 4.33 weeks/mo)
        h_97153 = ((ih_cases * ih_h) + (cl_cases * cl_h)) * 4.33
        
        # Supervision and Assessment remain case-based
        h_97155 = cases * 2 * 4.33
        h_97151 = cases * (8/6)
        
        rev_97153 = h_97153 * 4 * r_97153
        rev_97155 = h_97155 * 4 * r_97155
        rev_97151 = h_97151 * 4 * r_97151
        total_rev = rev_97153 + rev_97155 + rev_97151
        
        c_rbt = (h_97153 * pay_rbt * fringe)
        c_bcba = ((h_97155 + h_97151) * pay_bcba_billable * fringe)
        
        active_hires = clean_hires[clean_hires['Month'] <= m].copy()
        fixed_labor_mo = (active_hires['Salary'] * active_hires['Count']).sum() / 12 * fringe
        
        op_ex = 5000 + (total_rev * 0.06) + (int(np.ceil(m/12)) * 3000)
        ebitda = total_rev - (c_rbt + c_bcba + fixed_labor_mo + op_ex)
        cumulative_ebitda += ebitda
        
        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "Cases": cases, "Revenue": total_rev, "COGS": c_rbt + c_bcba, 
            "Fixed Labor": fixed_labor_mo, "OpEx": op_ex, "EBITDA": ebitda, "Cumulative": cumulative_ebitda,
            "R_97153": rev_97153, "R_97155": rev_97155, "R_97151": rev_97151,
            "H_97153": h_97153, "H_97155": h_97155, "H_97151": h_97151,
            "C_RBT": c_rbt, "C_BCBA": c_bcba, "Staff_Snap": active_hires.to_dict('records')
        })
    return pd.DataFrame(data)

# Process Data
df = run_board_model(st.session_state.manual_hires, ih_hours, cl_hours)

# --- TABS ---
tab1, tab2 = st.tabs(["🏛️ Executive P&L Board", "📋 Editable Hiring Roadmap"])

with tab2:
    st.subheader("Personnel & Hiring Triggers")
    st.info("💡 Edit roles. Note: To ensure 'Month' and 'Count' stick, click outside the table after typing.")
    # Renaming Key to force reset and better binding
    st.session_state.manual_hires = st.data_editor(st.session_state.manual_hires, num_rows="dynamic", key="hiring_v3")

with tab1:
    # 1. MILESTONES
    m1, m2, m3, m4 = st.columns(4)
    def find_m(target):
        match = df[df['Cumulative'] >= target]
        return f"Month {match.iloc[0]['Month']}" if not match.empty else "N/A"
    
    m1.metric("🎯 $500k Cumul. Profit", find_m(500000))
    m2.metric("🚀 $1M Cumul. Profit", find_m(1000000))
    m3.metric("🏛️ $2M Cumul. Profit", find_m(2000000))
    m4.metric("💰 Year 5 EBITDA", f"${df.iloc[-12:]['EBITDA'].sum():,.0f}")

    # 2. AGGREGATION
    if view_type == "Quarterly":
        board_df = df.groupby(["Year", "Quarter"]).agg({
            'Cases': 'max', 'Revenue': 'sum', 'COGS': 'sum', 'Fixed Labor': 'sum', 'OpEx': 'sum', 'EBITDA': 'sum',
            'R_97153':'sum', 'R_97155':'sum', 'R_97151':'sum', 'H_97153':'sum', 'H_97155':'sum', 'H_97151':'sum',
            'C_RBT':'sum', 'C_BCBA':'sum'
        }).reset_index().sort_values(['Year', 'Quarter'])
        board_df['Period'] = board_df.apply(lambda x: f"Year {int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    elif view_type == "Yearly":
        board_df = df.groupby("Year").agg({
            'Cases': 'max', 'Revenue': 'sum', 'COGS': 'sum', 'Fixed Labor': 'sum', 'OpEx': 'sum', 'EBITDA': 'sum',
            'R_97153':'sum', 'R_97155':'sum', 'R_97151':'sum', 'H_97153':'sum', 'H_97155':'sum', 'H_97151':'sum',
            'C_RBT':'sum', 'C_BCBA':'sum'
        }).reset_index().sort_values('Year')
        board_df['Period'] = board_df.apply(lambda x: f"Year {int(x['Year'])}", axis=1)
    else:
        board_df = df.copy()
        board_df['Period'] = board_df.apply(lambda x: f"Month {int(x['Month'])}", axis=1)

    # 3. MAIN TABLE
    st.subheader(f"Projected P&L Summary")
    display_df = board_df[['Period', 'Cases', 'Revenue', 'COGS', 'Fixed Labor', 'OpEx', 'EBITDA']].set_index('Period').T
    st.dataframe(display_df.style.format(precision=0, thousands=","), use_container_width=True)
    
    st.markdown("---")
    
    # 4. DEEP DIVE
    st.subheader("🔍 Deep Dive Audit Trail")
    periods = board_df['Period'].tolist()
    if periods:
        drill_period = st.selectbox("Select a period to audit:", periods)
        audit = board_df[board_df['Period'] == drill_period].iloc[0]
        
        a1, a2, a3 = st.columns(3)
        with a1:
            st.markdown("<div class='audit-card'><b>💰 Revenue Breakdown</b><br>", unsafe_allow_html=True)
            st.write(f"97153 (Direct): ${audit['R_97153']:,.0f} ({int(audit['H_97153']):,} hrs)")
            st.write(f"97155 (Super): ${audit['R_97155']:,.0f} ({int(audit['H_97155']):,} hrs)")
            st.write(f"97151 (Assess): ${audit['R_97151']:,.0f} ({int(audit['H_97151']):,} hrs)")
            st.markdown("</div>", unsafe_allow_html=True)
        with a2:
            st.markdown("<div class='audit-card'><b>💸 Variable Labor (COGS)</b><br>", unsafe_allow_html=True)
            st.write(f"RBT Payroll: ${audit['C_RBT']:,.0f}")
            st.write(f"BCBA Billable: ${audit['C_BCBA']:,.0f}")
            st.write(f"*(Based on {ih_hours}h IH / {cl_hours}h Clinic Avg)*")
            st.markdown("</div>", unsafe_allow_html=True)
        with a3:
            st.markdown("<div class='audit-card'><b>🏛️ Fixed Labor Personnel</b><br>", unsafe_allow_html=True)
            if view_type == "Monthly":
                month_val = int(drill_period.split(" ")[1])
                staff_info = df[df['Month'] == month_val].iloc[0]['Staff_Snap']
                for s in staff_info:
                    if s.get('Count', 0) > 0:
                        st.write(f"- {s.get('Role')}: ${s.get('Salary',0)/12*fringe:,.0f}/mo")
            else:
                st.write(f"Total Period Fixed Labor: ${audit['Fixed Labor']:,.0f}")
            st.markdown("</div>", unsafe_allow_html=True)

    # Excel Download
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Monthly_Detailed')
        board_df.to_excel(writer, index=False, sheet_name='Executive_Summary')
    st.download_button("📥 Download Board Financials", output.getvalue(), "ABA_Executive_Proforma.xlsx")
