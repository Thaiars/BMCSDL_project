#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mini_forum.settings')
django.setup()

from forum.models import User

# Create moderator account
moderator, created = User.objects.get_or_create(
    username='moderator_test',
    defaults={
        'email': 'moderator@test.com',
        'first_name': 'Moderator',
        'last_name': 'Test',
        'role': 'moderator'
    }
)
if created:
    moderator.set_password('password123')
    moderator.save()
    print(f'✓ Created moderator account: {moderator.username}')
else:
    print(f'✓ Moderator account already exists: {moderator.username}')

# Create guest account
guest, created = User.objects.get_or_create(
    username='guest_test',
    defaults={
        'email': 'guest@test.com',
        'first_name': 'Guest',
        'last_name': 'Test',
        'role': 'guest'
    }
)
if created:
    guest.set_password('password123')
    guest.save()
    print(f'✓ Created guest account: {guest.username}')
else:
    print(f'✓ Guest account already exists: {guest.username}')

# Create admin account if needed
admin_user, created = User.objects.get_or_create(
    username='admin_test',
    defaults={
        'email': 'admin@test.com',
        'first_name': 'Admin',
        'last_name': 'Test',
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True
    }
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print(f'✓ Created admin account: {admin_user.username}')
else:
    print(f'✓ Admin account already exists: {admin_user.username}')

print('\n' + '='*60)
print('Test Accounts Summary:')
print('='*60)
print('Role      | Username         | Password     | Email')
print('-'*60)
print('Guest     | guest_test       | password123  | guest@test.com')
print('Moderator | moderator_test   | password123  | moderator@test.com')
print('Admin     | admin_test       | admin123     | admin@test.com')
print('='*60)
