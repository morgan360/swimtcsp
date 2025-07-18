# Navigation Menu Structure

This document outlines the menu structure used in the custom navigation app.

---
## Exporting Menu(Navigation)  from localdb  to Deployment db

### From Local DB
- python manage.py dumpdata navigation.MenuGroup navigation.MenuItem --indent 2 > menu_export.json


### From DBeaver
- DELETE FROM `morganmck$swimtcsp`.navigation_menuitem_required_groups;
- DELETE FROM `morganmck$swimtcsp`.navigation_menuitem;
- DELETE FROM `morganmck$swimtcsp`.navigation_menugroup;

### Remote Terminal
- python manage.py loaddata menu_export.json



## 🌐 Public (Not Logged In)

**MenuGroup: `main`**

* Home (`/`)
* About
* Contact
* Timetable (URL: `swims:product_list`)

---

## 🔐 Customer (Logged In Basic User)

**MenuGroup: `main`**

* Public Swims

  * Book Swims (`swims:product_list`)

**MenuGroup: `profile`**

* Manage Profile
* View Orders
* Upgrade to Guardian

---

## 🧒 Guardian

**MenuGroup: `main`**

* Public Swims

  * Book Swim
* Swimling Panel
* Swimling Progress
* School Classes *(if in `schools` group)*

**MenuGroup: `profile`**

* Manage Profile
* View Orders
* Change Password
* Logout

---

## 🧰 Management (Pool Staff)

**MenuGroup: `management`**

* Move Swimmers Between Classes
* Order Management
* Booking Overview

---

## ⚙️ Administrator

**MenuGroup: `admin`**

* Add Lessons
* Change Prices
* Manage Lesson Settings
* Manage System Users

---

## 📊 Reporting (Senior Management)

**MenuGroup: `reporting`**

* Enrollment Reports
* Class Lists
* Term Summary
* Utilization Dashboard

---

## 📝 Notes

* `requires_login`, `requires_staff`, and `required_groups` are used to control visibility
* Menus will be rendered in a drawer layout using AlpineJS
* Each `MenuItem` should specify either `url_name` (preferred) or `external_url`
* Icons can be added using `icon_class` for FontAwesome compatibility
