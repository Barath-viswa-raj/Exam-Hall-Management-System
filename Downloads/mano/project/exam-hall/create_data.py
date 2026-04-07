import pandas as pd

data = {
    'register_no': [f'REG{i:03d}' for i in range(1, 90)],
    'name': [f'Student {i}' for i in range(1, 90)],
    'department': ['CS', 'MECH'] * 45,
    # Assign different subjects to see the interleaving
    'subject': ['Mathematics', 'Physics', 'Chemistry', 'Biology'] * 22 + ['Mathematics'],
    'sem': [4] * 90
}

pd.DataFrame(data).to_excel("test_subjects.xlsx", index=False)
print("✅ Created 'test_subjects.xlsx' with 4 different subjects.")






