import factory
from django.contrib.auth import get_user_model
from tests.factories.tenants import TenantFactory

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    role = "USER"
    tenant = factory.SubFactory(TenantFactory)
    is_superadmin = False
    is_email_verified = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted if extracted else "testpass123"
        self.set_password(password)
        if create:
            self.save()
