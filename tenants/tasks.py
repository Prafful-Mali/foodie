import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from tenants.models import Tenant
from users.models import User
from recipes.models import Cuisine, Ingredient, Recipe, RecipeIngredient
from payments.models import Subscription, Payment

logger = logging.getLogger(__name__)


@shared_task
def soft_delete_tenant_related_data(tenant_id, deleted_at_timestamp):
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        deleted_at = timezone.datetime.fromisoformat(deleted_at_timestamp)

        with transaction.atomic():
            User.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

            Cuisine.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

            Ingredient.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

            RecipeIngredient.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

            Recipe.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

            Payment.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

            Subscription.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, deleted_at=deleted_at
            )

        logger.info(
            f"Successfully soft deleted tenant {tenant_id} and all related data"
        )

        return {
            "tenant_id": str(tenant_id),
            "message": "Tenant and all related data soft deleted successfully",
        }

    except Exception as e:
        logger.error(
            f"Soft delete failed for tenant {tenant_id}: {str(e)}", exc_info=True
        )

        return {"status": "error", "tenant_id": str(tenant_id), "message": str(e)}


@shared_task
def restore_tenant_related_data(tenant_id, deleted_at_timestamp):
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        deleted_at = timezone.datetime.fromisoformat(deleted_at_timestamp)

        with transaction.atomic():
            User.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

            Cuisine.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

            Ingredient.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

            RecipeIngredient.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

            Recipe.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

            Payment.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

            Subscription.objects.filter(
                tenant=tenant, is_active=False, deleted_at=deleted_at
            ).update(is_active=True, deleted_at=None)

        logger.info(f"Successfully restored tenant {tenant_id} and all related data")

        return {
            "tenant_id": str(tenant_id),
            "message": "Tenant and all related data restored successfully",
        }

    except Exception as e:
        logger.error(f"Restore failed for tenant {tenant_id}: {str(e)}", exc_info=True)

        return {"status": "error", "tenant_id": str(tenant_id), "message": str(e)}
