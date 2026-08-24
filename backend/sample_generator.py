import os
import pandas as pd

def generate_sample_excel(output_path: str = "sample_data/mighty_knight_template.xlsx"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1. Coaches Data (Matching BRD Section 6 & Priorities)
    coaches_data = [
        {
            "Coach Name": "Guruvanthana",
            "Levels Handled": "Basic 1, Basic 2, Beginner 1, Beginner 2, Beginner 3, Early Intermediate 1",
            "Monthly Class Capacity": "60 - 90",
            "Monday Max": 4, "Tuesday Max": 4, "Wednesday Max": 4, "Thursday Max": 4, "Friday Max": 4, "Saturday Max": 5, "Sunday Max": 2,
            "Sunday Preference": "Available",
            "Preferred Timings": "Evening (4 PM - 9 PM)",
            "Special Comments": "Primary lead for Beginner batches",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Dhaanush",
            "Levels Handled": "Beginner 1, Beginner 2, Beginner 3, Early Intermediate 1, Early Intermediate 2, Intermediate",
            "Monthly Class Capacity": "70 - 78",
            "Monday Max": 4, "Tuesday Max": 4, "Wednesday Max": 4, "Thursday Max": 4, "Friday Max": 4, "Saturday Max": 5, "Sunday Max": 0,
            "Sunday Preference": "No Sunday Tournaments",
            "Preferred Timings": "Midday & Evening",
            "Special Comments": "Avoid Sunday tournament assignments",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Arshath",
            "Levels Handled": "Early Intermediate 2, Intermediate",
            "Monthly Class Capacity": "35 - 40",
            "Monday Max": 3, "Tuesday Max": 3, "Wednesday Max": 3, "Thursday Max": 3, "Friday Max": 3, "Saturday Max": 4, "Sunday Max": 2,
            "Sunday Preference": "Available",
            "Preferred Timings": "Evening (6 PM - 9 PM)",
            "Special Comments": "Senior Master Coach for Intermediate levels",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Saravanan",
            "Levels Handled": "Beginner 2, Beginner 3, Early Intermediate 1, Intermediate",
            "Monthly Class Capacity": "30 - 60",
            "Monday Max": 3, "Tuesday Max": 3, "Wednesday Max": 3, "Thursday Max": 3, "Friday Max": 3, "Saturday Max": 4, "Sunday Max": 0,
            "Sunday Preference": "No Sunday Tournaments",
            "Preferred Timings": "Evening",
            "Special Comments": "Avoid Sunday tournament assignments",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Bathrinath",
            "Levels Handled": "Basic 1, Basic 2, Beginner 1, Beginner 2",
            "Monthly Class Capacity": "60 - 90",
            "Monday Max": 4, "Tuesday Max": 4, "Wednesday Max": 4, "Thursday Max": 4, "Friday Max": 4, "Saturday Max": 5, "Sunday Max": 2,
            "Sunday Preference": "Available",
            "Preferred Timings": "Morning & Evening",
            "Special Comments": "Top Priority for Basic levels",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Abinaya",
            "Levels Handled": "Basic 1, Basic 2, Beginner 1",
            "Monthly Class Capacity": "30 - 60",
            "Monday Max": 3, "Tuesday Max": 3, "Wednesday Max": 3, "Thursday Max": 3, "Friday Max": 3, "Saturday Max": 4, "Sunday Max": 2,
            "Sunday Preference": "Available",
            "Preferred Timings": "Morning (6 AM - 8 AM) & Evening",
            "Special Comments": "Available for early morning slots",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Prakash",
            "Levels Handled": "Basic 1, Basic 2, Beginner 1, Beginner 2, Beginner 3, Early Intermediate 1, Early Intermediate 2, Intermediate",
            "Monthly Class Capacity": "30 - 100",
            "Monday Max": 4, "Tuesday Max": 4, "Wednesday Max": 4, "Thursday Max": 4, "Friday Max": 4, "Saturday Max": 5, "Sunday Max": 2,
            "Sunday Preference": "Available",
            "Preferred Timings": "All Operating Hours",
            "Special Comments": "Versatile Coach across all levels",
            "Temporary Exceptions": ""
        },
        {
            "Coach Name": "Manikandan",
            "Levels Handled": "Basic 1, Basic 2, Beginner 1",
            "Monthly Class Capacity": "16 - 20",
            "Monday Max": 2, "Tuesday Max": 2, "Wednesday Max": 2, "Thursday Max": 2, "Friday Max": 2, "Saturday Max": 3, "Sunday Max": 1,
            "Sunday Preference": "Available",
            "Preferred Timings": "Evening",
            "Special Comments": "Part-time Coach",
            "Temporary Exceptions": ""
        }
    ]

    # 2. Sample Students Data (Realistic coverage across 8 levels and batch types)
    students_data = [
        # Basic 1 - Group Batch
        {"Student ID": "STU001", "Student Name": "Aarav Sharma", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU002", "Student Name": "Ananya Patel", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU003", "Student Name": "Rohan Gupta", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU004", "Student Name": "Diya Iyer", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU005", "Student Name": "Kabir Mehta", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU006", "Student Name": "Sanya Malhotra", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU007", "Student Name": "Arjun Reddy", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU008", "Student Name": "Isha Joshi", "Student Level": "Basic 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "05:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "05:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "05:00 PM – 09:00 PM", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},

        # Basic 2 - Group Batch
        {"Student ID": "STU009", "Student Name": "Aditya Verma", "Student Level": "Basic 2", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "06:00 PM – 08:00 PM", "Tuesday": "06:00 PM – 08:00 PM", "Wednesday": "Not Available", "Thursday": "06:00 PM – 08:00 PM", "Friday": "Not Available", "Saturday": "05:00 PM – 09:00 PM", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU010", "Student Name": "Meera Nair", "Student Level": "Basic 2", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "06:00 PM – 08:00 PM", "Tuesday": "06:00 PM – 08:00 PM", "Wednesday": "Not Available", "Thursday": "06:00 PM – 08:00 PM", "Friday": "Not Available", "Saturday": "05:00 PM – 09:00 PM", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU011", "Student Name": "Karan Singh", "Student Level": "Basic 2", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "06:00 PM – 08:00 PM", "Tuesday": "06:00 PM – 08:00 PM", "Wednesday": "Not Available", "Thursday": "06:00 PM – 08:00 PM", "Friday": "Not Available", "Saturday": "05:00 PM – 09:00 PM", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},

        # Beginner 1 - Limited Batch (L)
        {"Student ID": "STU012", "Student Name": "Tara Sen", "Student Level": "Beginner 1", "Batch Type": "L", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "04:00 PM – 06:00 PM", "Tuesday": "04:00 PM – 06:00 PM", "Wednesday": "No Preference", "Thursday": "No Preference", "Friday": "Not Available", "Saturday": "No Preference", "Sunday": "09:00 AM – 12:00 PM", "Tournament Preference": "Yes", "Additional Comments": ""},
        {"Student ID": "STU013", "Student Name": "Varun Rao", "Student Level": "Beginner 1", "Batch Type": "L", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "04:00 PM – 06:00 PM", "Tuesday": "04:00 PM – 06:00 PM", "Wednesday": "No Preference", "Thursday": "No Preference", "Friday": "Not Available", "Saturday": "No Preference", "Sunday": "09:00 AM – 12:00 PM", "Tournament Preference": "Yes", "Additional Comments": ""},

        # Beginner 2 & 3
        {"Student ID": "STU014", "Student Name": "Nikhil Deshmukh", "Student Level": "Beginner 2", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "07:00 PM – 09:00 PM", "Tuesday": "07:00 PM – 09:00 PM", "Wednesday": "07:00 PM – 09:00 PM", "Thursday": "No Preference", "Friday": "No Preference", "Saturday": "05:00 PM – 09:00 PM", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU015", "Student Name": "Prisha Kapoor", "Student Level": "Beginner 3", "Batch Type": "L", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "No Preference", "Tuesday": "05:00 PM – 07:00 PM", "Wednesday": "No Preference", "Thursday": "05:00 PM – 07:00 PM", "Friday": "No Preference", "Saturday": "05:00 PM – 09:00 PM", "Sunday": "09:00 AM – 01:00 PM", "Tournament Preference": "Yes", "Additional Comments": ""},

        # Early Intermediate 1 & 2
        {"Student ID": "STU016", "Student Name": "Devansh Saxena", "Student Level": "Early Intermediate 1", "Batch Type": "G", "Region/TimeZone": "IST", "Required Classes": 8, "Monday": "06:00 PM – 08:00 PM", "Tuesday": "Not Available", "Wednesday": "06:00 PM – 08:00 PM", "Thursday": "Not Available", "Friday": "06:00 PM – 08:00 PM", "Saturday": "05:00 PM – 09:00 PM", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": ""},
        {"Student ID": "STU017", "Student Name": "Riya Banerjee", "Student Level": "Early Intermediate 2", "Batch Type": "I", "Region/TimeZone": "IST", "Required Classes": 4, "Monday": "07:00 PM – 09:00 PM", "Tuesday": "07:00 PM – 09:00 PM", "Wednesday": "Not Available", "Thursday": "Not Available", "Friday": "Not Available", "Saturday": "No Preference", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": "Individual training request"},

        # Intermediate
        {"Student ID": "STU018", "Student Name": "Vihaan Agarwal", "Student Level": "Intermediate", "Batch Type": "I", "Region/TimeZone": "IST", "Required Classes": 4, "Monday": "08:00 PM – 09:00 PM", "Tuesday": "Not Available", "Wednesday": "08:00 PM – 09:00 PM", "Thursday": "Not Available", "Friday": "08:00 PM – 09:00 PM", "Saturday": "07:00 PM – 09:00 PM", "Sunday": "Not Available", "Tournament Preference": "No", "Additional Comments": "Master preparation batch"}
    ]

    df_coaches = pd.DataFrame(coaches_data)
    df_students = pd.DataFrame(students_data)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_students.to_excel(writer, sheet_name="Students", index=False)
        df_coaches.to_excel(writer, sheet_name="Coaches", index=False)

    print(f"Sample template generated successfully at: {output_path}")

if __name__ == "__main__":
    generate_sample_excel()
