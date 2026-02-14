import unittest

from fastapi.routing import APIRoute

from app.main import app


class HealthContractTests(unittest.TestCase):
    def test_health_route_exists_with_get_method(self) -> None:
        health_route = next(
            (
                route
                for route in app.routes
                if isinstance(route, APIRoute) and route.path == "/health"
            ),
            None,
        )
        self.assertIsNotNone(health_route)
        self.assertIn("GET", health_route.methods)

    def test_health_route_returns_stable_payload(self) -> None:
        health_route = next(
            route
            for route in app.routes
            if isinstance(route, APIRoute) and route.path == "/health"
        )
        self.assertEqual(health_route.endpoint(), {"status": "ok"})
