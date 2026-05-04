from django.test import TestCase, Client
from django.test.utils import template_rendered
from django.test.client import store_rendered_templates

# Prevent Django test client from copying template Context objects (avoids
# AttributeError with certain Python/Django combinations when copying).
try:
    template_rendered.disconnect(store_rendered_templates)
except Exception:
    pass
from django.urls import reverse
from django.contrib.auth import get_user_model
from forum.models import Thread


class ViewsTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='viewtest', password='testpass123')
        self.client = Client()
        # Prevent template_rendered signal from attempting to copy Context objects
        # which can fail under certain Python/Django combinations in the test harness.
        try:
            template_rendered.send = lambda *a, **k: None
        except Exception:
            pass

    def test_index_view(self):
        # index should be reachable
        resp = self.client.get(reverse('forum:index'))
        self.assertEqual(resp.status_code, 200)

    def test_create_thread_requires_login(self):
        resp = self.client.get(reverse('forum:create_thread'))
        # should redirect to login
        self.assertEqual(resp.status_code, 302)

    def test_create_thread_post(self):
        self.client.login(username='viewtest', password='testpass123')
        resp = self.client.post(reverse('forum:create_thread'), {'title': 'View Test', 'content': 'x'})
        # after creation should redirect to index
        self.assertEqual(resp.status_code, 302)
        t = Thread.objects.filter(title='View Test').first()
        self.assertIsNotNone(t)
