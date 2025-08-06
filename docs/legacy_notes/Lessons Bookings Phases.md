# 🏊‍♀️ Swimling Booking Process Overview

The SwimTCSP system enables **Guardians** (parents or carers) to manage swimming lessons for their **Swimlings** (children). This includes registration, term bookings, and rebookings.

---

## 👶 Swimling Registration

Guardians can register their Swimlings by providing:

- **First Name**
- **Last Name**
- **Date of Birth**
- **Notes** (e.g. medical, skill level)

This information is stored for future bookings and rebookings.

---

## 📅 Booking Phases

Each swimming term is divided into three booking phases, allowing for structured access and priority.

### 1. Initial Booking Phase
- **When:** From the **start of the current term** to the **`rebooking_date`**
- **Who can book:** Any Guardian
- **Action:** Book Swimlings into **available classes in the current term**

### 2. Rebooking Phase
- **When:** From the **`rebooking_date`** to the **`booking_date`**
- **Who can book:** Guardians of Swimlings **already booked into the current term**
- **Action:** Rebook the **same class** for the **next term**

### 3. Open Booking Phase
- **When:** From the **`booking_date`** to the **end of the term**
- **Who can book:** **Any Guardian**, regardless of current-term booking status
- **Action:** Book Swimlings into **any class** in the **next term**

---

## 🔁 Booking Phase Summary

| Phase               | Timeframe                        | Eligibility                            | Booking Action                          |
|--------------------|----------------------------------|----------------------------------------|-----------------------------------------|
| Initial Booking     | Start of term → `rebooking_date` | Any Guardian                           | Book into **current** term classes      |
| Rebooking           | `rebooking_date` → `booking_date`| Guardians with current-term bookings   | Rebook **same class** for next term     |
| Open Booking        | `booking_date` → End of term     | Any Guardian                           | Book into **any** class for next term   |

---

Let me know if you would like this adapted as a help page, onboarding text, or included in a specific Django view or template.
