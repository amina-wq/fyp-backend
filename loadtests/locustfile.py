"""Load test simulating realistic FoodTrack usage: many users browsing/managing inventory.

Run against a real running stack (e.g. docker-compose.dev.yaml), never against
production data - this test creates real users and inventory items.

Usage:
    pip install -r requirements.dev.txt
    locust -f loadtests/locustfile.py --host http://localhost:80

Then open http://localhost:8089, set the number of users + spawn rate, and start.

For a scripted/headless run (good for capturing evidence for a report):
    locust -f loadtests/locustfile.py --host http://localhost:80 \
        --headless -u 200 -r 20 -t 3m --csv=loadtests/results/run1 --html=loadtests/results/run1.html
"""

import uuid
from datetime import date, timedelta

from locust import HttpUser, between, task

PASSWORD = 'LoadTest123!'


class FoodTrackUser(HttpUser):
    """One simulated app user: registers once, then repeatedly uses inventory/categories."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = f'loadtest_{uuid.uuid4().hex}@example.com'

        response = self.client.post(
            '/api/v1/auth/register',
            json={'name': 'Load Test User', 'email': email, 'password': PASSWORD},
            name='/auth/register',
        )
        response.raise_for_status()

        self.access_token = response.json()['access_token']
        self.headers = {'Authorization': f'Bearer {self.access_token}'}

        categories_response = self.client.get(
            '/api/v1/categories',
            headers=self.headers,
            name='/categories',
        )
        categories = categories_response.json()
        self.category_id = categories[0]['id'] if categories else None

    @task(5)
    def list_inventory(self) -> None:
        self.client.get('/api/v1/inventory', headers=self.headers, name='/inventory [list]')

    @task(3)
    def inventory_stats(self) -> None:
        self.client.get('/api/v1/inventory/stats', headers=self.headers, name='/inventory/stats')

    @task(2)
    def create_inventory_item(self) -> None:
        if not self.category_id:
            return

        payload = {
            'custom_name': f'Item-{uuid.uuid4().hex[:6]}',
            'category_id': self.category_id,
            'location': 'fridge',
            'amount': 1,
            'unit': 'pcs',
            'expiration_date': (date.today() + timedelta(days=7)).isoformat(),
        }

        self.client.post(
            '/api/v1/inventory',
            json=payload,
            headers=self.headers,
            name='/inventory [create]',
        )

    @task(2)
    def list_categories(self) -> None:
        self.client.get('/api/v1/categories', headers=self.headers, name='/categories')

    @task(1)
    def get_me(self) -> None:
        self.client.get('/api/v1/auth/me', headers=self.headers, name='/auth/me')

    # NOTE: /recipes and /storage/recommendations are intentionally left out of the
    # mixed scenario above - they call real paid/rate-limited third-party APIs
    # (Spoonacular, Gemini). Load-testing them here would either burn your API
    # quota or, with empty API keys (as in the test/dev env), just measure how
    # fast the app returns 502s - not a meaningful number. Test those separately,
    # deliberately, with a real key and low concurrency (see the README section
    # below on why).
