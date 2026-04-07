import sqlite3

# Check database staff records
conn = sqlite3.connect('exam_management.db')
cursor = conn.cursor()

print("=== DATABASE STAFF RECORDS ===")
cursor.execute('SELECT * FROM invigilators')
staff_records = cursor.fetchall()
print(f"Total staff in database: {len(staff_records)}")
for record in staff_records:
    print(f"ID: {record[0]}, Name: {record[1]}, Hall: {record[2]}")

print("\n=== DATABASE STUDENT RECORDS ===")
cursor.execute('SELECT DISTINCT hall_no FROM students WHERE subject != "EMPTY_GAP"')
halls = cursor.fetchall()
print(f"Total halls with students: {len(halls)}")
for hall in halls:
    print(f"Hall: {hall[0]}")

conn.close()
