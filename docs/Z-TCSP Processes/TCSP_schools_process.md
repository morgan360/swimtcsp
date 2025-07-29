## School Process
### Schools
- A list of all the schools that MAY participate in the schools program is stored in the app **schools** and model
(table) **
ScoSchools**. 
- Each school is identified by the field  **sco_role_num**.
- ScoLessons holds the list of lessons. Lessons are related to the school id in ScoSchools. Lessons may be active or 
  not. 
- Terms are defined in the app schools_bookings. Each term is associated with a particular school through 
  ScoSchool id 
  Only when terms are made active is enrollment possible.
### Guardians
- Only Guardians that have signed up to the schools program will see the the school panel in the Swimlings panel. 
- Signing up to the schools program is done via User Profile and is only available to guardians, then the profile 
  school is added to their profile. In order to see this option they have to 
  be registered as a guardian first.
- Once a guradian is registered for the schools program they must add the sco_role_number to the swimling profile, 
  before they will have access to the Schools panel. If the term for that swimling's school is active then they will 
  be able to book a lesson for that term. There is no rebooking for schools and booking remains open until the end 
  of the term and and if the terms is active.
### Administration (Admin/Schools Admin)
The schools administrations tables are availiable to 
- is_staff
- administrator
From her an administrator can carry out the following tasks:
- create/delete lessons
- set prices
- create terms per school
- Activate/deactive a term for booking
- **Note** Terms will be no longer shown after their end_date wether active or not.
- Orders and enrolments can be seen here. 

### Notes
Guardian need not register school in order to become part of the schools program. They only need to Update to schools program under their profile. Then they will be allocated the roles schools. If the swimling has a correct sch_role_number then they will be included I the schools panel which will show the name of the student and if they have been registered for the active term for that school. If not they will be presented with a book now button (or if no active term then No active term will be displayed. The swimling will only be able to book into one lesson per term. If there are two active terms then only the latest one is made available. The information about schools is only available I the administration area.

- ScoLessons are generic and used for every term(They are set to active if actually available) and they are also identified by school
## Files used in checkout
schools_bookings/views
direct_order.html
