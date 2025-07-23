# 🏊 TCSP Instructor Structure

## 🧑‍🏫 Instructor Qualifications

All instructors at TCSP are certified by **Swim Ireland** and hold one of the following qualifications:

- **Level 1 Assistant Swimming Teacher**
- **Level 2 Swimming Teacher**

Most of our instructors are current or former competitive swimmers, bringing both experience and passion to every lesson.

---

## 👥 Roles and Responsibilities

### Role Assignments

- All instructors are identified as **users** with the role:  
  `instructor`
- Those with only **Assistant Swimming Teacher** qualifications are additionally assigned the role:  
  `assistant`

### Lesson Assignment

- **All lessons must have an assigned Instructor.**
- Only users with the role `instructor` (i.e. Level 2 Teachers) can be assigned to lead lessons.
- Assistant Teachers may support but are not assigned directly as the main instructor.

---

## 📝 Instructor Duties

### Progress Reporting

- Instructors are responsible for compiling **end-of-term progress reports** for each swimling they teach.
- These reports cover skill levels and development across the term.

### Cover Arrangements

- If an instructor is **unavailable to teach a lesson**, they are expected to **organize a qualified replacement** for their session.
- Substitutes must also hold the `instructor` role and appropriate Swim Ireland certification.

---
## ADMIN
progress/management/commands/
├── export_skills_data.py
└── import_skills_data.py

📤 Exporting from PythonAnywhere
Run the following command on your live server (e.g. via SSH or PythonAnywhere console):

python manage.py export_skills_data
This will generate a file named:

skills_export.json
Download this file and copy it into your local project root.

📥 Importing into Local Environment
To reset and import data locally:

python manage.py import_skills_data --purge
This will:

Delete existing data from the relevant models.
Load all records from skills_export.json.
⚠️ Warning: This will erase local data in the above models.
