import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Strides ABA: Final Investment Suite", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 18px; color: #1e3a8a; }
    .division-header { background-color: #1e3a8a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .audit-card { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; min-height: 300px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Strides ABA: Multi-Divisional Investment Model")

# --- INITIALIZE PERSISTENT DATA ---
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

if 'overhead_budget' not in st.session_state:
    st.session_state.overhead_budget = {
        "Marketing_Monthly": 10000.0,
        "Indeed_Monthly": 5000.0,
        "EMR_Per_HC": 90.0,
        "IT_Per_HC": 100.0,
        "AI_Notes_Per_30_Cases": 1800.0,
        "Billing_Pct_Revenue": 0.05,
        "Leadtrap_Monthly": 800.0,
        "ATS_Apploi_Monthly": 400.0,
        "Legal_Annual": 10000.0,
        "Hardware_Per_New_BO": 1500.0,
        "CFO_Threshold_Rev": 5000000.0,
        "CFO_Salary": 150000.0
    }

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
def run_model(hiring_data, ov_budget, ih_h_in, cl_h_in):
    months = 60
    data = []
    cum_ebitda = 0
    clean_hires = hiring_data.copy()
    for col in ['Count', 'Salary', 'Month']:
        clean_hires[col] = pd.to_numeric(clean_hires[col], errors='coerce').fillna(0)

    for m in range(1, months + 1):
        # 1. VOLUME
        new_ih = ih_growth if m > 1 else 0
        ih_cases = ih_start + (ih_growth * (m-1))
        cl_cases = 0 if m < 13 else (20 / 24) * min(m - 12, 24)
        total_cases = ih_cases + cl_cases
        mix_ih = ih_cases / total_cases if total_cases > 0 else 1
        mix_cl = 1 - mix_ih

        # 2. PERSONNEL
        active_staff = clean_hires[clean_hires['Month'] <= m]
        cc_req = max(1, int(np.ceil(total_cases / 50)))
        ih_fixed, cl_fixed, ih_staff_list, cl_staff_list = 0, 0, [], []
        fixed_hc, new_bo_hires = 0, 0
        for _, row in active_staff.iterrows():
            cnt = cc_req if "Care Coordinator" in row['Role'] else row['Count']
            cost = (row['Salary'] * cnt) / 12 * fringe
            fixed_hc += cnt
            if row['Month'] == m: new_bo_hires += cnt
            if "Clinic" in row['Role']: 
                cl_fixed += cost
                cl_staff_list.append({"Role": row['Role'], "Cost": cost})
            else: 
                ih_fixed += cost
                ih_staff_list.append({"Role": row['Role'], "Cost": cost})

        # 3. REVENUE
        h_ih53 = (ih_cases * ih_h_in * 4.33) * buffer_mult
        h_ih55 = (ih_cases * 2 * 4.33) * buffer_mult
        h_ih51 = (((ih_growth if m > 1 else 0) + (ih_cases/6)) * 8)
        rev_ih = (h_ih53 * 4 * r_97153) + (h_ih55 * 4 * r_97155) + (h_ih51 * 4 * r_97151)
        cogs_ih = (h_ih53 * pay_rbt * fringe) + (h_ih55 * pay_bcba * fringe)
        
        h_cl53, h_cl55, h_cl51, rev_cl, cogs_cl = 0, 0, 0, 0, 0
        if m >= 13:
            h_cl53 = (cl_cases * cl_h_in * 4.33) * buffer_mult
            h_cl55 = (cl_cases * 2 * 4.33) * buffer_mult
            h_cl51 = (((20/24) + (cl_cases/6)) * 8)
            rev_cl = (h_cl53 * 4 * r_97153) + (h_cl55 * 4 * r_97155) + (h_cl51 * 4 * r_97151)
            cogs_cl = (h_cl53 * pay_rbt * fringe) + (h_cl55 * pay_bcba * fringe)

        total_rev = rev_ih + rev_cl
        
        # 4. OPEX (Using Editable Budget)
        total_hc = fixed_hc + ((h_ih53 + h_cl53 + h_ih55 + h_cl55) / (25 * 4.33))
        mktg = ov_budget['Marketing_Monthly']
        indeed = ov_budget['Indeed_Monthly']
        emr = total_hc * ov_budget['EMR_Per_HC']
        it = total_hc * ov_budget['IT_Per_HC']
        ai = np.ceil(total_cases/30) * ov_budget['AI_Notes_Per_30_Cases']
        billing = total_rev * ov_budget['Billing_Pct_Revenue']
        leadtrap = ov_budget['Leadtrap_Monthly']
        ats = ov_budget['ATS_Apploi_Monthly']
        legal = ov_budget['Legal_Annual'] / 12
        hw = new_bo_hires * ov_budget['Hardware_Per_New_BO']
        acct = (ov_budget['CFO_Salary']/12*fringe) if (total_rev*12 >= ov_budget['CFO_Threshold_Rev']) else (total_rev * 0.01)
        total_op_ex = mktg+indeed+emr+it+ai+legal+billing+leadtrap+ats+hw+acct

        # 5. PROFIT
        eb_ih = rev_ih - cogs_ih - ih_fixed - (total_op_ex * mix_ih)
        eb_cl = rev_cl - cogs_cl - cl_fixed - (total_op_ex * mix_cl) - (cl_rent if m >= 13 else 0)
        p_share = ((eb_ih + eb_cl) * 0.05) if (m >= 13 and (eb_ih + eb_cl) > 0) else 0
        ebitda = (eb_ih + eb_cl) - p_share
        cum_ebitda += ebitda

        data.append({
            "Month": m, "Year": int(np.ceil(m/12)), "Quarter": int(np.ceil(((m-1) % 12 + 1)/3)),
            "Total_Rev": total_rev, "Total_EB": ebitda, "Cum_EB": cum_ebitda,
            "IH_Cases": ih_cases, "IH_Rev": rev_ih, "IH_EB": eb_ih, "IH_H53": h_ih53, "IH_H55": h_ih55, "IH_H51": h_ih51, "IH_Staff": ih_staff_list,
            "CL_Cases": cl_cases, "CL_Rev": rev_cl, "CL_EB": eb_cl, "CL_H53": h_cl53, "CL_H55": h_cl55, "CL_H51": h_cl51, "CL_Staff": cl_staff_list,
            "Op_Mktg": mktg, "Op_Indeed": indeed, "Op_EMR": emr, "Op_IT": it, "Op_AI": ai, "Op_Billing": billing, "Op_Acct": acct, "Op_Leadtrap": leadtrap, "Op_ATS": ats, "Op_Legal": legal, "Op_Hardware": hw, "Rent": (cl_rent if m >= 13 else 0), "P_Share": p_share, "Headcount": total_hc
        })
    return pd.DataFrame(data)

df = run_model(st.session_state.manual_hires, st.session_state.overhead_budget, ih_h, cl_h)

# --- MILESTONES HEADER ---
m1, m2, m3, m4 = st.columns(4)
def find_m(target):
    match = df[df['Cum_EB'] >= target]
    return f"Month {match.iloc[0]['Month']}" if not match.empty else "N/A"

m1.metric("🎯 $500k Profit Milestone", find_m(500000))
m2.metric("🚀 $1M Profit Milestone", find_m(1000000))
y5_ebitda = df.iloc[-12:]['Total_EB'].sum()
m3.metric("🏛️ Year 5 Annual EBITDA", f"${y5_ebitda:,.0f}")
m4.metric("📊 Total Headcount", f"{int(df['Headcount'].max())} people")

# --- VIEW LOGIC ---
def get_view(prefix, is_total=False):
    g_map = {"Monthly": ["Month"], "Quarterly": ["Year", "Quarter"], "Yearly": ["Year"]}
    aggs = {'Total_Rev':'sum', 'Total_EB':'sum', 'IH_Cases':'max', 'CL_Cases':'max', 'IH_Rev':'sum', 'IH_EB':'sum', 'CL_Rev':'sum', 'CL_EB':'sum', 'IH_H53':'sum', 'IH_H55':'sum', 'IH_H51':'sum', 'CL_H53':'sum', 'CL_H55':'sum', 'CL_H51':'sum', 'Headcount':'max', 'Op_Mktg':'sum', 'Op_Indeed':'sum', 'Op_EMR':'sum', 'Op_IT':'sum', 'Op_AI':'sum', 'Op_Billing':'sum', 'Op_Acct':'sum', 'Op_Leadtrap':'sum', 'Op_ATS':'sum', 'Op_Legal':'sum', 'Op_Hardware':'sum', 'Rent':'sum'}
    board = df.groupby(g_map[view_type]).agg(aggs).reset_index()
    if view_type == "Monthly": board['Period'] = board['Month'].apply(lambda x: f"Month {x}")
    elif view_type == "Quarterly": board['Period'] = board.apply(lambda x: f"Y{int(x['Year'])} Q{int(x['Quarter'])}", axis=1)
    else: board['Period'] = board['Year'].apply(lambda x: f"Year {x}")
    board['Disp_Cases'], board['Disp_Rev'], board['Disp_EB'] = (board['IH_Cases'] + board['CL_Cases'] if is_total else board[f'{prefix}_Cases']), (board['Total_Rev'] if is_total else board[f'{prefix}_Rev']), (board['Total_EB'] if is_total else board[f'{prefix}_EB'])
    board['Margin %'] = (board['Disp_EB'] / board['Disp_Rev'] * 100).fillna(0)
    return board

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(["🌎 Consolidated", "🏠 In-Home", "🏢 Clinic", "📋 Personnel", "⚙️ Expenses", "📝 Investor Docs"])

with t6:
    st.subheader("Investor Package Generation")
    
    st.markdown("### 📥 Financial Export")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Simplified clean table for export
        export_v = get_view("", is_total=True)[['Period', 'Disp_Cases', 'Disp_Rev', 'Disp_EB', 'Margin %']]
        export_v.columns = ['Period', 'Active Cases', 'Total Revenue', 'Total EBITDA', 'Margin %']
        export_v.to_excel(writer, sheet_name='5-Year Executive P&L', index=False)
        st.session_state.manual_hires.to_excel(writer, sheet_name='Hiring Roadmap', index=False)
    st.download_button(label="Download Investor Summary Table (Excel)", data=output.getvalue(), file_name="Strides_ABA_Executive_Summary.xlsx", mime="application/vnd.ms-excel")

    st.markdown("### 📝 Business Plan Draft")
    plan_text = f"EXECUTIVE SUMMARY: STRIDES ABA\n- Acquired Cases: {ih_start}\n- $500k Milestone: {find_m(500000)}\n- $1M Milestone: {find_m(1000000)}\n- Year 5 Exit EBITDA: ${y5_ebitda:,.0f}"
    st.text_area("Copy into Word:", value=plan_text, height=200)

with t5:
    st.subheader("Overhead & Operational Expense Manager")
    st.info("Edit your non-payroll monthly expenses below.")
    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state.overhead_budget['Marketing_Monthly'] = st.number_input("Marketing Spend ($/mo)", value=st.session_state.overhead_budget['Marketing_Monthly'])
        st.session_state.overhead_budget['Indeed_Monthly'] = st.number_input("Indeed Ads ($/mo)", value=st.session_state.overhead_budget['Indeed_Monthly'])
        st.session_state.overhead_budget['EMR_Per_HC'] = st.number_input("EMR Cost ($/staff member)", value=st.session_state.overhead_budget['EMR_Per_HC'])
        st.session_state.overhead_budget['IT_Per_HC'] = st.number_input("IT & Email ($/staff member)", value=st.session_state.overhead_budget['IT_Per_HC'])
    with col_b:
        st.session_state.overhead_budget['AI_Notes_Per_30_Cases'] = st.number_input("AI Notechecker ($/30 cases)", value=st.session_state.overhead_budget['AI_Notes_Per_30_Cases'])
        st.session_state.overhead_budget['Billing_Pct_Revenue'] = st.slider("Billing Fee (% Revenue)", 0.0, 0.10, 0.05, 0.01)
        st.session_state.overhead_budget['CFO_Salary'] = st.number_input("CFO Salary ($/yr)", value=st.session_state.overhead_budget['CFO_Salary'])
    if st.button("🚀 Apply Expense Changes"):
        st.rerun()

with t4:
    st.subheader("Hiring Roadmap Manager")
    with st.form("h_shield"):
        edited = st.data_editor(st.session_state.manual_hires, num_rows="dynamic", use_container_width=True)
        if st.form_submit_button("🚀 Sync Roadmap"):
            st.session_state.manual_hires = edited
            st.rerun()

def render_audit(view_df, prefix, is_total=False):
    st.markdown("---")
    drill = st.selectbox(f"Select Period to Audit ({prefix}):", view_df['Period'].tolist(), key=f"d_{prefix}")
    a = view_df[view_df['Period'] == drill].iloc[0]
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("<div class='audit-card'><b>💰 Overhead Audit</b>", unsafe_allow_html=True)
        overhead = pd.DataFrame([{"Item": "Marketing/Indeed", "Cost": a['Op_Mktg']+a['Op_Indeed']}, {"Item": "Tech Stack (EMR/IT/AI)", "Cost": a['Op_EMR']+a['Op_IT']+a['Op_AI']}, {"Item": "Finance (Billing/Acct)", "Cost": a['Op_Billing']+a['Op_Acct']}, {"Item": "Rent", "Cost": a['Rent']}])
        st.table(overhead.set_index('Item').style.format(precision=0, thousands=","))
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='audit-card'><b>🏛️ Personnel & P&L</b>", unsafe_allow_html=True)
        st.write(f"EBITDA: ${a['Disp_EB']:,.0f} | Margin: {a['Margin %']:.1f}%")
        if not is_total:
            m_list = [a['Month']] if view_type == "Monthly" else df[df['Year'] == a['Year']]['Month'].tolist()
            staff = []
            for m in m_list: staff.extend(df[df['Month'] == m].iloc[0][f'{prefix}_Staff'])
            if staff:
                s_sum = pd.DataFrame(staff).groupby("Role")['Cost'].sum().reset_index()
                for _, row in s_sum.iterrows(): st.write(f"- {row['Role']}: ${row['Cost']:,.0f}")
        st.markdown("</div>", unsafe_allow_html=True)

with t1:
    v = get_view("", is_total=True)
    st.markdown("<div class='division-header'><h3>Total Enterprise Summary</h3></div>", unsafe_allow_html=True)
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
