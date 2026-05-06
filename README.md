# mini_forum

Minimal Django-based discussion forum for quick development and testing.

Run locally (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run locally (Linux CLi):

```linux
python -m venv .venv
source .venv\bin\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```


Open http://127.0.0.1:8000/ to view the forum. Admin is at http://127.0.0.1:8000/admin/

This project uses SQLite by default and a very small model set: `User`, `Thread`, `Comment`, `Report`, and `ActivityLog`.
