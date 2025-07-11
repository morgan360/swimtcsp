# 🧑‍💻 TCSP System Roles – Consolidation & Redesign Plan

This document outlines the current system roles, plans for consolidation, and future role strategy including access levels for staff, schools, guardians, and ownership.

---

## ✅ Roles to Keep

| Role Name       | Purpose                                                                 |
|-----------------|-------------------------------------------------------------------------|
| `administrator` | Full access excluding superuser actions. Can manage all entities, assign managers, but not other administrators. |
| `bbp_blocked`   | Used to block users from accessing the system.                         |
| `Customer`      | Default role for anyone who signs up. Can book public swims.           |
| `ex-staff`      | Former staff whose accounts should be blocked while data is preserved. |
| `guardian`      | Can book lessons and public swims. Can also participate in schools.    |
| `guest`         | Temporary elevated access to simulate manager capabilities.            |
| `instructor`    | Can view staff schedules, record attendance, and update swim assessments. |
| `pool_manager`  | Operational control: move students, manage waiting lists, view orders, hijack sessions. Can assign any role below `manager`. |
| `schools`       | Represents users participating in school programs. May book or manage school swim groups. |

---

## 🗑️ Roles to Remove / Consolidate

| Old Role Name       | Action                                 | Reason |
|---------------------|----------------------------------------|--------|
| `admin`             | ❌ Delete                               | Redundant. Use `administrator`. |
| `bishop_galvin`     | ❌ Delete, merge into `schools`         | School-specific role now unified. |
| `bishopgalvin`      | ❌ Delete, merge into `schools`         | Typo/redundant. |
| `coupon_manager`    | ❌ Delete                               | Functionality will be given to `administrator`. |
| `desk_duties`       | ❌ Delete                               | No longer required. |
| `editor`            | ❌ Delete                               | Not applicable. |
| `guardian_temporary`| ❌ Delete                               | Handled via `guest`. |
| `instructors`       | ❌ Delete, merge into `instructor`      | Redundant plural. |
| `manager`           | ❌ Delete                               | Overlapping with `pool_manager`. |
| `pool_administrator`| ❌ Delete                               | Merge responsibility under `pool_manager`. |
| `sh4_admin`         | ❌ Delete                               | Not relevant. |
| `shop_manager`      | ❌ Delete                               | Shop module likely deprecated. |
| `zion`              | ❌ Delete  and incorporate into schools | 

---

## 🆕 Proposed Role

| Role Name | Purpose |
|-----------|---------|
| `owner`   | Executive read-only access to key reports and dashboards. No CRUD access. Intended for pool ownership or stakeholders interested in operational overviews without editing capabilities. |

### `owner` Role Access:
- 📈 View reports (bookings, revenue, utilization).
- 📊 See dashboards (attendance, waiting lists, trends).
- 👁️ Read-only access only. No modifications allowed.

---

## 🔐 Role Hierarchy Overview

```text
Superuser
  └── administrator
        └── pool_manager
              ├── instructor
              ├── guardian
              ├── guest
              └── schools
