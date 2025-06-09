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
### SWIMS APP
Products, Categories, Variants import
#### Shortcut
python manage.py sync_public_swims

### SWIMS_Orders APP
Swim Orders
#### Shortcut
python manage.py sync_swim_orders

### Schools APP
Models: 
1. ScoSchool(information about schools)
2. ScoCategory (beg, inter... etc.)
3. ScoLessons
#### Shortcut
python manage.py sync_schools