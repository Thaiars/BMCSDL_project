import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'mini_forum.settings'
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT @@SERVERNAME, @@SERVICENAME, SERVERPROPERTY('InstanceName'), SERVERPROPERTY('ServerName')")
row = cursor.fetchone()
print(f"@@SERVERNAME      : {row[0]}")
print(f"@@SERVICENAME     : {row[1]}")
print(f"InstanceName      : {row[2]}")
print(f"ServerName        : {row[3]}")
