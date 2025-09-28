# Live DB Backup
Every night the live db is synced with the dev and the data is saved to PythonAnywhere(PA) drive **'db_backups'**. Thre 
is a seven day rolling backup kept.
The script for backupd is **'sync_db.sh'**