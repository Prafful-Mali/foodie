import os
import random
import uuid
import string
from locust import HttpUser, task, between

def get_token():
    try:
        with open(".perf_token", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv("LOCUST_AUTH_TOKEN", "PASTE_TENANT_ADMIN_TOKEN_HERE")

AUTH_TOKEN = get_token()

class FoodieUser(HttpUser):
    wait_time = between(1, 4)
    
    def on_start(self):
        """Called when a virtual user starts."""
        self.auth_token = AUTH_TOKEN
        
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

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

    @task(3)
    def view_recipes(self):
        """Test Read performance (GET) for Recipes."""
        self.client.get("/api/v1/recipes/", headers=self.headers, name="Read: List Recipes")
