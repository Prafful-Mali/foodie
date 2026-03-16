import os
from locust import HttpUser, task, between

# --- HARDCODE TOKENS HERE ---
# Paste your tokens here so you can just run 'locust'
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNjg4MDA2LCJpYXQiOjE3NzM2ODQ0MDYsImp0aSI6IjMyMDFjMDczZDQ1ZjQ2OGY5Y2IyMWQxZTZkMDEyODFiIiwidXNlcl9pZCI6Ijg1MDAxZDExLWYwN2EtNDYxNi04YjUxLTk1YjJmYmUxYzY1MCJ9.GeIKuWYLgiv8iE0cfD6oQ6jNnO9tibxZOY9gAC6yCk0"
SUPER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNjg4MDA2LCJpYXQiOjE3NzM2ODQ0MDYsImp0aSI6IjYyYzU4Mjc3NTk5YTQwYzA4Yjk1Y2NlMGY0NjA4MjM1IiwidXNlcl9pZCI6ImRlZTQ2YjE1LTk2YTgtNDk5YS1iYWY4LTkzOGI3NjNkYmMwYSJ9.n9BYnrRApiULgfRtQVCSKGDhBp64Ww92UPCePRMbceY"
# ----------------------------

class FoodieUser(HttpUser):
    wait_time = between(1, 4)  # Simulate real user thinking time
    
    def on_start(self):
        """Called when a virtual user starts."""
        # Use hardcoded tokens first, fallback to environment variables
        self.auth_token = AUTH_TOKEN if AUTH_TOKEN != "PASTE_TENANT_ADMIN_TOKEN_HERE" else os.getenv("LOCUST_AUTH_TOKEN")
        self.super_token = SUPER_TOKEN if SUPER_TOKEN != "PASTE_SUPERADMIN_TOKEN_HERE" else os.getenv("LOCUST_SUPERADMIN_TOKEN")
        
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}"
        }
        self.super_headers = {
            "Authorization": f"Bearer {self.super_token}"
        } if self.super_token else self.headers

    @task(3)
    def view_recipes(self):
        """Simulate browsing the recipe list (Optimized with select_related/only)."""
        self.client.get("/api/v1/recipes/", headers=self.headers, name="List Recipes")

    @task(2)
    def view_users(self):
        """Simulate an admin checking the user list (Optimized with only)."""
        self.client.get("/api/v1/users/", headers=self.headers, name="List Users")

    @task(2)
    def view_ingredients(self):
        """Simulate browsing ingredients."""
        self.client.get("/api/v1/ingredients/", headers=self.headers, name="List Ingredients")

    @task(1)
    def view_cuisines(self):
        """Simulate browsing cuisines."""
        self.client.get("/api/v1/cuisines/", headers=self.headers, name="List Cuisines")

    @task(2)
    def view_orders(self):
        """Simulate a tenant admin checking their subscription orders."""
        self.client.get("/api/v1/orders/", headers=self.headers, name="List Orders")

    @task(1)
    def view_payment_history(self):
        """Simulate checking payment history (Requires SuperAdmin)."""
        self.client.get("/api/v1/payments/", headers=self.super_headers, name="List Payments")
