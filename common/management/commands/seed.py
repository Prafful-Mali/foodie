from django.core.management.base import BaseCommand
from users.models import User
from users.enums import UserRole


class Command(BaseCommand):
    help = "Seed initial data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")

        admin, created = User.objects.get_or_create(
            email="praffulmali7@gmail.com",
            defaults={
                "first_name": "Prafful",
                "last_name": "Mali",
                "username": "prafful",
                "role": UserRole.SUPERADMIN,
                "is_superadmin": True,
                "is_active": True,
                "is_email_verified": True,
                "tenant": None,
            },
        )

        if created:
            admin.set_password("Password123*")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Superadmin created"))
        else:
            self.stdout.write("Superadmin already exists")

        self.stdout.write(self.style.SUCCESS("Done"))
