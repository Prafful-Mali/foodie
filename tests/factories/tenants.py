import factory
from tenants.models import Tenant


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Faker("company")
    is_active = True
    is_premium = False
