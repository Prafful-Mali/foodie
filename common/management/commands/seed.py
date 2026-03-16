import os
from django.core.management.base import BaseCommand
from users.models import User
from common.enums import UserRole


class Command(BaseCommand):
    help = "Seed initial data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")

        email = os.getenv("SUPERADMIN_EMAIL")
        password = os.getenv("SUPERADMIN_PASSWORD")

        if not email or not password:
            self.stdout.write(
                self.style.ERROR(
                    "SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must be set in environment"
                )
            )
            return

        admin, created = User.objects.get_or_create(
            email=email,
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
            admin.set_password(password)
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f"Superadmin created with email: {email}")
            )
        else:
            self.stdout.write(f"Superadmin with email {email} already exists")

        self.stdout.write(self.style.SUCCESS("Done"))
