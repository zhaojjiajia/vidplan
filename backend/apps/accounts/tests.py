from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AccountsAPITests(APITestCase):
    def test_register_login_refresh_and_me(self):
        register_resp = self.client.post(
            "/api/v1/auth/register/",
            {"username": "alice", "password": "password123", "nickname": "阿丽"},
            format="json",
        )

        self.assertEqual(register_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(register_resp.data["username"], "alice")
        self.assertEqual(register_resp.data["nickname"], "阿丽")
        self.assertNotIn("password", register_resp.data)
        user = User.objects.get(username="alice")
        self.assertTrue(user.check_password("password123"))

        login_resp = self.client.post(
            "/api/v1/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_resp.data)
        self.assertIn("refresh", login_resp.data)

        me_resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        me_resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data["username"], "alice")

        refresh_resp = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh": login_resp.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_resp.data)

    def test_register_rejects_short_password(self):
        resp = self.client.post(
            "/api/v1/auth/register/",
            {"username": "short", "password": "123", "nickname": ""},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.data)
