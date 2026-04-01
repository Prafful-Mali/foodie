import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodie.settings")
django.setup()

from tenants.models import Tenant

def cleanup_performance_test():
    print("🧹 Cleaning up Performance Test Data...")
    
    # Find tenants that starting with Perf-Test
    tenants = Tenant.objects.filter(name__startswith="Perf-Test")
    count = tenants.count()
    
    if count == 0:
        print("ℹ️ No performance test tenants found.")
        return

    for tenant in tenants:
        print(f"🗑️ Deleting Tenant and all its related data: {tenant.name}")
        # We perform a hard delete here for the test data to keep the DB clean
        tenant.delete() 

    print(f"✅ Successfully removed {count} test tenant(s). Your DB is clean!")

if __name__ == "__main__":
    cleanup_performance_test()
