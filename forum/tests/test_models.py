from django.test import TestCase
from django.contrib.auth import get_user_model
from forum.models import Thread, Comment


class ModelsTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='modtest', password='testpass123')

    def test_thread_and_comment_creation(self):
        t = Thread.objects.create(title='Model Test', content='content', author=self.user)
        self.assertEqual(Thread.objects.count(), 1)
        c = Comment.objects.create(thread=t, author=self.user, content='nice')
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(str(t).find('Model Test') >= 0, True)
        self.assertEqual(str(c).find('Comment by') >= 0, True)
