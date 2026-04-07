import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import random
import time

# ReportLab setup
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# --- DATABASE SETUP ---
DB_NAME = "exam_management.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                register_no TEXT PRIMARY KEY,
                name TEXT,
                department TEXT,
                subject TEXT,
                year INTEGER,
                hall_no INTEGER,
                seat_no INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invigilators (
                staff_id TEXT PRIMARY KEY,
                staff_name TEXT,
                assigned_hall INTEGER
            )
        """)
        conn.commit()

# --- SEATING LOGIC ---
def generate_dynamic_seating(df, h_cap, cols, start_idx=0):
    df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
    if 'sem' in df.columns:
        df = df.rename(columns={'sem': 'year'})
    df = df.dropna(subset=['register_no', 'subject']).drop_duplicates(subset=['register_no'])
    groups = {sub: list(group.to_dict('records')) for sub, group in df.groupby('subject')}
    final_layout = []

    def get_sub_at(idx):
        return final_layout[idx]['subject'] if 0 <= idx < len(final_layout) else None

    while any(groups.values()):
        curr_idx = len(final_layout)
        total_pos = start_idx + curr_idx
        left_sub = get_sub_at(curr_idx - 1) if total_pos % cols != 0 else None
        front_sub = get_sub_at(curr_idx - cols)
        available_subs = sorted([s for s in groups if groups[s]], key=lambda x: len(groups[x]), reverse=True)
        placed = False
        for sub in available_subs:
            if sub != left_sub and sub != front_sub:
                final_layout.append(groups[sub].pop(0))
                placed = True
                break
        if not placed:
            final_layout.append({'register_no': f'GAP_{total_pos+1}', 'name': 'EMPTY', 'department': '-', 'subject': 'EMPTY_GAP', 'year': 0})

    for i, entry in enumerate(final_layout):
        actual_pos = start_idx + i
        entry['seat_no'] = actual_pos + 1
        entry['hall_no'] = (actual_pos // h_cap) + 1
    return pd.DataFrame(final_layout)

# --- PDF GENERATOR ---
def generate_staff_pdf(df):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>Exam Invigilation Duty Chart</b>", styles['Title']))
    data = [["Staff ID", "Staff Name", "Assigned Hall"]]
    for _, row in df.iterrows():
        data.append([str(row['staff_id']), row['staff_name'], f"Hall {row['assigned_hall']}"])
    t = Table(data, colWidths=[100, 250, 100])
    # Purple theme for PDF
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND',(0,0),(-1,0), colors.purple), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(t); doc.build(elements); buffer.seek(0)
    return buffer

def generate_hall_pdf(df):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(name='CellStyle', fontSize=8, leading=10, alignment=1)
    
    halls = sorted(df['hall_no'].unique())
    for hall in halls:
        elements.append(Paragraph(f"<b>Hall No : {hall} Seating Chart</b>", styles['Title']))
        hall_data = df[(df['hall_no'] == hall) & (df['subject'] != 'EMPTY_GAP')]
        deps = ", ".join(sorted(hall_data['department'].unique().astype(str).tolist()))
        yrs = ", ".join(sorted([str(y) for y in hall_data['year'].unique()]))
        summary = f"<b>Departments:</b> {deps} | <b>Years:</b> {yrs}"
        elements.append(Paragraph(summary, styles['Normal']))
        elements.append(Spacer(1, 10))
        data = [["Seat", "Reg No", "Name", "Subject", "Year", "Dept"]]
        for _, row in hall_data.iterrows():
            data.append([row['seat_no'], row['register_no'], Paragraph(str(row['name']), cell_style), Paragraph(str(row['subject']), cell_style), row['year'], Paragraph(str(row['department']), cell_style)])
        t = Table(data, colWidths=[35, 75, 130, 130, 35, 80], repeatRows=1)
        # Purple theme for PDF
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
        elements.append(t); elements.append(Spacer(1, 40))
    doc.build(elements); buffer.seek(0)
    return buffer

# --- UI CONFIG ---
st.set_page_config(page_title="NexGen Exam Manager", layout="wide")
init_db()

COLLEGE_LOGO = "image_1eff82.jpg" 
SIDEBAR_LOGO = "download.png"

# --- SUPER ATTRACTIVE PURPLE & NEON ORANGE THEME CSS ---
st.markdown("""
<style>
    /* 1. Deep Matte Dark Base with Floating Geometrics Pattern */
    .stApp { 
        background-color: #0d1117;
        background-image: 
            radial-gradient(at 10% 10%, rgba(147, 51, 234, 0.1) 0px, transparent 50%),
            radial-gradient(at 90% 90%, rgba(249, 115, 22, 0.08) 0px, transparent 50%),
            url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43 25c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 56c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-7-43c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9 10c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm90-1c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-25 39c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm-3 51c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm-3-33c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM18 38c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM5 63c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM88 5c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM86 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm10 17c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM43 43c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-2 23c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm18 16c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM67 20c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM91 91c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4z' fill='%239333ea' fill-opacity='0.02' fill-rule='evenodd'/%3E%3C/svg%3E");
        color: #e2e8f0; 
        font-family: 'Open Sans', sans-serif;
    }
    
    /* Global Text overrides */
    h1, h2, h3, h4, .stHeader, [data-testid="stSubheader"] {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    
    /* 2. Glassmorphism Seat Card (Teacher View) */
    .seat-card { 
        background: rgba(30, 41, 59, 0.6); 
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 16px; 
        text-align: center; 
        height: 250px; 
        margin-bottom: 25px; 
        box-shadow: 0 10px 15px rgba(0,0,0,0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .seat-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 30px rgba(147, 51, 234, 0.2);
        border: 1px solid rgba(168, 85, 247, 0.4);
    }

    /* Glossy Purple Header */
    .seat-header { 
        background: linear-gradient(135deg, #9333ea 0%, #6b21a8 100%); 
        color: white; 
        font-weight: bold; 
        padding: 10px; 
        border-radius: 16px 16px 0 0; 
        font-size: 0.8rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .student-name { color: #ffffff; font-weight: bold; margin-top: 15px; font-size: 1.1rem; padding: 0 5px; }
    .sub-text { color: #cbd5e1; font-size: 0.85rem; margin-top: 5px; }
    
    /* Neon Badge Registration */
    .reg-text { 
        color: #f97316; 
        font-size: 0.9rem; 
        font-weight: bold; 
        margin-top: 10px; 
        background: rgba(249, 115, 22, 0.1);
        padding: 3px 10px;
        border-radius: 10px;
        display: inline-block;
        border: 1px solid rgba(249, 115, 22, 0.2);
    }
    
    .year-text { color: #f59e0b; font-size: 0.9rem; font-weight: bold; margin-top: 5px; }
    
    /* Gap Card Design */
    .gap-card { 
        background: repeating-linear-gradient(45deg, #1e293b, #1e293b 10px, #0d1117 10px, #0d1117 20px);
        border: 2px dashed #475569; 
        border-radius: 16px; 
        height: 250px; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        color: #64748b; 
        font-weight: bold;
        opacity: 0.5;
    }

    /* 3. Modern Floating Sidebar - Glassmorphism */
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Sidebar Radio elements coloring */
    [data-testid="stSidebar"] [data-baseweb="radio"] label {
        color: white !important;
    }
    
    [data-testid="stSidebar"] input[type="radio"]:checked + div {
        border-color: #9333ea !important;
        background-color: #9333ea !important;
    }

    /* 4. Digital Topic Header Styling - Purple Neon drop */
    .topic-header {
        display: flex;
        align-items: center;
        background: rgba(30, 41, 59, 0.5);
        padding: 15px;
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 25px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .topic-logo {
        font-size: 3rem;
        margin-right: 20px;
        color: #a855f7;
        filter: drop-shadow(0 0 10px #9333ea);
    }
    
    .topic-title-container h2 { margin: 0 !important; }
    .topic-subtitle { color: #94a3b8; font-size: 0.9rem; margin-top: 2px; }

    /* 5. Shiny Modern Buttons - Purple Gradient and drop */
    .stButton>button {
        border-radius: 10px;
        background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%);
        color: white;
        border: none;
        font-weight: bold;
        transition: 0.3s;
        box-shadow: 0 4px 10px rgba(168, 85, 247, 0.3);
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.5);
        background: linear-gradient(135deg, #c084fc 0%, #9333ea 100%);
    }
    
    /* Modern Inputs matte styling */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border-radius: 10px !important;
    }
    
    /* Divider modern coloring */
    div.stDivider { border-top: 1px solid rgba(255,255,255,0.05) !important; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR & NAV LOGIC ---
with st.sidebar:
    if os.path.exists(SIDEBAR_LOGO): st.image(SIDEBAR_LOGO, use_container_width=True)
    
    # Custom Sidebar Radio styling for better attractive look
    st.markdown('<p style="color:#cbd5e1; font-weight:bold; margin-bottom:5px;">CONTROL PANEL</p>', unsafe_allow_html=True)
    menu = st.radio("Navigation", ["🛡️ Admin Portal", "🧑‍🏫 Teacher View", "🔍 Student Search"], label_visibility="collapsed")

# --- APPLICATION START ---

if menu == "🛡️ Admin Portal":
    # Topic Header for ADMIN (Vibrant Purple icon drop)
    st.markdown("""
        <div class="topic-header">
            <div class="topic-logo">🛡️</div>
            <div class="topic-title-container">
                <h2>Admin Control Center</h2>
                <div class="topic-subtitle">System Configuration & Data Management</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    pwd = st.sidebar.text_input("Access Key", type="password")
    if pwd == "admin123":
        if os.path.exists(COLLEGE_LOGO): st.image(COLLEGE_LOGO, width=120)
        
        st.subheader("Hall & Seating Setup")
        c1, c2 = st.columns(2)
        h_cap = c1.number_input("Hall Capacity", 1, 1000, 25)
        row_w = c2.number_input("Seats per Row", 2, 12, 5)
        
        file = st.file_uploader("Upload Student Excel", type=['xlsx'])
        if file:
            if st.button("➕ Process/Update Students"):
                df_raw = pd.read_excel(file,engine='openpyxl')
                df_raw.columns = [c.lower().strip().replace(' ', '_') for c in df_raw.columns]
                
                with sqlite3.connect(DB_NAME) as conn:
                    existing_regs = pd.read_sql_query("SELECT register_no FROM students", conn)['register_no'].astype(str).tolist()
                
                new_regs = df_raw['register_no'].astype(str).tolist()
                dupes = [r for r in new_regs if r in existing_regs]

                if dupes:
                    st.error(f"❌ Error: Register Number(s) {', '.join(dupes[:3])} already exist!")
                else:
                    new_students = df_raw.to_dict('records')
                    with sqlite3.connect(DB_NAME) as conn:
                        gaps = pd.read_sql_query("SELECT seat_no FROM students WHERE subject = 'EMPTY_GAP' ORDER BY seat_no", conn)
                        gap_list = gaps['seat_no'].tolist()
                        to_append, filled = [], 0
                        for student in new_students:
                            if filled < len(gap_list):
                                s_no = gap_list[filled]
                                conn.execute("UPDATE students SET register_no=?, name=?, department=?, subject=?, year=? WHERE seat_no=?", (str(student['register_no']), student['name'], student['department'], student['subject'], student.get('year', 1), s_no))
                                filled += 1
                            else: to_append.append(student)
                        if to_append:
                            last_seat = conn.execute("SELECT MAX(seat_no) FROM students").fetchone()[0] or 0
                            processed = generate_dynamic_seating(pd.DataFrame(to_append), h_cap, row_w, start_idx=last_seat)
                            processed.to_sql('students', conn, if_exists='append', index=False)
                        conn.commit(); st.success(f"Gaps Filled: {filled} | New Added: {len(to_append)}"); time.sleep(1); st.rerun()

        st.divider()
        st.subheader("Dangerous Zone")
        w1, w2 = st.columns(2)
        if w1.button("🔴 Wipe Student Data"):
            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM students")
            st.warning("🗑️ Student data wiped successfully!")
            time.sleep(1); st.rerun()
        if w2.button("🟠 Wipe Staff Data"):
            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM invigilators")
            st.warning("🗑️ Staff data wiped successfully!")
            time.sleep(1); st.rerun()

        # Staff Allocation Logic
        with sqlite3.connect(DB_NAME) as conn:
            staff_count = conn.execute("SELECT COUNT(*) FROM invigilators").fetchone()[0]
        
        st.divider()
        st.subheader("👨‍🏫 Staff Allocation")
        if staff_count == 0:
            staff_file = st.file_uploader("Upload Staff Excel", type=['xlsx'])
            if staff_file and st.button("🔄 Allocate Staff"):
                staff_df = pd.read_excel(staff_file)
                staff_df.columns = [c.lower().strip() for c in staff_df.columns]
                
                if staff_df['staff_id'].duplicated().any():
                    st.error("❌ Error: Duplicate Staff IDs found in the Excel file.")
                else:
                    with sqlite3.connect(DB_NAME) as conn:
                        hall_data = pd.read_sql_query("SELECT hall_no, GROUP_CONCAT(DISTINCT department) as hall_depts FROM students GROUP BY hall_no", conn)
                        h_list, s_pool = hall_data.to_dict('records'), staff_df.to_dict('records')
                        random.shuffle(s_pool)
                        final_allocs, assigned_ids = [], set()
                        for hall in h_list:
                            h_depts = [d.strip().upper() for d in str(hall['hall_depts']).split(',')]
                            selected = next((s for s in s_pool if str(s['staff_id']) not in assigned_ids and str(s['department']).strip().upper() not in h_depts), None)
                            if not selected: selected = next((s for s in s_pool if str(s['staff_id']) not in assigned_ids), None)
                            if selected:
                                assigned_ids.add(str(selected['staff_id']))
                                final_allocs.append((str(selected['staff_id']), selected['staff_name'], int(hall['hall_no'])))
                        conn.executemany("INSERT INTO invigilators (staff_id, staff_name, assigned_hall) VALUES (?, ?, ?)", final_allocs)
                        conn.commit(); st.success("Staff Allocated!"); time.sleep(1); st.rerun()
        else: st.info("✅ Staff already allocated.")

        st.divider()
        st.subheader("📄 Reports Download")
        with sqlite3.connect(DB_NAME) as conn:
            sf_list = pd.read_sql_query("SELECT * FROM invigilators", conn)
            st_list = pd.read_sql_query("SELECT * FROM students", conn)
            
            d1, d2 = st.columns(2)
            if REPORTLAB_AVAILABLE:
                if not sf_list.empty: d1.download_button("📄 Download Staff PDF", generate_staff_pdf(sf_list), "Staff_Duty.pdf", use_container_width=True)
                if not st_list.empty: d2.download_button("📄 Download Seating PDF", generate_hall_pdf(st_list), "Seating_Plan.pdf", use_container_width=True)
            else:
                st.warning("⚠️ PDF generation is unavailable. Please install `reportlab` library.")

    else:
        if pwd: st.sidebar.error("Invalid Access Key")
        st.info("Please enter the Access Key in the sidebar to enter Admin Portal.")

elif menu == "🧑‍🏫 Teacher View":
    # Topic Header for TEACHER (Vibrant Purple icon drop)
    st.markdown("""
        <div class="topic-header">
            <div class="topic-logo">🧑‍🏫</div>
            <div class="topic-title-container">
                <h2>Hall Seating Viewer</h2>
                <div class="topic-subtitle">Real-time Visual Seating Layout</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with sqlite3.connect(DB_NAME) as conn:
        halls_df = pd.read_sql_query("SELECT DISTINCT hall_no FROM students ORDER BY hall_no", conn)
    
    if not halls_df.empty:
        c1, c2 = st.columns([2, 1])
        sel_h = c1.selectbox("Select Hall No", halls_df['hall_no'].tolist())
        display_cols = c2.slider("Seats per Row", 2, 12, 5)
        
        with sqlite3.connect(DB_NAME) as conn:
            data = pd.read_sql_query("SELECT * FROM students WHERE hall_no = ? ORDER BY seat_no", conn, params=(sel_h,))
        
        st.divider()
        st.subheader(f"Exam Hall Layout: Hall {sel_h}")
        
        rows = (len(data)//display_cols) + (1 if len(data)%display_cols > 0 else 0)
        for r in range(rows):
            cols_grid = st.columns(display_cols)
            for c in range(display_cols):
                idx = r * display_cols + c
                if idx < len(data):
                    s = data.iloc[idx]
                    if s['subject'] == "EMPTY_GAP": 
                        cols_grid[c].markdown('<div class="gap-card">EMPTY</div>', unsafe_allow_html=True)
                    else: 
                        cols_grid[c].markdown(f"""
                        <div class="seat-card">
                            <div class="seat-header">SEAT {s['seat_no']}</div>
                            <div class="student-name">{s['name']}</div>
                            <div class="sub-text">{s['subject']}</div>
                            <div class="year-text">Year: {s['year']}</div>
                            <div class="sub-text" style="font-size:0.75rem; color:#64748b;">{s['department']}</div>
                            <div class="reg-text">{s['register_no']}</div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.warning("No seating data available. Admins must process student data first.")

elif menu == "🔍 Student Search":
    # Topic Header for STUDENT SEARCH (Vibrant Purple icon drop)
    st.markdown("""
        <div class="topic-header">
            <div class="topic-logo">🔍</div>
            <div class="topic-title-container">
                <h2>Quick Seat Finder</h2>
                <div class="topic-subtitle">Find your assigned Exam Hall and Seat</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("Student Seating Lookup")
    reg = st.text_input("Enter your Register Number", key="student_reg_input")
    
    if reg:
        with sqlite3.connect(DB_NAME) as conn:
            res = pd.read_sql_query("SELECT * FROM students WHERE register_no = ?", conn, params=(reg,))
        
        if not res.empty: 
            st.markdown(f"""
            <div style="background:rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); padding:25px; border-radius:15px; border:1px solid rgba(168, 85, 247, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <h2 style="color:#ffffff; margin:0 0 15px 0;">✅ Seat Found!</h2>
                <p style="font-size:1.3rem; margin:8px 0;"><b>Name:</b> {res.iloc[0]['name']}</p>
                <hr style="border:0.5px solid rgba(255,255,255,0.05); margin:15px 0;">
                <p style="font-size:1.3rem; margin:8px 0;">🏛️ <b>Exam Hall:</b> Hall <span style="color:#f97316; font-size:1.5rem; font-weight:bold;">{res.iloc[0]['hall_no']}</span></p>
                <p style="font-size:1.3rem; margin:8px 0;">💺 <b>Seat No:</b> <span style="color:#f97316; font-size:1.5rem; font-weight:bold;">{res.iloc[0]['seat_no']}</span></p>
                <p style="font-size:1.1rem; color:#cbd5e1; margin:15px 0 0 0;"><b>Subject:</b> {res.iloc[0]['subject']}</p>
            </div>
            """, unsafe_allow_html=True)
        else: 
            st.markdown(f"""
            <div style="background:rgba(239, 68, 68, 0.1); backdrop-filter: blur(10px); padding:20px; border-radius:15px; border:1px solid #ef4444; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <h3 style="color:#ef4444; margin:0;">❌ Student Not Found</h3>
                <p style="margin:10px 0 0 0;">Please check the register number and try again. Contact Admin if the issue persists.</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Input your unique Register Number above to find your seating details.")