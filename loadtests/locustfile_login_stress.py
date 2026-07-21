# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Locust load test that stress-tests the login endpoint in isolation.
# First Written on: Wednesday, 15-Jul-2026
# Edited on: Wednesday, 15-Jul-2026

"""Isolated scenario: hammer /auth/login only.

Why a separate file: login is the one endpoint that does CPU-bound Argon2
password hashing (see app/src/core/security.py) on every single call, unlike
read endpoints which are mostly waiting on MongoDB I/O. Running this alone
(not mixed with the other scenario) makes it easy to see where the app's
throughput ceiling actually comes from - Gunicorn worker count / CPU, not
the database.

Usage:
    locust -f loadtests/locustfile_login_stress.py --host http://localhost:80
"""

import uuid

from locust import HttpUser, between, task

PASSWORD = 'LoadTest123!'


class LoginStormUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        self.email = f'loginstorm_{uuid.uuid4().hex}@example.com'

        self.client.post(
            '/api/v1/auth/register',
            json={'name': 'Login Storm', 'email': self.email, 'password': PASSWORD},
            name='/auth/register (setup)',
        )

    @task
    def login(self) -> None:
        self.client.post(
            '/api/v1/auth/login',
            json={'email': self.email, 'password': PASSWORD},
            name='/auth/login',
        )
