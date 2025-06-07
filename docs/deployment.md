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

## MySql Dump
### Export from Mac
mysqldump -u swimuser -p'StrongPass!2025' --no-tablespaces swimtcsp lessons_bookings_term > import_sql/mor_terms.sql
### Import to Pythonanywhere
mysql -u morganmck -p'Mongo@8899' -h morganmck.mysql.eu.pythonanywhere-services.com morganmck\$swimtcsp < import_sql/mor_terms.sql



