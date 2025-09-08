# 🧑‍💻 TCSP System Roles – Consolidation & Redesign Plan

This document outlines the current system roles, plans for consolidation, and future role strategy including access levels for staff, schools, guardians, and ownership.

---

## ✅ NEW ROLES (aka Groups)

**Note: All *new* roles for the new website are captialsied**

| Role Name       | Purpose                                                                 |
|-----------------|-------------------------------------------------------------------------|
| `Customer` | Default for every user. Can view and book public swims. |
| `Guardian` | Can add swimlings to their account and book into term-based lessons. Must be a customer first. |
| `Schools` | Can book into schools lessons. Must be a Guardian first. |
| `Desk` | Can access existing user information. Can edit existing user information. Can view public swims management panel (cannot edit swims or add new swims). Can access lessons list and view class history. Can view isntructor assignments but not assign. Have full control over the swimlings panel and can move swimlings to/from classes. Can view enrollment stats. Can print class lists. Can view term information. Cannot access schools management panel. Can access orders dashboard. Cannot see the Management or Coupons panels. |
| `Instructor` | Can view the instructor dashboard in the main menu. Can view their assigned lessons. Can evaluate the students' skills. Can take attendance. Can view their class list. |
| `Full-Timer` | Have all the capabilities of desk staff. Cannot change user groups/permissions. Cannot do refunds. Cannot view financial reports. Can add/remove/alter public swim and lesson details. |
| `Manager` | Full access to all admin panels and can add/remove/view/change all products. Can assign user roles/groups. |


## Old Roles and Proposed Actions


| Role Name           |Action|Reason|
|---------------------|-----------------------------------------|------------------------------------------------|
| `administrator`     | ❌ Delete, merge into `Manager`         | Redundant. Use `Manager`.|
| `bbp_blocked`       | ⚠️ TBD                                  | Unsure if needed. |
| `Customer`          | ✅ Keep and reuse                       | NA |
| `ex-staff`          | ⚠️ TBD                                  | Can this be capitalised? |
| `guardian`          | ❌ Delete, merge into `Guardian`        | Update for clarity. |
| `guest`             | ⚠️ TBD                                  | Unsure if needed. |
| `instructor`        | ❌ Delete, merge into `Instructor`      | Redundant lower case version. |
| `pool_manager`      | ❌ Delete, merge into `Manager`         | Redundant. |
| `schools`           | ❌ Delete, merge into `Schools`         | Redundant |
| `admin`             | ❌ Delete, merge into `Manager`         | Redundant. |
| `bishop_galvin`     | ❌ Delete, merge into `Schools`         | School-specific role now unified. |
| `bishopgalvin`      | ❌ Delete, merge into `Schools`         | Typo/redundant. |
| `coupon_manager`    | ❌ Delete                               | Functionality will be given to `administrator`. |
| `desk_duties`       | ❌ Delete, merge into `Desk`            | Redundant |
| `editor`            | ❌ Delete                               | Not applicable. |
| `guardian_temporary`| ❌ Delete                               | Handled via `guest`. |
| `instructors`       | ❌ Delete, merge into `Instructor`      | Redundant plural. |
| `manager`           | ❌ Delete, merge into `Manager`         | Overlapping with `pool_manager`. |
| `pool_administrator`| ❌ Delete, merge into `Manager`         | Redundant |
| `sh4_admin`         | ❌ Delete                               | Not relevant. |
| `shop_manager`      | ❌ Delete                               | Shop module likely deprecated. |
| `zion`              | ❌ Delete, merge into `Schools`         | Redundant |


## Updated Hierarchy Overview

```text
Superuser
  └── Manager
        └── Full Timer
                  ├── Desk
                  ├── Instructor
                  ├── Coupons
                        └── Customer
                        └── Guardian
                        └── Schools
            

