import os
import random
import uuid
import string
from locust import HttpUser, task, between

# --- HARDCODE TOKENS HERE ---
# Paste your tokens here so you can just run 'locust'
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNzQ4NTQ1LCJpYXQiOjE3NzM3NDQ5NDUsImp0aSI6IjRmMzczYTQ3OTlhZjRlZDM4MjM5NzcwNGFiMWJmYzMyIiwidXNlcl9pZCI6Ijc3N2E3YThhLTY4NjQtNDVjMS05NzE3LTE5OTRkZWJiNTJiNyJ9.Cfj_uTRpwXfKqa8KIlu2yG7BUFKCLeXk6M4hmraNuME"
SUPER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNzQ4NTQ1LCJpYXQiOjE3NzM3NDQ5NDUsImp0aSI6IjA3YmMyNTU4MjFmZjQ1MzNiMjk3ODNiNzAyOGUzZmNmIiwidXNlcl9pZCI6ImRlZTQ2YjE1LTk2YTgtNDk5YS1iYWY4LTkzOGI3NjNkYmMwYSJ9.RZ0-Dw1YUBGvkFEs-JyciNqifKhYGDKIcKj8tQiWufI"
# ----------------------------

class FoodieUser(HttpUser):
    wait_time = between(1, 4)
    
    def on_start(self):
        """Called when a virtual user starts."""
        self.auth_token = AUTH_TOKEN if AUTH_TOKEN != "PASTE_TENANT_ADMIN_TOKEN_HERE" else os.getenv("LOCUST_AUTH_TOKEN")
        self.super_token = SUPER_TOKEN if SUPER_TOKEN != "PASTE_SUPERADMIN_TOKEN_HERE" else os.getenv("LOCUST_SUPERADMIN_TOKEN")
        
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        self.super_headers = {
            "Authorization": f"Bearer {self.super_token}",
            "Content-Type": "application/json"
        } if self.super_token else self.headers

        self.cuisine_ids = []
        self.fetch_initial_data()

    def fetch_initial_data(self):
        """Pre-fetch some IDs so we can do realistic writes."""
        # Fetch Cuisines
        response = self.client.get("/api/v1/cuisines/", headers=self.headers, name="Init: Fetch Cuisines")
        if response.status_code == 200:
            results = response.json().get("results", [])
            self.cuisine_ids = [c["id"] for c in results]

    @task(3)
    def view_cuisines(self):
        self.client.get("/api/v1/cuisines/", headers=self.headers, name="Read: List Cuisines")

    @task(1)
    def create_cuisine(self):
        """Test Write performance (POST) for Cuisines."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
        payload = {
            "name": f"New Cuisine {random_suffix}",
        }
        
        with self.client.post("/api/v1/cuisines/", json=payload, headers=self.headers, name="Write: Create Cuisine", catch_response=True) as response:
            if response.status_code == 201:
                new_id = response.json().get("id")
                if new_id:
                    self.cuisine_ids.append(new_id)
            else:
                response.failure(f"Failed to create cuisine: {response.status_code} - {response.text}")

    @task(1)
    def update_cuisine(self):
        """Test Update performance (PATCH) for Cuisines."""
        if not self.cuisine_ids:
            return
            
        cuisine_id = random.choice(self.cuisine_ids)
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
        payload = {
            "name": f"Updated Cuisine {random_suffix}"
        }
        with self.client.patch(f"/api/v1/cuisines/{cuisine_id}/", json=payload, headers=self.headers, name="Write: Patch Cuisine", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to patch cuisine: {response.status_code} - {response.text}")

    @task(5)
    def view_recipes(self):
        """Test Read performance (GET) for Recipes."""
        self.client.get("/api/v1/recipes/", headers=self.headers, name="Read: List Recipes")
