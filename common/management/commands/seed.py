from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = "Seed initial data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")

        admin, created = User.objects.get_or_create(
            email="praffulmali10@gmail.com",
            defaults={
                "first_name": "Prafful",
                "last_name": "Mali",
                "username": "Prafful",
                "role": "ADMIN",
                "is_active": True,
                "is_email_verified": True,
            },
        )

        if created:
            admin.set_password("Password123*")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Admin created"))
        else:
            self.stdout.write("Admin already exists")

        self.stdout.write(self.style.SUCCESS("Done"))
