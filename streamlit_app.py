import streamlit as st
import sqlite3
import uuid
import datetime

# ---------------------------
# 1. DATABASE SETUP & HELPERS
# ---------------------------
def init_db():
    """Create tables if not already existing."""
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()

    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Contracts table
    c.execute("""
    CREATE TABLE IF NOT EXISTS contracts (
        contract_id TEXT PRIMARY KEY,
        vendor_name TEXT,
        description TEXT,
        start_date TEXT,
        end_date TEXT,
        budget REAL,
        status TEXT  -- e.g. Draft, Pending Approval, Active, Rejected
    )
    """)

    # Approvals table - one row per contract per approver
    c.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id TEXT PRIMARY KEY,
        contract_id TEXT,
        approver_id TEXT,
        approval_status TEXT,  -- Pending, Approved, Rejected
        timestamp TEXT,
        FOREIGN KEY(contract_id) REFERENCES contracts(contract_id),
        FOREIGN KEY(approver_id) REFERENCES users(user_id)
    )
    """)

    # Service Reports
    c.execute("""
    CREATE TABLE IF NOT EXISTS service_reports (
        report_id TEXT PRIMARY KEY,
        contract_id TEXT,
        service_date TEXT,
        work_performed TEXT,
        parts_cost REAL,
        labor_hours REAL,
        FOREIGN KEY(contract_id) REFERENCES contracts(contract_id)
    )
    """)

    # Invoices
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id TEXT PRIMARY KEY,
        contract_id TEXT,
        amount REAL,
        invoice_date TEXT,
        payment_status TEXT,  -- Pending, Paid, Overdue, etc.
        FOREIGN KEY(contract_id) REFERENCES contracts(contract_id)
    )
    """)

    conn.commit()
    conn.close()

def seed_users():
    """
    Create a few demo users with different roles, if they don't already exist.
    In production, always store hashed passwords!
    """
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()

    # Attempt to create some demo users
    demo_users = [
        ("manager_user", "manager_pass", "manager"),     # Contract Manager
        ("approver_user1", "approver_pass1", "approver"), # Approver (Dept. Head)
        ("approver_user2", "approver_pass2", "approver"), # Approver (Finance Controller)
        ("approver_user3", "approver_pass3", "approver"), # Approver (Legal Officer)
        ("finance_user", "finance_pass", "finance")      # Finance role for invoicing
    ]
    for username, password, role in demo_users:
        # Check if user exists
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            user_id = str(uuid.uuid4())
            c.execute("INSERT INTO users (user_id, username, password, role) VALUES (?, ?, ?, ?)",
                      (user_id, username, password, role))
    conn.commit()
    conn.close()

def get_user(username, password):
    """Return user record if username/password match, else None."""
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user  # (user_id, username, password, role)

# Helper to get user role from user_id
def get_user_role(user_id):
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# -----------
# 2. MAIN APP
# -----------
def main():
    st.set_page_config(page_title="O&M Contract Management", layout="wide")
    init_db()
    seed_users()

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        login_page()
    else:
        # We have a logged-in user
        role = get_user_role(st.session_state.user_id)
        app_layout(role)

