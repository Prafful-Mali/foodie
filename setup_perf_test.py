import os
import django
import uuid
import sys
from django.utils import timezone

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodie.settings")
django.setup()

from tenants.models import Tenant
from users.models import User
from recipes.models import Cuisine, Ingredient, Recipe, RecipeIngredient
from payments.models import Subscription, Payment
from common.enums import UserRole, SubscriptionStatus, PaymentStatus
from rest_framework_simplejwt.tokens import RefreshToken
from faker import Faker

fake = Faker()

def setup_performance_test():
    print("Setting up Performance Test Data...")
    
    # 1. Create Tenant
    tenant_name = f"Perf-Test-{uuid.uuid4().hex[:6]}"
    tenant = Tenant.objects.create(name=tenant_name, is_premium=True)
    print(f"Created Tenant: {tenant_name}")

    # 2. Create Admin (used for Tenant Admin Token)
    admin_email = f"admin@{tenant_name.lower()}.com"
    admin = User.objects.create(
        email=admin_email,
        username=f"admin_{uuid.uuid4().hex[:4]}",
        role=UserRole.ADMIN,
        tenant=tenant,
        is_email_verified=True,
        is_active=True,
        is_superadmin=False
    )
    admin.set_password("password123")
    admin.save()
    print(f"Created Admin: {admin_email}")

    # 3. Create Users
    print("Seeding 10 Users...")
    for _ in range(10):
        User.objects.create(
            email=fake.email(),
            username=fake.user_name() + uuid.uuid4().hex[:4],
            role=UserRole.USER,
            tenant=tenant,
            is_email_verified=True,
            is_active=True
        )

    # 4. Create Cuisines & Ingredients
    cuisine = Cuisine.objects.create(name="Performance Cuisine", tenant=tenant)
    ingredients = []
    for _ in range(10):
        ingredients.append(Ingredient.objects.create(name=fake.word() + f"_{uuid.uuid4().hex[:4]}", tenant=tenant))

    # 5. Create Recipes
    print("⏳ Seeding 50 Recipes...")
    for _ in range(50):
        recipe = Recipe.objects.create(
            name=fake.sentence(nb_words=3) + f"_{uuid.uuid4().hex[:4]}",
            description=fake.paragraph(),
            preparation_steps=fake.text(),
            cooking_time=fake.random_int(min=5, max=120),
            sharing_status="PUBLIC",
            tenant=tenant,
            user=admin,
            cuisine=cuisine
        )
        # Add random ingredients (ensuring uniqueness)
        selected_ingredients = fake.random_elements(elements=ingredients, length=3, unique=True)
        for ingredient in selected_ingredients:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                tenant=tenant,
                quantity="1.0",
                unit="unit"
            )

    # 6. Create Payments & Subscriptions
    print(" Seeding 20 Subscriptions & Payments...")
    for _ in range(20):
        sub = Subscription.objects.create(
            tenant=tenant,
            created_by=admin,
            amount=49900,
            status=SubscriptionStatus.PAID,
            activated_at=timezone.now()
        )
        Payment.objects.create(
            tenant=tenant,
            subscription=sub,
            user=admin,
            order_id=f"order_{uuid.uuid4().hex[:8]}",
            payment_id=f"pay_{uuid.uuid4().hex[:8]}",
            amount=49900,
            status=PaymentStatus.CAPTURED,
            captured=True
        )

    # 7. Generate Token
    # Token 1: Tenant Admin (for Recipes/Users/Cuisines)
    tenant_admin_refresh = RefreshToken.for_user(admin)
    tenant_admin_token = str(tenant_admin_refresh.access_token)
    
    # Store token in a file for Locust to read automatically
    with open(".perf_token", "w") as f:
        f.write(tenant_admin_token)

    print("\n" + "="*50)
    print(f"STRESS TEST ADMIN TOKEN:")
    print(f"{tenant_admin_token}")
    print("="*50)
    print(f"\n✅ Token saved to .perf_token")
    print("Setup Complete! Run Locust now.")

if __name__ == "__main__":
    setup_performance_test()
