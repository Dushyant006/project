import streamlit as st
import pyodbc
import pandas as pd
import plotly.express as px

# 1. Page Layout Configuration
st.set_page_config(page_title="Cloud Cost Portal (SSMS)", page_icon="☁️", layout="wide")

# 2. Database Connection Helper 
def get_ssms_connection():
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"  
        "DATABASE=CloudDB;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


# --- SIDEBAR: INTERACTIVE DATA CONTROLS ---
st.sidebar.title("📥 Data Management Panel")

# 📊 1st Feature: Upload CSV Button (Fully Automated)
st.sidebar.header("1. Upload New Data")
uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    # Create a unique fingerprint for the file to prevent infinite upload loops
    file_fingerprint = f"{uploaded_file.name}_{uploaded_file.size}"
    
    # If this file hasn't been uploaded to SQL yet, process it automatically
    if st.session_state.get("last_processed_file") != file_fingerprint:
        try:
            user_df = pd.read_csv(uploaded_file)
            
            # Clean columns to ensure perfect matching
            user_df.columns = user_df.columns.str.strip().str.lower()
            required_cols = ['server_id', 'department', 'cpu_utilization', 'monthly_cost', 'status']
            
            if all(col in user_df.columns for col in required_cols):
                conn = get_ssms_connection()
                cursor = conn.cursor()
                
                # Upsert Query for SQL Server
                upsert_query = """
                    MERGE INTO server_metrics AS target
                    USING (SELECT ?, ?, ?, ?, ?) AS source (server_id, department, cpu_utilization, monthly_cost, status)
                    ON (target.server_id = source.server_id)
                    WHEN MATCHED THEN
                        UPDATE SET department = source.department, 
                                   cpu_utilization = source.cpu_utilization, 
                                   monthly_cost = source.monthly_cost, 
                                   status = source.status
                    WHEN NOT MATCHED THEN
                        INSERT (server_id, department, cpu_utilization, monthly_cost, status)
                        VALUES (source.server_id, source.department, source.cpu_utilization, source.monthly_cost, source.status);
                """
                
                for _, row in user_df.iterrows():
                    cursor.execute(upsert_query, 
                                   str(row['server_id']), 
                                   str(row['department']), 
                                   float(row['cpu_utilization']), 
                                   float(row['monthly_cost']), 
                                   str(row['status']))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                # Save status in memory and trigger an automatic data reload
                st.session_state["last_processed_file"] = file_fingerprint
                st.rerun()
                
            else:
                st.sidebar.error(f" Column mismatch! CSV needs exactly: {required_cols}")
        except Exception as e:
            st.sidebar.error(f"Error reading file: {e}")
    else:
        # Show success text quietly without blocking the charts
        st.sidebar.success(" Success")

# Reset token if file is cleared out
if uploaded_file is None and "last_processed_file" in st.session_state:
    del st.session_state["last_processed_file"]

# ✏️ 2nd Feature: Edit Data (Add or Update Records Manually)
st.sidebar.markdown("---")
st.sidebar.header("2. Edit Records")

