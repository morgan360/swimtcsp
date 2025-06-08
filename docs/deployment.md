# deploying\_site

#### Freeze Reuirements

pip freeze > requirements.txt

#### Force Push

* git push -f origin main
* \

* pip install -r requirements.txt
* workon swimtcsp

#### Discard changes to local files

git checkout -- core/asgi.py core/wsgi.py manage.py

To quit and save from bash terminal :wq

git stash clear

[Pythonanywher Set Variables](https://help.pythonanywhere.com/pages/environment-variables-for-web-apps/)
## In Bash
1. cd swimtcsp
2. git pull (git merge origin/main)
3. workon swimtcsp
4. pip install -r requirements.txt
5. python manage.py collectstatic
6. wget -qO- https://whatsmyip.ie | grep IP #gets IP of pythonanywhere
7. python3 test_connection.py (connection test: mac and pythonanywhere)


#### Force Pull

## Fetch the latest changes from the remote repository

git fetch origin

## Discard local changes and forcefully reset to the state of the remote repository

git reset --hard origin/main


# Import\_Export

Note both schools and Lessons use the same categories and Programs. Load Programs before Categories
## Current Process
Next I want to do a similar process, that is importing all the users directly from the remote database, after making 
changes to various fields. These changes are curreltly carried out during the following process.
users Then  I want to export the database model to users.sql file and then create an import users for the deployment 
site. 
The process at the moment it is a complex process involving the following steps:
1. I have an Jupyter Notebok cell which extracts all user data and puts it into a file users.csv.
2. Then another cell (Updated Version for Batch) is run to deserilise the roles into a field Groups comma separated 
   format  
   and 
   saves the users into four csv files,
   so they can be imported in batches.
3. Then from inside my project webapp I import (using import/export) each of the four csv files into my user model.
 Note: when Importing users if a Group does not exist then it is created

I want to streamline this process what info do you need.

## MySql Dump
1. Import Data directly into local DB
2. export as an sql file
3. git push
4. Git pull
5. import into Python Anywhere DB
### Export terms from Mac
mysqldump -u swimuser -p'StrongPass!2025' --no-tablespaces swimtcsp lessons_bookings_term > exported_sql/mor_terms.sql
#### Shortcut
python manage.py export_terms_sql
### Import to Pythonanywhere
mysql -u morganmck -p'Mongo@8899' -h morganmck.mysql.eu.pythonanywhere-services.com morganmck\$swimtcsp < import_sql/mor_terms.sql
#### Shortcut
python manage.py import_terms_sql

## Importing and exporting users/swimlings Data
Note: these scripts are stored in users/managment/commands. To be done in order.
### Syncing users From TCSP
#### Shortcuts
1. python manage.py sync_users_from_remote
2. python manage.py import_swimlings_remote

### Exporting Users
#### Shortcuts
1. python manage.py export_users_sql
2. python manage.py export_swimlings_sql
### Importing Swimlings on Pythonanywhere
#### Shortcuts
1. python manage.py import_users_sq
2. python manage.py import_swimlings_sql

## Importing and exporting lessons Data
This handles all three models together programs, categories, products
#### Shortcuts
1. python manage.py import_lessons_remote (Works Locally as well as remotly)
2. python manage.py export_lessons_sql (Might not be necessary)
#### Shortcuts
1. 
## _Importing  lessons_bookings Data_
1. python manage.py import_lessons_bookings_remote 
## Public Swims
The origional notebook is Swim TCSP Import CSVs.ipynb
### Direction for ChatGPT
Now I want to sync data from remote DB for Public Swims. First we will import the swims imformation in the app swims.
There are three models:
1. PublicSwimCategory, (name = models.CharField(max_length=100, null=True)
    slug = models.SlugField(max_length=200,
                            unique=True)
    description = models.TextField(blank=True))
2. PublicSwimProduct, (name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PublicSwimCategory, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, blank=True)
    start_time = models.TimeField(blank=True)
    end_time = models.TimeField(blank=True)
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    num_places = models.IntegerField(null=True)
    available = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True))
3. PriceVariant. (class PriceVariant(models.Model):
    VARIANT_CHOICES = [
        ('Adult', 'Adult'),
        ('Child', 'Child'),
        ('OAP', 'OAP'),
        ('Student', 'Student'),
        ('Infant', 'Infant'),
    ]
    product = models.ForeignKey(PublicSwimProduct, on_delete=models.CASCADE,
                                related_name='price_variants')
    variant = models.CharField(max_length=10, choices=VARIANT_CHOICES,
                               blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, ))
There are three tables involved at the 
remote DB: 
1. mor_events (id, event)
2. mor_sessions_generic (`id`, `day_id`, `event_id`, `num_places`, `time_start`, `time_end`, `notes`, `active` )
3. mor_generic_bookings (`wc_order_id as id`, `customer_id as user_id`, `session_id as product_id`, `session_date as booking`, `wc_order_id as stripe_id` (duplicate alias))
4. mor_generic_bookings (wc_order_id as id`, `num_adults`, `num_children`, `num_senior`, `num_under3`)

### SWIMS APP