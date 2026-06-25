import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the initial Django admin user."

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = os.environ.get("DJANGO_ADMIN_USERNAME", "admin")
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD")

        if not password:
            self.stdout.write(self.style.ERROR("DJANGO_ADMIN_PASSWORD is missing."))
            return

        user, created = User.objects.get_or_create(username=username)

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Admin ready: {username}"))