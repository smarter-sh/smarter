"""
Test the views that the api's test urls serve, :mod:`smarter.apps.api.v1.tests.views.test_views`.

These views give other tests, and the cli's tests, fixed responses for authenticated and
unauthenticated requests.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.api.v1.tests.urls import ApiV1TestUrls
from smarter.apps.api.v1.tests.views.test_views import (
    FauxDictSerializer,
    faux_dict,
    faux_list,
)


class TestTestViews(ApiV1TestBase):
    """Get and post each test url, unauthenticated and with the test user's api key."""

    def url(self, name: str) -> str:
        return reverse(ApiV1TestUrls.namespace + name)

    def test_unauthenticated(self):
        client = Client()
        self.assertEqual(client.get(self.url(ApiV1TestUrls.UNAUTHENTICATED_DICT)).json(), faux_dict)
        self.assertEqual(client.get(self.url(ApiV1TestUrls.UNAUTHENTICATED_LIST)).json(), faux_list)
        for name in (ApiV1TestUrls.UNAUTHENTICATED_DICT, ApiV1TestUrls.UNAUTHENTICATED_LIST):
            with self.subTest(name=name):
                response = client.post(self.url(name), data={"a": 1}, content_type="application/json")
                self.assertEqual(response.json(), {"a": 1})

    def test_authenticated(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_key}")
        self.assertEqual(client.get(self.url(ApiV1TestUrls.AUTHENTICATED_DICT)).json(), faux_dict)
        self.assertEqual(client.get(self.url(ApiV1TestUrls.AUTHENTICATED_LIST)).json(), faux_list)
        for name in (ApiV1TestUrls.AUTHENTICATED_DICT, ApiV1TestUrls.AUTHENTICATED_LIST):
            with self.subTest(name=name):
                response = client.post(self.url(name), data={"a": 1}, format="json")
                self.assertEqual(response.json(), {"a": 1})

    def test_serializer(self):
        serializer = FauxDictSerializer(data={"id": 1, **faux_dict})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save()["id"], 1)
        instance = {"id": 1, **faux_dict}
        self.assertEqual(serializer.update(instance, {"status": "updated"})["status"], "updated")

    def test_course_catalogue(self):
        """Test that the course catalogue is filtered by course id, cost and description."""
        client = Client()
        url = self.url(ApiV1TestUrls.STACKADEMY_COURSE_CATALOGUE)
        courses = client.get(url).json()
        self.assertTrue(courses)
        self.assertEqual(len(client.get(url, {"course_id": courses[0]["course_id"]}).json()), 1)
        self.assertTrue(all(c["cost"] <= 100 for c in client.get(url, {"max_cost": "100"}).json()))
        client.get(url, {"course_id": "x", "max_cost": "y", "description": "python"})
        self.assertEqual(client.post(url, data={"a": 1}, content_type="application/json").json(), {"a": 1})
