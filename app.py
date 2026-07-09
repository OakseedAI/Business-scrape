import streamlit as st
import pandas as pd
import os
import urllib.parse
from scraper import run_lead_search, save_leads_to_excel, clean_company_name

DB_FILE = 'leads.xlsx'
CSS_FILE = 'style.css'

# Page configurations
st.set_page_config(
    page_title="OakSeedAI - Lead Generation & Outreach Panel",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(CSS_FILE)

# Helper function to load database
def load_db():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            # Ensure required columns are present
            required_cols = [
                'Company Name', 'City', 'Business Type', 'Phone', 'Email', 
                'Website', 'Automation Status', 'Likely Lacks Automation', 'Status', 'Drafted Email'
            ]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = "" if col != 'Likely Lacks Automation' else "Yes"
            return df
        except Exception as e:
            st.error(f"Error reading Excel database: {e}")
            return create_empty_db()
    else:
        return create_empty_db()

def create_empty_db():
    df = pd.DataFrame(columns=[
        'Company Name', 'City', 'Business Type', 'Phone', 'Email', 
        'Website', 'Automation Status', 'Likely Lacks Automation', 'Status', 'Drafted Email'
    ])
    df.to_excel(DB_FILE, index=False)
    return df

def save_db(df):
    try:
        df.to_excel(DB_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving to Excel database: {e}")
        return False

# Default Email Template Generator
def default_email_template(company_name, city, business_type, sender_name="OakSeedAI Specialist"):
    return f"""Hi there,

I hope this email finds you well.

My name is {sender_name}, and I run a small, local AI and operations agency called OakSeedAI, based right here in Raleigh.

I noticed {company_name} is doing fantastic work in {city}. As an Automations & AI Implementation Specialist, I love helping local businesses streamline their daily operations. I would love to learn more about your daily work and discuss how custom automations and Artificial Intelligence might be able to help save you time and money.

Are you open to a brief 10-minute chat sometime next week?

Best regards,

{sender_name}
OakSeedAI
Raleigh, NC"""

# Initialize session states
if 'db' not in st.session_state:
    st.session_state['db'] = load_db()

if 'selected_lead_idx' not in st.session_state:
    st.session_state['selected_lead_idx'] = 0

# App Header
st.markdown("""
<div class="main-header">
    <h1>🌱 OakSeedAI Outreach & Lead Panel</h1>
    <p>NC Local Business Lead Scraper, Automation Auditor, and Custom Email Builder</p>
</div>
""", unsafe_allow_html=True)

# Sidebar settings & Scrape options
st.sidebar.markdown("### ⚙️ Outreach & Agency Settings")
sender_name = st.sidebar.text_input("Sender Name", value="Alex", help="Your name as it appears in the drafted emails.")
custom_sig = st.sidebar.text_area("Email Signature Addendum", value="OakSeedAI\nBased out of Raleigh, NC", height=80)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧹 Database Maintenance")
if st.sidebar.button("Clear Database", type="secondary"):
    if st.sidebar.checkbox("Confirm database reset? This deletes all leads."):
        st.session_state['db'] = create_empty_db()
        st.success("Database reset successfully.")
        st.rerun()

# Sync loaded DB into session state
df = st.session_state['db']

# Setup main tabs
tab1, tab2, tab3 = st.tabs([
    "📊 Search & Dashboard", 
    "📋 Lead Directory (Spreadsheet)", 
    "✉️ Human Check & Email outreach"
])

# ================= TAB 1: Search & Dashboard =================
with tab1:
    st.markdown("### 📊 Live Performance Metrics")
    
    # KPIs calculation
    total_leads = len(df)
    leads_no_auto = len(df[df['Likely Lacks Automation'] == 'Yes'])
    contacted_leads = len(df[df['Status'] == 'Warm lead - Contacted'])
    pending_leads = len(df[df['Status'] == 'New Lead'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Leads Scraped</div>
            <div class="kpi-value">{total_leads}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #52b788;">
            <div class="kpi-title">Automation Targets (Likely None)</div>
            <div class="kpi-value">{leads_no_auto}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #0369a1;">
            <div class="kpi-title">Warm Leads Contacted</div>
            <div class="kpi-value">{contacted_leads}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #d4af37;">
            <div class="kpi-title">Pending Human Check</div>
            <div class="kpi-value">{pending_leads}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔍 Scrape for New Local Businesses in NC")
    st.markdown("Query local search engines for businesses in specific North Carolina regions. Our engine automatically checks their websites for automation tag signatures (like Calendly, HubSpot, etc.).")
    
    col_city, col_biz, col_max = st.columns([2, 2, 1])
    with col_city:
        city_input = st.text_input("NC Town / City", value="Raleigh", help="e.g. Raleigh, Durham, Cary, Apex, Wilmington, Charlotte")
    with col_biz:
        biz_input = st.text_input("Business Type", value="Plumber", help="e.g. Plumber, HVAC, Bakery, Landscaping, Florist, Roofing")
    with col_max:
        max_leads = st.number_input("Max Leads to Crawl", min_value=1, max_value=50, value=10)
        
    if st.button("🚀 Run Lead Search & Crawl", type="primary"):
        if not city_input or not biz_input:
            st.error("Please provide both a city and a business type to search.")
        else:
            with st.spinner(f"Searching DuckDuckGo and crawling websites for '{biz_input}' in '{city_input}, NC'..."):
                # Run lead search
                new_leads = run_lead_search(city_input, biz_input, max_results=max_leads)
                
                if new_leads:
                    # Pre-generate emails
                    for lead in new_leads:
                        lead['Drafted Email'] = default_email_template(
                            lead['Company Name'], 
                            lead['City'], 
                            lead['Business Type'], 
                            sender_name=sender_name
                        )
                        
                    # Save leads to spreadsheet
                    added_count = save_leads_to_excel(new_leads, DB_FILE)
                    
                    # Refresh Session State DB
                    st.session_state['db'] = load_db()
                    st.success(f"Scraping complete! Crawled {len(new_leads)} businesses. Added {added_count} new unique leads to the database.")
                    st.rerun()
                else:
                    st.warning("No new matching business websites could be found or parsed for this query.")

# ================= TAB 2: Lead Directory (Spreadsheet) =================
with tab2:
    st.markdown("### 📋 Leads Spreadsheet Database")
    st.markdown("Double-click cells below to manually fix emails, phone numbers, or update statuses, then click **'Save Grid Changes'** to persist modifications.")
    
    current_db = st.session_state['db']
    
    if current_db.empty:
        st.info("The database is currently empty. Run a scrape in the first tab to discover leads!")
    else:
        # Edit sheet directly using Streamlit data editor
        edited_df = st.data_editor(
            current_db, 
            column_config={
                "Company Name": st.column_config.TextColumn("Company Name", disabled=True),
                "City": st.column_config.TextColumn("City", disabled=True),
                "Business Type": st.column_config.TextColumn("Business Type", disabled=True),
                "Phone": st.column_config.TextColumn("Phone"),
                "Email": st.column_config.TextColumn("Email"),
                "Website": st.column_config.LinkColumn("Website"),
                "Automation Status": st.column_config.TextColumn("Automation Status", disabled=True),
                "Likely Lacks Automation": st.column_config.SelectboxColumn(
                    "Likely Lacks Automation", 
                    options=["Yes", "No"], 
                    required=True
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["New Lead", "Warm lead - Contacted", "Archived"],
                    required=True
                ),
                "Drafted Email": st.column_config.TextColumn("Drafted Email")
            },
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True
        )
        
        col_s1, col_s2 = st.columns([1, 4])
        with col_s1:
            if st.button("💾 Save Grid Changes", type="primary"):
                st.session_state['db'] = edited_df
                save_db(edited_df)
                st.success("Excel sheet database updated and saved successfully!")
                st.rerun()
                
        with col_s2:
            # Download xlsx button
            try:
                with open(DB_FILE, "rb") as file:
                    st.download_button(
                        label="📥 Download Excel Spreadsheet (.xlsx)",
                        data=file,
                        file_name="nc_leads.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except FileNotFoundError:
                pass

# ================= TAB 3: Human Check & Outreach =================
with tab3:
    st.markdown("### ✉️ Human Check & Drafting Panel")
    
    # Filter the leads that are active (New Lead status)
    active_leads_df = df[df['Status'] == 'New Lead']
    
    if active_leads_df.empty:
        st.info("🎉 Hooray! There are no pending leads in the Human Check queue. All leads are contacted or archived.")
    else:
        # Selectbox to pick a lead to review
        lead_options = [
            f"{row['Company Name']} ({row['City']} - {row['Business Type']})" 
            for idx, row in active_leads_df.iterrows()
        ]
        
        # Keep selected index bounded
        if st.session_state['selected_lead_idx'] >= len(lead_options):
            st.session_state['selected_lead_idx'] = 0
            
        selected_lead_str = st.selectbox(
            "Select Lead to Review & Edit:", 
            options=lead_options,
            index=st.session_state['selected_lead_idx']
        )
        
        # Get the actual index in the main dataframe
        selected_idx_main = None
        for idx, row in active_leads_df.iterrows():
            option_str = f"{row['Company Name']} ({row['City']} - {row['Business Type']})"
            if option_str == selected_lead_str:
                selected_idx_main = idx
                break
                
        if selected_idx_main is not None:
            lead = df.iloc[selected_idx_main]
            
            # Show lead details
            st.markdown(f"## {lead['Company Name']}")
            
            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                st.markdown(f"**🌐 Website:** [Visit Site]({lead['Website']})")
                st.markdown(f"**📍 Location:** {lead['City']}, NC")
            with col_l2:
                # Allow user to edit email and phone directly
                lead_email = st.text_input("Contact Email", value=str(lead['Email']) if pd.notna(lead['Email']) else "")
                lead_phone = st.text_input("Contact Phone", value=str(lead['Phone']) if pd.notna(lead['Phone']) else "")
            with col_l3:
                # Badge rendering based on status
                if lead['Likely Lacks Automation'] == 'Yes':
                    st.markdown("""<span class="badge badge-green">High Priority: Likely No Automations</span>""", unsafe_allow_html=True)
                else:
                    st.markdown("""<span class="badge badge-yellow">Medium Priority: Some Scripts Found</span>""", unsafe_allow_html=True)
                st.write(f"Automation audit: *{lead['Automation Status']}*")
                
            st.markdown("---")
            
            # Subject Line & Email Body Editor
            st.markdown("### ✍️ Draft Email Customization")
            
            default_subject = f"Helping {lead['Company Name']} save time and money through AI/automation"
            email_subject = st.text_input("Email Subject Line", value=default_subject)
            
            # Handle draft text loading or regeneration
            draft_content = lead['Drafted Email']
            if not draft_content or pd.isna(draft_content) or "[Your Name]" in draft_content:
                # Regenerate with current settings
                draft_content = default_email_template(
                    lead['Company Name'], 
                    lead['City'], 
                    lead['Business Type'], 
                    sender_name=sender_name
                )
                
            email_body = st.text_area("Email Body", value=draft_content, height=350)
            
            # Create a mailto URL for desktop mail client opening
            # URL encoding params
            encoded_subject = urllib.parse.quote(email_subject)
            encoded_body = urllib.parse.quote(email_body)
            mailto_link = f"mailto:{lead_email}?subject={encoded_subject}&body={encoded_body}"
            
            # Save progress callback
            def update_lead_record(new_status=None):
                # Update cells in DataFrame
                df.at[selected_idx_main, 'Email'] = lead_email
                df.at[selected_idx_main, 'Phone'] = lead_phone
                df.at[selected_idx_main, 'Drafted Email'] = email_body
                if new_status:
                    df.at[selected_idx_main, 'Status'] = new_status
                save_db(df)
                st.session_state['db'] = df
            
            col_actions1, col_actions2, col_actions3 = st.columns(3)
            
            with col_actions1:
                # Mail client launcher (Primary option)
                if lead_email:
                    st.link_button("📤 Open Email Client (mailto:)", mailto_link, type="primary")
                    st.caption("Launches your default desktop mail application with this pre-filled message.")
                else:
                    st.warning("Cannot generate mailto link without a contact email. Please enter one above.")
                    
            with col_actions2:
                # Copy draft clipboard
                st.button("📋 Copy Email Body to Clipboard")
                # Wait, Streamlit text_area natively has copy buttons in some UI layouts, 
                # but we can save changes when this is clicked.
                if st.button("💾 Save Edits (Draft Only)"):
                    update_lead_record()
                    st.success("Draft edits saved!")
                    
            with col_actions3:
                # Update status in db
                if st.button("✅ Approve & Mark Contacted"):
                    update_lead_record(new_status="Warm lead - Contacted")
                    st.success(f"Status for '{lead['Company Name']}' updated to: Warm lead - Contacted")
                    
                    # Try to advance queue to next item
                    active_cnt = len(active_leads_df)
                    if active_cnt > 1:
                        # Index is 0-indexed on the filtered df list
                        st.session_state['selected_lead_idx'] = min(st.session_state['selected_lead_idx'], active_cnt - 2)
                    else:
                        st.session_state['selected_lead_idx'] = 0
                    st.rerun()
                    
                if st.button("🗑️ Archive Lead"):
                    update_lead_record(new_status="Archived")
                    st.info(f"Lead '{lead['Company Name']}' archived.")
                    st.rerun()