def login_page():
    st.title("O&M Contract Management - Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_record = get_user(username, password)
        if user_record:
            # user_record = (user_id, username, password, role)
            st.session_state.user_id = user_record[0]
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def app_layout(role):
    st.sidebar.title("Navigation")
    menu = ["Home"]

    # Common pages for all roles
    menu.append("Service Reports")

    # Show Contracts menu for manager
    if role == "manager":
        menu.append("Contracts")

    # Approvers see an "Approvals" page
    if role == "approver":
        menu.append("Approvals")

    # Finance sees an "Invoices" page
    if role == "finance":
        menu.append("Invoices")

    menu.append("Logout")
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        home_page(role)
    elif choice == "Contracts" and role == "manager":
        manage_contracts()
    elif choice == "Approvals" and role == "approver":
        review_contracts()  # Approvers see contracts pending approval
    elif choice == "Service Reports":
        manage_service_reports()
    elif choice == "Invoices" and role == "finance":
        manage_invoices()
    elif choice == "Logout":
        st.session_state.user_id = None
        st.experimental_rerun()

def home_page(role):
    st.title("Welcome to the O&M Contract Management Dashboard")
    st.write(f"You are logged in as: **{role}**")

    # Optionally display some quick stats
    # E.g., number of active contracts, pending approvals, etc.
    # For demonstration, we'll keep it simple.
    st.info("Use the sidebar to navigate through the application.")

# -------------------------
# 3. CONTRACTS (Manager)
# -------------------------
def manage_contracts():
    st.title("Manage Contracts (Manager Only)")

    # For demonstration, we’ll show existing contracts in a table
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()

    # Display existing contracts
    c.execute("SELECT contract_id, vendor_name, status, budget FROM contracts")
    rows = c.fetchall()
    conn.close()

    st.subheader("Existing Contracts")
    if rows:
        for row in rows:
            contract_id, vendor_name, status, budget = row
            st.write(f"**Contract ID**: {contract_id}")
            st.write(f"**Vendor**: {vendor_name}")
            st.write(f"**Budget**: {budget}")
            st.write(f"**Status**: {status}")
            # If Draft, allow submission
            if status == "Draft":
                if st.button(f"Submit for Approval - {contract_id}", key=f"submit_{contract_id}"):
                    submit_contract_for_approval(contract_id)
                    st.success("Submitted for approval.")
                    st.experimental_rerun()
            st.write("---")
    else:
        st.info("No contracts found.")

    st.subheader("Add New Contract")
    with st.form("new_contract_form", clear_on_submit=True):
        vendor_name = st.text_input("Vendor/Subcontractor Name")
        description = st.text_area("Description")
        start_date = st.date_input("Start Date", datetime.date.today())
        end_date = st.date_input("End Date", datetime.date.today())
        budget = st.number_input("Budget", min_value=0.0, step=1000.0)
        submitted = st.form_submit_button("Create Contract")

        if submitted:
            create_contract(vendor_name, description, start_date, end_date, budget)
            st.success("New contract created.")
            st.experimental_rerun()

def create_contract(vendor, desc, start_date, end_date, budget):
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    contract_id = str(uuid.uuid4())
    c.execute("""
        INSERT INTO contracts (contract_id, vendor_name, description, start_date, end_date, budget, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (contract_id, vendor, desc, str(start_date), str(end_date), budget, "Draft"))
    conn.commit()
    conn.close()

def submit_contract_for_approval(contract_id):
    # Update status to Pending Approval
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("UPDATE contracts SET status=? WHERE contract_id=?", ("Pending Approval", contract_id))
    conn.commit()

    # Create approvals for each of the 3 designated approvers
    # For simplicity, let's just find all users with role='approver'
    c.execute("SELECT user_id FROM users WHERE role='approver'")
    approvers = c.fetchall()
    for (approver_id,) in approvers:
        approval_id = str(uuid.uuid4())
        c.execute("""
            INSERT INTO approvals (approval_id, contract_id, approver_id, approval_status, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (approval_id, contract_id, approver_id, "Pending", str(datetime.datetime.now())))
    conn.commit()
    conn.close()

# -------------------------
# 4. APPROVALS (Approvers)
# -------------------------
def review_contracts():
    st.title("Review Contracts (Approver)")

    # Show only contracts that are "Pending Approval" and specifically "Pending" for this approver
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()

    # Current user
    approver_id = st.session_state.user_id

    c.execute("""
        SELECT c.contract_id, c.vendor_name, c.description, c.budget, a.approval_id, a.approval_status
        FROM contracts c
        JOIN approvals a ON c.contract_id = a.contract_id
        WHERE a.approver_id=? AND a.approval_status='Pending'
    """, (approver_id,))
    rows = c.fetchall()
    conn.close()

    if rows:
        for row in rows:
            contract_id, vendor_name, description, budget, approval_id, approval_status = row
            st.write(f"**Contract ID**: {contract_id}")
            st.write(f"**Vendor**: {vendor_name}")
            st.write(f"**Budget**: {budget}")
            st.write(f"**Description**: {description}")
            col1, col2 = st.columns(2)
            if col1.button(f"Approve {contract_id}", key=f"approve_{contract_id}"):
                approve_contract(approval_id, contract_id)
                st.experimental_rerun()
            if col2.button(f"Reject {contract_id}", key=f"reject_{contract_id}"):
                reject_contract(approval_id, contract_id)
                st.experimental_rerun()
            st.write("---")
    else:
        st.info("No contracts pending your approval.")

def approve_contract(approval_id, contract_id):
    # Approve the individual's record
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("UPDATE approvals SET approval_status=? WHERE approval_id=?", ("Approved", approval_id))
    conn.commit()

    # Check if ALL approvers have approved
    c.execute("""
        SELECT COUNT(*) 
        FROM approvals
        WHERE contract_id=? AND approval_status='Approved'
    """, (contract_id,))
    approved_count = c.fetchone()[0]

    # How many total approvers?
    c.execute("""
        SELECT COUNT(*) 
        FROM approvals
        WHERE contract_id=?
    """, (contract_id,))
    total_approvers = c.fetchone()[0]

    if approved_count == total_approvers:
        # Everyone approved, set contract to Active
        c.execute("UPDATE contracts SET status='Active' WHERE contract_id=?", (contract_id,))
    conn.commit()
    conn.close()

def reject_contract(approval_id, contract_id):
    # Reject the individual's record
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("UPDATE approvals SET approval_status=? WHERE approval_id=?", ("Rejected", approval_id))
    # Also set the contract status to Rejected
    c.execute("UPDATE contracts SET status='Rejected' WHERE contract_id=?", (contract_id,))
    conn.commit()
    conn.close()

# ---------------------------
# 5. SERVICE REPORTS (All)
# ---------------------------
def manage_service_reports():
    st.title("Service Reports")

    # Show a list of existing service reports
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("""
        SELECT report_id, contract_id, service_date, work_performed, parts_cost, labor_hours
        FROM service_reports
    """)
    rows = c.fetchall()
    conn.close()

    st.subheader("Existing Service Reports")
    if rows:
        for r in rows:
            report_id, contract_id, service_date, work_performed, parts_cost, labor_hours = r
            st.write(f"**Report ID**: {report_id}")
            st.write(f"**Contract ID**: {contract_id}")
            st.write(f"**Date**: {service_date}")
            st.write(f"**Work Performed**: {work_performed}")
            st.write(f"**Parts Cost**: {parts_cost}, **Labor Hours**: {labor_hours}")
            st.write("---")
    else:
        st.info("No service reports found.")

    st.subheader("Submit New Service Report")
    with st.form("new_report_form", clear_on_submit=True):
        contract_id = st.text_input("Contract ID")
        service_date = st.date_input("Service Date", datetime.date.today())
        work_performed = st.text_area("Work Performed")
        parts_cost = st.number_input("Parts Cost", min_value=0.0, step=1.0)
        labor_hours = st.number_input("Labor Hours", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Submit Report")

        if submitted:
            report_id = str(uuid.uuid4())
            conn = sqlite3.connect("contracts.db")
            c = conn.cursor()
            c.execute("""
                INSERT INTO service_reports (report_id, contract_id, service_date, work_performed, parts_cost, labor_hours)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (report_id, contract_id, str(service_date), work_performed, parts_cost, labor_hours))
            conn.commit()
            conn.close()
            st.success("Service report submitted.")
            st.experimental_rerun()

# ------------------------
# 6. INVOICES (Finance)
# ------------------------
def manage_invoices():
    st.title("Invoices (Finance Role)")

    # Show existing invoices
    conn = sqlite3.connect("contracts.db")
    c = conn.cursor()
    c.execute("""
        SELECT invoice_id, contract_id, amount, invoice_date, payment_status
        FROM invoices
    """)
    rows = c.fetchall()

    st.subheader("Existing Invoices")
    if rows:
        for inv in rows:
            invoice_id, contract_id, amount, invoice_date, payment_status = inv
            st.write(f"**Invoice ID**: {invoice_id}")
            st.write(f"**Contract ID**: {contract_id}")
            st.write(f"**Amount**: {amount}")
            st.write(f"**Date**: {invoice_date}")
            st.write(f"**Status**: {payment_status}")

            # Mark as Paid
            if payment_status != "Paid":
                if st.button(f"Mark Paid - {invoice_id}"):
                    c.execute("UPDATE invoices SET payment_status='Paid' WHERE invoice_id=?", (invoice_id,))
                    conn.commit()
                    st.experimental_rerun()
            st.write("---")
    else:
        st.info("No invoices found.")

    st.subheader("Generate New Invoice")
    with st.form("new_invoice_form", clear_on_submit=True):
        contract_id = st.text_input("Contract ID")
        amount = st.number_input("Amount", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Generate Invoice")
        if submitted:
            invoice_id = str(uuid.uuid4())
            invoice_date = str(datetime.date.today())
            c.execute("""
                INSERT INTO invoices (invoice_id, contract_id, amount, invoice_date, payment_status)
                VALUES (?, ?, ?, ?, ?)
            """, (invoice_id, contract_id, amount, invoice_date, "Pending"))
            conn.commit()
            st.success(f"Invoice {invoice_id} generated!")
            st.experimental_rerun()

    conn.close()

# -------------
# RUN THE APP
# -------------
if __name__ == "__main__":
    main()
