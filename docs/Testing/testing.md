## Test Users

## Test Users

The following test users have been created using the `create_test_users` management command:

1. **Basic Public Swim User**
   - Email: public@acme.ie
   - Password: public1234
   - Groups: Customer
   - Access: Public swims only

2. **Guardian/Lessons User**
   - Email: guardian@acme.ie
   - Password: guardian1234
   - Groups: Customer, Guardian
   - Access: Public swims and ability to book lessons

3. **Bishop Galvin School**
   - Email: bishopgalvin@acme.ie
   - Password: bishopgalvin1234
   - Groups: Customer, bishopgalvin
   - Access: School-specific functionality

4. **Zion School**
   - Email: zion@acme.ie
   - Password: zion1234
   - Groups: Customer, zion
   - Access: School-specific functionality

To recreate these users at any time, run:
python manage.py create_test_users

The command is idempotent - it will not create duplicate users if they already exist.