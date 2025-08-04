
# 🧭 Swimling Guardian Dashboard Overview

The dashboard provides Guardians with full control over their Swimling(s)’ lesson participation. It includes interactive panels for:

- Public Lessons
- School Lessons
- Waiting List
- Swimling Management

---

## 🔹 Panels Overview

### 1. Public Lessons Panel
Showld be arranged as a table with action buttons on the Right
**Rows**: One per Swimling  
**Columns**:
- **Swimling Name**
- **Current Term**: All lessons currently registered.
- **Next Term**: All future bookings.
- **Actions**:
  - `Book Current`: If unregistered for current term and booking is open.
  - `Rebook`: If registered and inside rebooking window.
  - `Book Next`: If after general booking date and not already booked.
  - `Waiting List`: Can join waiting list for New registration or Transfer

**Note**: Even if already booked, additional lessons may be booked. No restriction on multiple bookings.

---

### 2. School Lessons Panel
**Visible only if Swimlings have `sco_role_num`**  
**Rows**: One per School Swimling  
**Columns**:
- Swimling Name
- Assigned School
- Assigned Lesson (if booked)

**Action**:  
- `Book Now` button if bookings are open for that school’s term.

---

### 3. Waiting List Panel
**Rows**: One per waiting list entry  
**Columns**:
- Swimling Name
- Requested Lesson
- Assigned Lesson (if offered)
- **Actions**:
  - `✅ Book Now`: Goes directly to product detail view with Swimling + Lesson preselected and locked.
  - `🗑️ Remove`: Removes entry from waiting list.

**Logic**:  
Entries are **hidden after successful booking** by marking the record complete.

---

### 4. Swimling Management Panel
Allows Guardians to:
- ➕ Add a new Swimling
- ✏️ Edit existing Swimlings (name, DOB, notes, school role number)

---
## Phases
In every term there are a number of phases:

| Phase              | Book Current Term |
| Before Booking | From **start_date** to **rebooking_date** |
| Rebooking Window| From **rebooking_date** to **booking_date** |
| Open Booking | From **booking_date** to **end_date** |

## 📘 Booking Rules

| Phase              | Book Current Term | Rebook for Next Term | Book Next Term |Waiting List|
|-------------------|-------------------|----------------------|----------------|-------------|
| **Before Rebooking** | ✅ Yes            | ❌ No                | ❌ No          |✅ Yes |
| **Rebooking Window** | ✅ Yes            | ✅ Yes               | ❌ No          |✅ Yes |
| **Open Booking**     | ❌ No             | ❌ No                | ✅ Yes         |✅ Yes |

---

## 🧑‍💻 User Permissions

Guardians will see:

- ✅ **Public Lessons Panel** – always
- ✅ **School Panel** – if any Swimlings have `sco_role_num`
- ✅ **Waiting List Panel** – if any entries exist
- ✅ **Swimling Editor** – always
