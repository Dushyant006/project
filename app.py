import streamlit as st
import pyodbc
import pandas as pd
import plotly.express as px

# 1. Page Layout Styling
st.set_page_config(page_title="Cloud Portal", page_icon="☁️", layout="wide")

# 2. Database Connection Helper
def get_ssms_connection():
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"  
        "DATABASE=CloudDB;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

# Helper function to auto-create and fetch Lookup IDs across dimension tables
def get_or_create_lookup(cursor, table, col_name, val):
    if table == "departments":
        id_col = "dept_id"
    elif table == "server_status":
        id_col = "status_id"
    else:
        id_col = "region_id"
        
    cursor.execute(f"SELECT {id_col} FROM {table} WHERE {col_name} = ?", (val,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute(f"INSERT INTO {table} ({col_name}) VALUES (?)", (val,))
        cursor.execute("SELECT @@IDENTITY")
        return cursor.fetchone()[0]

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.title("📥 Data Management Panel")

# 📊 CSV Bulk Uploader
st.sidebar.header("1. Bulk Upload (CSV)")
uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    file_fingerprint = f"{uploaded_file.name}_{uploaded_file.size}"
    
    if st.session_state.get("last_processed_file") != file_fingerprint:
        try:
            user_df = pd.read_csv(uploaded_file)
            user_df.columns = user_df.columns.str.strip().str.lower()
            
            if 'status' not in user_df.columns:
                status_candidates = [c for c in user_df.columns if 'status' in c]
                user_df['status'] = user_df[status_candidates[0]] if status_candidates else 'Active'
            
            if 'region' not in user_df.columns:
                import random
                user_df['region'] = [random.choice(['us-east-1', 'us-west-2', 'eu-central-1', 'ap-south-1']) for _ in range(len(user_df))]
                
            required_cols = ['server_id', 'department', 'cpu_utilization', 'monthly_cost', 'status', 'region']
            
            if all(col in user_df.columns for col in required_cols):
                conn = get_ssms_connection()
                cursor = conn.cursor()
                
                for _, row in user_df.iterrows():
                    d_id = get_or_create_lookup(cursor, "departments", "department_name", str(row['department']).strip())
                    s_id = get_or_create_lookup(cursor, "server_status", "status_name", str(row['status']).strip())
                    r_id = get_or_create_lookup(cursor, "cloud_regions", "region_name", str(row['region']).strip())
                    
                    cursor.execute("SELECT server_id FROM server_metrics WHERE server_id = ?", (str(row['server_id']),))
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE server_metrics 
                            SET dept_id = ?, status_id = ?, region_id = ?, cpu_utilization = ?, monthly_cost = ?
                            WHERE server_id = ?
                        """, (d_id, s_id, r_id, float(row['cpu_utilization']), float(row['monthly_cost']), str(row['server_id'])))
                    else:
                        cursor.execute("""
                            INSERT INTO server_metrics (server_id, dept_id, status_id, region_id, cpu_utilization, monthly_cost)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (str(row['server_id']), d_id, s_id, r_id, float(row['cpu_utilization']), float(row['monthly_cost'])))
                
                conn.commit()
                cursor.close()
                conn.close()
                st.session_state["last_processed_file"] = file_fingerprint
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error bulk uploading: {e}")
else:
    if "last_processed_file" in st.session_state:
        del st.session_state["last_processed_file"]

# 🗑️ Danger Zone
st.sidebar.markdown("---")
st.sidebar.header("2. Reset System")
if st.sidebar.button("🧹 Clear data "):
    try:
        conn = get_ssms_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM server_metrics")
        cursor.execute("DELETE FROM departments")
        cursor.execute("DELETE FROM server_status")
        cursor.execute("DELETE FROM cloud_regions")
        conn.commit()
        cursor.close()
        conn.close()
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# --- MAIN DASHBOARD LAYER ---
st.title("☁️ Cloud Infrastructure FinOps Portal")
st.markdown("### Powered by Advanced Relational SQL Database & Live CRUD Engine")

try:
    conn = get_ssms_connection()
    join_query = """
        SELECT m.server_id, d.department_name AS department, r.region_name AS region, m.cpu_utilization, m.monthly_cost, s.status_name AS status
        FROM server_metrics m
        INNER JOIN departments d ON m.dept_id = d.dept_id
        INNER JOIN server_status s ON m.status_id = s.status_id
        INNER JOIN cloud_regions r ON m.region_id = r.region_id
    """
    df = pd.read_sql(join_query, conn)
    conn.close()

    if df.empty:
        st.info("👋 Database is blank. Drop your CSV file")
    else:
        # Dashboard Calculations
        total_servers = len(df)
        total_cost = df['monthly_cost'].sum()
        total_waste = df[df['status'] == 'Idle']['monthly_cost'].sum()
        avg_cpu = df['cpu_utilization'].mean()

        # KPI Badges
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Resources", f"{total_servers}")
        col2.metric("Total Cost Spend", f"${total_cost:,.2f}")
        col3.metric("Identified Idle Waste", f"${total_waste:,.2f}", delta="-Potential Savings", delta_color="inverse")
        col4.metric("Average CPU Usage", f"{avg_cpu:.1f}%")

        # Interactive Analytics Charts
        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("🏢 Cost Allocation by Department")
            dept_spend = df.groupby('department')['monthly_cost'].sum().reset_index()
            fig_pie = px.pie(dept_spend, values='monthly_cost', names='department', hole=0.4, color_discrete_sequence=px.colors.sequential.Tealgrn)
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            st.subheader("🌐 Cost Metrics by Cloud Region")
            region_spend = df.groupby(['region', 'status'])['monthly_cost'].sum().reset_index()
            fig_bar = px.bar(region_spend, x='region', y='monthly_cost', color='status', barmode='group', color_discrete_map={"Active": "#2ecc71", "Idle": "#e74c3c", "Maintenance": "#f39c12"})
            st.plotly_chart(fig_bar, use_container_width=True)

    # --- ADVANCED CRUD ENGINE SECTION ---
    st.markdown("---")
    st.header("⚙️ Live Database changes")
    
    tab1, tab2, tab3 = st.tabs(["➕ Add New Server Record", "✏️ Edit / Update Existing Data", "❌ Delete Specific Server"])
    
    # ➕ TAB 1: ADD DATA
    with tab1:
        st.subheader("Insert a Brand New Server Instance")
        with st.form("add_form", clear_on_submit=True):
            new_id = st.text_input("Enter Unique Server ID (e.input: SRV-999):").strip()
            new_dept = st.selectbox("Assign Department:", ["Finance", "Engineering", "Operations", "Marketing", "Sales", "HR"])
            new_region = st.selectbox("Select Cloud Region Location:", ["us-east-1", "us-west-2", "eu-central-1", "ap-south-1"])
            new_cpu = st.number_input("Current CPU Utilization (%)", min_value=0.0, max_value=100.0, value=50.0)
            new_cost = st.number_input("Monthly Operations Cost ($)", min_value=0.0, value=250.0)
            new_status = st.selectbox("Initial Server Status:", ["Active", "Idle", "Maintenance"])
            
            submit_add = st.form_submit_button("Save Server to SQL Server Database")
            
            if submit_add:
                if not new_id:
                    st.error("❌ Server ID cannot be left blank!")
                elif not df.empty and new_id in df['server_id'].values:
                    st.error(f"❌ Server ID '{new_id}' already exists in the database! Use the Edit tab to modify it.")
                else:
                    try:
                        conn = get_ssms_connection()
                        cursor = conn.cursor()
                        d_id = get_or_create_lookup(cursor, "departments", "department_name", new_dept)
                        s_id = get_or_create_lookup(cursor, "server_status", "status_name", new_status)
                        r_id = get_or_create_lookup(cursor, "cloud_regions", "region_name", new_region)
                        
                        cursor.execute("""
                            INSERT INTO server_metrics (server_id, dept_id, status_id, region_id, cpu_utilization, monthly_cost)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (new_id, d_id, s_id, r_id, new_cpu, new_cost))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"🎉 Successfully inserted new record: Server {new_id} added to Fact Table!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

    # ✏️ TAB 2: EDIT / UPDATE DATA
    with tab2:
        st.subheader("Modify Particular Existing Fields")
        if df.empty:
            st.warning("No data available to edit. Please upload a file first.")
        else:
            selected_edit_id = st.selectbox("Select the Server ID you want to modify:", ["-- Select Server --"] + df['server_id'].tolist())
            
            if selected_edit_id != "-- Select Server --":
                # Pre-fetch existing row details to auto-populate fields for user editing convenience
                current_row = df[df['server_id'] == selected_edit_id].iloc[0]
                
                with st.form("edit_form"):
                    st.info(f"Editing Metrics for Instance: **{selected_edit_id}**")
                    
                    # Departments mapping indices logic
                    dept_list = ["Finance", "Engineering", "Operations", "Marketing", "Sales", "HR"]
                    curr_dept_idx = dept_list.index(current_row['department']) if current_row['department'] in dept_list else 0
                    edit_dept = st.selectbox("Update Department:", dept_list, index=curr_dept_idx)
                    
                    # Regions mapping logic
                    reg_list = ["us-east-1", "us-west-2", "eu-central-1", "ap-south-1"]
                    curr_reg_idx = reg_list.index(current_row['region']) if current_row['region'] in reg_list else 0
                    edit_region = st.selectbox("Update Cloud Region Location:", reg_list, index=curr_reg_idx)
                    
                    edit_cpu = st.number_input("Modify CPU Utilization (%)", min_value=0.0, max_value=100.0, value=float(current_row['cpu_utilization']))
                    edit_cost = st.number_input("Modify Monthly Cost ($)", min_value=0.0, value=float(current_row['monthly_cost']))
                    
                    # Status mapping logic
                    stat_list = ["Active", "Idle", "Maintenance"]
                    curr_stat_idx = stat_list.index(current_row['status']) if current_row['status'] in stat_list else 0
                    edit_status = st.selectbox("Update Server Status State:", stat_list, index=curr_stat_idx)
                    
                    submit_edit = st.form_submit_button("Apply Changes to SQL Server")
                    
                    if submit_edit:
                        try:
                            conn = get_ssms_connection()
                            cursor = conn.cursor()
                            d_id = get_or_create_lookup(cursor, "departments", "department_name", edit_dept)
                            s_id = get_or_create_lookup(cursor, "server_status", "status_name", edit_status)
                            r_id = get_or_create_lookup(cursor, "cloud_regions", "region_name", edit_region)
                            
                            cursor.execute("""
                                UPDATE server_metrics 
                                SET dept_id = ?, status_id = ?, region_id = ?, cpu_utilization = ?, monthly_cost = ?
                                WHERE server_id = ?
                            """, (d_id, s_id, r_id, edit_cpu, edit_cost, selected_edit_id))
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success(f"✨ Row update query executed successfully for: Server {selected_edit_id}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error applying updates: {e}")

    # ❌ TAB 3: DELETE DATA
    with tab3:
        st.subheader("Permanent Row Removal Panel")
        if df.empty:
            st.warning("No data available to delete.")
        else:
            selected_drop_id = st.selectbox("Select particular Server ID to remove permanently from Fact Table:", ["-- Select Server --"] + df['server_id'].tolist())
            
            if selected_drop_id != "-- Select Server --":
                st.warning(f"⚠️ Warning: This will permanently delete Server **{selected_drop_id}** from the server_metrics table inside SQL Server database.")
                if st.button(f"💥 Confirm Delete: Drop {selected_drop_id} Now"):
                    try:
                        conn = get_ssms_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM server_metrics WHERE server_id = ?", (selected_drop_id,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"❌ Server record {selected_drop_id} successfully deleted from SQL backend!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error dropping record: {e}")

    # Display the final unified dataframe grid at the very bottom
    st.markdown("---")
    st.subheader("📋 Active Database State - Fact View Grid (`server_metrics`) ")
    if not df.empty:
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"❌error occurred. Logs: {e}")
    #to run (python -m streamlit run app.py)