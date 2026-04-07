import sqlite3
import pandas as pd

DB_NAME = "exam_management.db"

def init_db():
    """Database tables-ai create pannum. sem-ku bathila year column sethu create pannum."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Students Table (sem-ku bathila year nu mathiyachu)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            register_no TEXT PRIMARY KEY,
            name TEXT,
            department TEXT,
            subject TEXT,
            year INTEGER,
            hall_no INTEGER,
            seat_no INTEGER,
            file_name TEXT
        )
    """)

    # Safety Migration: Year column illai-na add pannum
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN year INTEGER")
    except:
        pass

    # 2. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)

    # 3. Invigilators Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invigilators (
            staff_id TEXT PRIMARY KEY,
            staff_name TEXT,
            department TEXT,
            assigned_hall INTEGER
        )
    """)

    # Default Admin Login
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'admin')")

    conn.commit()
    conn.close()

# --- MAIN APPEND LOGIC ---

def save_seating_to_db(df, h_cap, current_filename="Unknown"):
    """
    Pazhaiya data-vai azhikkaamal pudhu data-vai mattum append pannum.
    'sem' column excel-la iruntha athai 'year' nu mathi save pannum.
    """
    conn = sqlite3.connect(DB_NAME)
    
    try:
        # 1. Database-la munnadiye ethana per irukaanga nu check panrom
        existing_count_query = "SELECT COUNT(*) as total FROM students"
        existing_count = pd.read_sql_query(existing_count_query, conn).iloc[0]['total']
        
        # 2. Excel columns clean-up
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
        
        # Oru vélai excel-la 'sem' nu iruntha athai 'year' nu mathi save panna
        if 'sem' in df.columns:
            df = df.rename(columns={'sem': 'year'})
        
        # 3. Thodarchiyaana Seat, Hall and File Name logic
        new_entries = []
        for i, row in df.iterrows():
            current_idx = existing_count + i
            row_dict = row.to_dict()
            row_dict['seat_no'] = int(current_idx + 1)
            row_dict['hall_no'] = int((current_idx // h_cap) + 1)
            row_dict['file_name'] = current_filename
            new_entries.append(row_dict)
        
        final_df = pd.DataFrame(new_entries)

        # 4. IF_EXISTS='APPEND'
        final_df.to_sql("students", conn, if_exists="append", index=False)
        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return "Error: Duplicate Register Numbers! Intha register no munnadiye database-la irukku."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()

# --- DATA VIEW FUNCTIONS ---

def get_last_uploaded_filename():
    """Kadaisiya upload panna file name-ai mattum edukka."""
    conn = sqlite3.connect(DB_NAME)
    res = conn.execute("SELECT file_name FROM students WHERE file_name IS NOT NULL ORDER BY rowid DESC LIMIT 1").fetchone()
    conn.close()
    return res[0] if res else "No uploads yet"

def get_all_students():
    """Motha students list-aiyum edukka."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM students ORDER BY seat_no", conn)
    conn.close()
    return df

def get_hall_students(hall_no):
    """Hall wise students-ai paarkka."""
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM students WHERE hall_no = ? ORDER BY seat_no"
    df = pd.read_sql_query(query, conn, params=(hall_no,))
    conn.close()
    return df

# --- CLEANUP ---

def wipe_all_data():
    """Fresh-ah start panna mattum use pannunga."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM invigilators")
    conn.commit()
    conn.close()

# --- LOGIN ---

def check_login(user, pwd):
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT role FROM users WHERE username=? AND password=?"
    df = pd.read_sql_query(query, conn, params=(user, pwd))
    conn.close()
    return df.iloc[0]['role'] if not df.empty else None