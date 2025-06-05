## Models in lessons_booking/models.py

### Term
Represents a school term with:
- Start/end dates
- Booking and rebooking dates
- Assessment and creation timestamps
- Methods:
  - `get_current_term_id()`
  - `concatenated_term()`
  - `determine_phase()`

### LessonEnrollment
Represents a student's (swimling's) confirmed booking into a lesson:
- ForeignKeys: `Product`, `Swimling`, `Term`, `Order`
- Indexed by term, lesson, swimling

### LessonAssignment
Assigns instructors (Users in `instructors` group) to multiple lessons in a term.
You can generate this with AI later too — just copy and paste your models and ask for a docs/summary version.

Would you like me to generate a full models.md outline now based on your code?



