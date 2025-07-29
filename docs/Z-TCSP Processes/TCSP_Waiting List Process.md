# 🕰️ Waiting List Process – Customer & Administrator View

## 👨‍👩‍👧 Guardian Experience

When a lesson is fully booked, guardians(parents) are given the option to join the **Waiting List** via a **"Join 
Waiting 
List"** button on the lesson booking screen. Upon joining, they select which Swimling(swimmer) is being waitlisted 
for and which lesson. This entry is saved in the system and becomes visible on their **Swimling dashboard** under the 
**Waiting List Panel**.

Each waiting list entry includes:
- **Swimling Name**
- **Requested Lesson**
- **Assigned Lesson** (When  a space becomes available this is made available)
- **Actions**:
  - *Remove from Waiting List*
  - *Book Now* (if assigned to a lesso and notified of availability)

If an administrator assigns a space to a Swimling and marks them as *notified*, the **Book Now** button becomes 
available. Clicking the **Book Now** button redirects the guardian to the **lesson detail view**, where the lesson and 
Swimling are 
pre-selected and the guardian can book and pay for the lesson. If the lesson is not booked within 5 days of 
 notification, the entry will be removed.

Once the lesson is booked successfully, the waiting list entry is automatically marked as complete and removed from the dashboard to prevent clutter.

---

## 🧑‍💼 Administrator Experience

Administrators manage waiting list entries via the Django admin interface. Each entry can be:
- Reviewed by Swimling and product
- Assigned to an available lesson
- Marked as **notified**, where the guardian is sent an email and allows the guardian to book the swimling into the 
  lesson. Once Booked the record will be automatically marked as completed and no longer appear on the guardians 
  waiting list.

Admins can also **bulk notify** guardians using a custom admin action. The date of notification is recorded for auditing and follow-up.

The system enforces **uniqueness** for each `(swimling, lesson)` pair to prevent duplicate entries.

After a successful booking (e.g. via BoIPA), a post-payment process automatically marks the waiting list record as 
**complete**, removing it from the Swimling dashboard view.

---

This workflow ensures clarity for guardians, transparency in lesson demand, and effective space management for administrators.
