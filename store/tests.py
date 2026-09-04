from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from .models import Game, Developer, Purchase, Review

class GameViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.developer = Developer.objects.create(
            developer_name='Dev Studio',
            country='USA',
            foundation_date='2000-01-01'
        )
        self.game_data = {
            'game_name': 'Test Game',
            'price': 50.0,
            'score': 0,
            'info': 'Some info about game',
            'status': 'Available',
            'system_requirements': 'Some requirements',
            'developer': self.developer.id
        }

    def test_create_game(self):
        response = self.client.post('/games/', self.game_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(Game.objects.get().game_name, 'Test Game')

    def test_list_games(self):
        Game.objects.create(
            game_name='Game 1',
            price=30.0,
            score=4.5,
            info='Info 1',
            status='Available',
            system_requirements='Req 1',
            developer=self.developer
        )
        Game.objects.create(
            game_name='Game 2',
            price=60.0,
            score=4.0,
            info='Info 2',
            status='Available',
            system_requirements='Req 2',
            developer=self.developer
        )
        response = self.client.get('/games/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

class PurchaseViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.developer = Developer.objects.create(
            developer_name='Dev Studio',
            country='USA',
            foundation_date='2000-01-01'
        )
        self.game = Game.objects.create(
            game_name='Buy Game',
            price=100.0,
            score=5.0,
            info='Info',
            status='Available',
            system_requirements='Req',
            developer=self.developer
        )

    def test_create_purchase(self):
        data = {'user': self.user.id, 'game': self.game.id, 'price_at_purchase': self.game.price}
        response = self.client.post('/purchases/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Purchase.objects.count(), 1)

    def test_list_purchases(self):
        Purchase.objects.create(user=self.user, game=self.game, price_at_purchase=self.game.price)
        response = self.client.get('/purchases/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class ReviewViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='reviewuser', password='password')
        self.developer = Developer.objects.create(
            developer_name='Dev Studio',
            country='USA',
            foundation_date='2000-01-01'
        )
        self.game = Game.objects.create(
            game_name='Review Game',
            price=80.0,
            score=4.5,
            info='Info',
            status='Available',
            system_requirements='Req',
            developer=self.developer
        )

    def test_create_review(self):
        data = {'user': self.user.id, 'game': self.game.id, 'review_text': 'Great game!', 'rating': 5}
        response = self.client.post('/reviews/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)

    def test_list_reviews(self):
        Review.objects.create(user=self.user, game=self.game, review_text='Nice', rating=4)
        response = self.client.get('/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
