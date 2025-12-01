from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'testuser@example.com',
            'username': 'testuser',
            'password': 'testpassword123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.login_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')

    def test_obtain_token_pair(self):
        """
        Ensure we can obtain a token pair with valid credentials.
        """
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_obtain_token_invalid_credentials(self):
        """
        Ensure we cannot obtain a token pair with invalid credentials.
        """
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': 'wrongpassword'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """
        Ensure we can refresh an access token using a valid refresh token.
        """
        # First obtain a token pair
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }, format='json')
        
        refresh_token = login_response.data['refresh']
        
        # Now try to refresh it
        response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