with st.sidebar.expander("➕ Add / Update a Server"):
    with st.form("add_form", clear_on_submit=True):
        srv_id = st.text_input("Server ID (e.g. SRV-999)").strip()
        dept = st.selectbox("Department", ["Operations", "Data Science", "Finance", "Engineering", "Marketing", "Product Management", "Human Resources"])
        cpu = st.number_input("CPU Utilization (%)", min_value=0.0, max_value=100.0, step=0.1)
        cost = st.number_input("Monthly Cost ($)", min_value=0.0, step=10.0)
        status = st.selectbox("Status", ["Active", "Idle", "Maintenance"])
        
        submit_btn = st.form_submit_button("Save to SQL Database")
        
        if submit_btn:
            if srv_id:
                try:
                    conn = get_ssms_connection()
                    cursor = conn.cursor()
                    manual_query = """
                        MERGE server_metrics AS target
                        USING (SELECT ?, ?, ?, ?, ?) AS source (server_id, department, cpu_utilization, monthly_cost, status)
                        ON (target.server_id = source.server_id)
                        WHEN MATCHED THEN
                            UPDATE SET department = source.department, cpu_utilization = source.cpu_utilization, monthly_cost = source.monthly_cost, status = source.status
                        WHEN NOT MATCHED THEN
                            INSERT (server_id, department, cpu_utilization, monthly_cost, status) VALUES (source.server_id, source.department, source.cpu_utilization, source.monthly_cost, source.status);
                    """
                    cursor.execute(manual_query, srv_id, dept, cpu, cost, status)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.sidebar.success(f" Saved row {srv_id} to SSMS!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"SQL Error: {e}")
            else:
                st.sidebar.error("Server ID is required!")


# 🗑️ 3rd Feature: Delete CSV Data (Wipe Everything to start fresh)
st.sidebar.markdown("---")
st.sidebar.header("3. Danger Zone")

if st.sidebar.button(" Clear Entire SQL Database"):
    try:
        conn = get_ssms_connection()
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE server_metrics")
        conn.commit()
        cursor.close()
        conn.close()
        
        # Clear upload flags out of state memory
        if "last_processed_file" in st.session_state:
            del st.session_state["last_processed_file"]
            
        st.sidebar.warning(" Database fully cleared! Ready for a fresh CSV.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error: {e}")


# --- MAIN VIEWPORT: FETCH DATA & SHOW DASHBOARD AUTOMATICALLY ---
st.title("☁️ Cloud Infrastructure FinOps Portal")
st.markdown("### Powered by Microsoft SQL Server (SSMS) & Python")

try:
    # Pull data right out of your local database
    conn = get_ssms_connection()
    query = "SELECT server_id, department, cpu_utilization, monthly_cost, status FROM server_metrics"
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        st.info("👋 Your SQL Database table is currently empty! Drop a CSV file into the sidebar to analyze data automatically.")
    else:
        # Math calculations executed instantly
        total_servers = len(df)
        total_cost = df['monthly_cost'].sum()
        
        waste_df = df[df['status'] == 'Idle']
        total_waste = waste_df['monthly_cost'].sum()
        avg_cpu = df['cpu_utilization'].mean()

        # Display Dynamic Metric Cards
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Cloud Resources", f"{total_servers}")
        col2.metric("Total Monthly Spend", f"${total_cost:,.2f}")
        col3.metric("Identified Idle Waste", f"${total_waste:,.2f}", delta="-Potential Savings", delta_color="inverse")
        col4.metric("Average Resource CPU", f"{avg_cpu:.1f}%")

        # Render Data Visualization Charts
        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("🏢 Infrastructure Cost Distribution by Department")
            dept_spend = df.groupby('department')['monthly_cost'].sum().reset_index()
            fig_pie = px.pie(dept_spend, values='monthly_cost', names='department', hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Tealgrn)
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            st.subheader("Resource Metric Analysis (CPU vs Monthly Cost)")
            fig_scatter = px.scatter(df, x='cpu_utilization', y='monthly_cost', color='status',
                                     hover_data=['server_id'],
                                     labels={'cpu_utilization': 'CPU Utilization (%)', 'monthly_cost': 'Monthly Cost ($)'},
                                     color_discrete_map={"Active": "#2ecc71", "Idle": "#e74c3c", "Maintenance": "#f39c12"})
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Interactive Row Remover inside the main view table
        st.markdown("---")
        st.subheader("🔍 Live Database Table View & Row Removal")
        
        server_list = df['server_id'].tolist()
        selected_server_to_drop = st.selectbox("Select a particular Server ID to remove permanently from SQL:", ["-- Select Server --"] + server_list)
        
        if selected_server_to_drop != "-- Select Server --":
            if st.button(f"❌ Delete Server {selected_server_to_drop}"):
                try:
                    conn = get_ssms_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM server_metrics WHERE server_id = ?", (selected_server_to_drop,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"Removed {selected_server_to_drop} from the database backend successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete: {e}")

        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"❌ Connection or table query error on SQL Server instance. Error: {e}")
    #to run (python -m streamlit run app.py)