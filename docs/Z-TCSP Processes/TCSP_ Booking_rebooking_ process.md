# 🧭 Swimling Guardian Dashboard Overview

The dashboard provides **Guardians** with complete control over their **Swimling(s)'** lesson registrations across:

- **Public Lessons**
- **School Lessons**
- **Waiting Lists**
- **Swimling Management**

---

## 🔹 Panels Overview

### 1. **Public Lessons Panel**

Displays **one row per Swimling × Lesson combination**.

**Columns:**
- **Swimling Name**
- **Current Term**: Shows all lessons the swimling is currently registered for
- **Next Term**: Shows lessons already booked for the upcoming term
- **Action Button**:
  - `Book Current`: if not yet registered for current term (active until `booking_date`)
  - `Rebook`: if registered this term and in rebooking window (`rebooking_date` → `booking_date`)
  - `Book Next`: if after `booking_date` and swimling isn’t booked yet

---

### 2. **School Lessons Panel** *(visible only to guardians with Swimlings in a school program)*

**Rows:** One per school swimling

**Columns:**
- **Swimling Name**
- **Assigned School**
- **Assigned Lesson** (if booked)
- **Action**:
  - `Book Now` button (if booking is open for that school’s term)

---

### 3. **Waiting List Panel**

Shows all Swimlings the guardian has added to a waiting list.

**Columns:**
- **Swimling Name**
- **Requested Lesson**
- **Assigned Lesson** (if offered)

**Actions:**
- `Remove from Waiting List`
- `Book Now` (if a place has been offered)

---

### 4. **Swimling Management Panel**

Allows guardians to:
- ➕ Add a new Swimling
- ✏️ Edit existing Swimling info (name, DOB, notes, school role number)

---

## 📘 Booking Rules

| Phase              | Can Book into Current Term | Can Rebook for Next Term | Can Book into Next Term |
|--------------------|----------------------------|---------------------------|--------------------------|
| **Before Rebooking** | ✅ Yes                     | ❌ No                     | ❌ No                   |
| **Rebooking Window** | ✅ Yes                     | ✅ Yes                    | ❌ No                   |
| **Open Booking**     | ❌ No                      | ❌ No                     | ✅ Yes                  |

---

## 🧑‍💻 User Permissions

Guardians will see:

- ✅ **Public Lessons Panel**: always
- ✅ **School Panel**: only if one or more swimlings has a `sco_role_num`
- ✅ **Waiting List Panel**: only if they have active waiting list entries
- ✅ **Swimling Editor**: always

