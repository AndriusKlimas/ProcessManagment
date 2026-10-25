import uuid

from locust import HttpUser, between, task


class MusicAppUser(HttpUser):
    """Exercise the public and authenticated music-app flows."""

    wait_time = between(1, 3)

    def on_start(self):
        suffix = uuid.uuid4().hex[:10]
        self.username = f"locust_{suffix}"
        self.password = f"LoadTest-{suffix}!"

        self.client.get("/login-page", name="GET /login-page")
        response = self.client.post(
            "/signup",
            data={
                "username": self.username,
                "password": self.password,
                "confirm_password": self.password,
            },
            name="POST /signup",
            allow_redirects=True,
        )
        if response.status_code >= 400:
            self.environment.runner.quit()
            raise RuntimeError(
                f"Signup failed with HTTP {response.status_code} for {self.username}"
            )

        response = self.client.post(
            "/login",
            data={"username": self.username, "password": self.password},
            name="POST /login",
            allow_redirects=True,
        )
        if response.status_code >= 400:
            self.environment.runner.quit()
            raise RuntimeError(
                f"Login failed with HTTP {response.status_code} for {self.username}"
            )

    @task(5)
    def browse_catalog(self):
        self.client.get("/get-catalog", name="GET /get-catalog")

    @task(2)
    def view_history(self):
        self.client.get("/history-page", name="GET /history-page")

    @task(1)
    def view_product_page(self):
        self.client.get("/add-product-page", name="GET /add-product-page")

    @task(1)
    def logout_and_login(self):
        self.client.get("/logout", name="GET /logout")
        self.client.post(
            "/login",
            data={"username": self.username, "password": self.password},
            name="POST /login (repeat)",
            allow_redirects=True,
        )
