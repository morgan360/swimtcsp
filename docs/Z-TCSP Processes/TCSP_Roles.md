# 🧑‍💻 TCSP System Roles – Consolidation & Redesign Plan

This document outlines the current system roles, plans for consolidation, and future role strategy including access levels for staff, schools, guardians, and ownership.

---

## ✅ NEW ROLES (aka Groups)

The following is a list of that will be used for the new website. Some are carried over, but most are new. 
*Note: Capitalisation is important.*

| Role Name       | Purpose                                                                 | Role Status |
|-----------------|-------------------------------------------------------------------------|-------------|
| `Customer` | Default for every user. Can view and book public swims. | 🔁 Reuse |
| `Guardian` | Can add swimlings to their account and book into term-based lessons. Must be a customer first. | ✅ New |
| `schools` | Can book into schools lessons. Must be a Guardian first. | 🔁 Reuse |
| `Desk` | Can access existing user information. Can edit existing user information. Can view public swims management panel (cannot edit swims or add new swims). Can access lessons list and view class history. Can view isntructor assignments but not assign. Have full control over the swimlings panel and can move swimlings to/from classes. Can view enrollment stats. Can print class lists. Can view term information. Cannot access schools management panel. Can access orders dashboard. Cannot see the Management or Coupons panels. | ✅ New |
| `instructor` | Can view the instructor dashboard in the main menu. Can view their assigned lessons. Can evaluate the students' skills. Can take attendance. Can view their class list. | ✅ New |
| `Full-Timer` | Have all the capabilities of desk staff. Cannot change user groups/permissions. Cannot do refunds. Cannot view financial reports. Can add/remove/alter public swim and lesson details. | ✅ New |
| `Manager` | Full access to all admin panels and can add/remove/view/change all products. Can assign user roles/groups. | ✅ New |
| `Coupons` | Can issue coupons. This is an additional role - must be Desk/Manager first.| ✅ New |
| `ex-staff` | Former staff members. | 🔁 Reuse |


## Proposed Actions for Old Roles


| Role Name           |Action|Reason|
|---------------------|-----------------------------------------|------------------------------------------------|
| `administrator`     | ❌ Delete, merge into `Manager`         | Redundant. Use `Manager`.|
| `bbp_blocked`       | ⚠️ TBD                                  | Unsure if needed. |
| `Customer`          | ✅ Keep and reuse                       |  |
| `ex-staff`          | ✅ Keep and reuse                       |  |
| `guardian`          | ❌ Delete, merge into `Guardian`        | Update for clarity. |
| `guest`             | ❌ Delete                               | Unsure if needed. |
| `instructor`        | ✅ Keep and reuse                       | Redundant lower case version. |
| `pool_manager`      | ❌ Delete, merge into `Manager`         | Redundant. |
| `schools`           | ✅ Keep and reuse                       |  |
| `admin`             | ❌ Delete, merge into `Manager`         | Redundant. |
| `bishop_galvin`     | ❌ Delete, merge into `Schools`         | School-specific role now unified. |
| `bishopgalvin`      | ❌ Delete, merge into `Schools`         | Typo/redundant. |
| `coupon_manager`    | ❌ Delete, merge into `Coupons`         | Functionality will be given to `administrator`. |
| `desk_duties`       | ❌ Delete, merge into `Desk`            | Redundant |
| `editor`            | ❌ Delete                               | Not applicable. |
| `guardian_temporary`| ❌ Delete                               | Handled via `guest`. |
| `instructors`       | ❌ Delete, merge into `instructor`      | Redundant plural. |
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
            

