import uuid
from django.db import models
from common.models import BaseModel


class Tenant(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_default=True)
    is_premium = models.BooleanField(default=False, db_default=False)

    def __str__(self):
        return self.name
