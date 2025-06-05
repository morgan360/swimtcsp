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

#### Force Pull

## Fetch the latest changes from the remote repository

git fetch origin

## Discard local changes and forcefully reset to the state of the remote repository

git reset --hard origin/main


# Import\_Export

Note both schools and Lessons use the same categories and Programs. Load Programs before Categories