import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mini_forum.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from forum.models import Thread, Comment
User = get_user_model()
username='tester'
password='testpass123'
if not User.objects.filter(username=username).exists():
    User.objects.create_user(username=username,password=password)
client=Client()
login_ok=client.login(username=username,password=password)
print('login_ok=',login_ok)
resp=client.post('/threads/create/', {'title':'Test Thread','content':'This is a test.'})
print('create status_code=',resp.status_code)
t=Thread.objects.filter(title='Test Thread').first()
print('thread exists=',bool(t))
if t:
    resp2=client.post(f'/threads/{t.id}/', {'content':'Nice thread'})
    print('comment post status_code=',resp2.status_code)
    c=Comment.objects.filter(thread=t, content='Nice thread').first()
    print('comment exists=',bool(c))
