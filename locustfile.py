import os
from locust import HttpUser, task, between

class FoodieUser(HttpUser):
    wait_time = between(1, 4)  # Simulate real user thinking time
    
    def on_start(self):
        """Called when a virtual user starts."""
        self.auth_token = os.getenv("LOCUST_AUTH_TOKEN")
        if not self.auth_token:
            print("❌ ERROR: LOCUST_AUTH_TOKEN not found in environment!")
        
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}"
        }

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
