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


# from users.models import User
# from tenants.models import Tenant
# from users.enums import UserRole

# tenant = Tenant.objects.get(id="67d065c1-911d-4871-9e3b-dfff0fb33ad1")

# user, created = User.objects.get_or_create(
#     email="praffulmali10@gmail.com",
#     defaults={
#         "username": "praffulmali10",
#         "first_name": "Prafful",
#         "last_name": "Mali",
#         "role": UserRole.ADMIN,
#         "tenant": tenant,
#         "is_active": True,
#         "is_email_verified": True,
#     },
# )

# if created:
#     user.set_password("Password123*")
#     user.save()
#     print("Tenant admin created")
# else:
#     # Ensure it is an admin of this tenant
#     user.role = UserRole.ADMIN
#     user.tenant = tenant
#     user.is_active = True
#     user.is_email_verified = True
#     user.save()
#     print("User updated as tenant admin")
