"""
Автотесты для API интернет-магазина игр (приложение store).
Покрывают CRUD-операции по всем моделям + проверки прав доступа (auth / 2FA).

Запуск локально:
    python manage.py test store
или через pytest:
    pytest store/tests.py

Всего ~32 теста — с запасом перекрывают требование лабы "минимум 20 CRUD-операций".

ВАЖНО: если API подключён в главном urls.py не под префиксом /api/,
        поменяй значение API ниже на свой префикс.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from store.models import Developer, Game, UserProfile, Purchase, Review

# Префикс, под которым подключён router.urls в главном urls.py проекта
API = "/api"


class BaseAPITestCase(APITestCase):
    """Общая подготовка данных для всех тестов: пользователи + разработчик + игра."""

    def setUp(self):
        # чистим кэш, чтобы OTP-флаги не протекали между тестами
        cache.clear()

        self.user = User.objects.create_user(username="tester", password="pass12345")
        self.admin = User.objects.create_superuser(username="admin", password="admin12345")

        self.developer = Developer.objects.create(
            developer_name="CD Projekt",
            country="Poland",
            foundation_date="2002-05-01",
        )
        self.game = Game.objects.create(
            game_name="The Witcher 3",
            price="29.99",
            score=9.5,
            info="RPG про Геральта",
            status="released",
            system_requirements="8GB RAM",
            developer=self.developer,
        )

    def auth(self, user=None):
        """Залогиниться под пользователем (по умолчанию обычный tester)."""
        self.client.force_authenticate(user=user or self.user)

    def pass_otp(self, user=None):
        """Проставить флаг пройденного 2FA — нужно для create/update/delete."""
        u = user or self.user
        cache.set(f"otp_good_{u.id}", True, 300)


# ==========================  DEVELOPER  ==========================
class DeveloperCRUDTests(BaseAPITestCase):
    url_list = f"{API}/developers/"

    def detail(self, pk):
        return f"{API}/developers/{pk}/"

    # ---- READ (открыто всем) ----
    def test_list_developers(self):
        r = self.client.get(self.url_list)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_retrieve_developer(self):
        r = self.client.get(self.detail(self.developer.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["developer_name"], "CD Projekt")

    # ---- CREATE ----
    def test_create_developer_unauthorized(self):
        r = self.client.post(self.url_list, {
            "developer_name": "Valve", "country": "USA", "foundation_date": "1996-08-24",
        })
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_developer_without_otp_forbidden(self):
        self.auth()  # залогинен, но 2FA не пройдена
        r = self.client.post(self.url_list, {
            "developer_name": "Valve", "country": "USA", "foundation_date": "1996-08-24",
        })
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_developer_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.post(self.url_list, {
            "developer_name": "Valve", "country": "USA", "foundation_date": "1996-08-24",
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Developer.objects.count(), 2)

    # ---- UPDATE ----
    def test_update_developer_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.put(self.detail(self.developer.id), {
            "developer_name": "CD Projekt RED", "country": "Poland", "foundation_date": "2002-05-01",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.developer_name, "CD Projekt RED")

    def test_partial_update_developer_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.patch(self.detail(self.developer.id), {"country": "PL"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.country, "PL")

    # ---- DELETE ----
    def test_delete_developer_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.delete(self.detail(self.developer.id))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Developer.objects.count(), 0)


# ==========================  GAME  ==========================
class GameCRUDTests(BaseAPITestCase):
    url_list = f"{API}/games/"

    def detail(self, pk):
        return f"{API}/games/{pk}/"

    def payload(self):
        return {
            "game_name": "Cyberpunk 2077",
            "price": "59.99",
            "score": 8.0,
            "info": "Открытый мир, будущее",
            "status": "released",
            "system_requirements": "16GB RAM",
            "developer_id": self.developer.id,
        }

    def test_list_games(self):
        r = self.client.get(self.url_list)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_retrieve_game(self):
        r = self.client.get(self.detail(self.game.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["game_name"], "The Witcher 3")
        # проверяем, что developer отдаётся вложенным объектом
        self.assertEqual(r.data["developer"]["developer_name"], "CD Projekt")

    def test_create_game_unauthorized(self):
        r = self.client.post(self.url_list, self.payload())
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_game_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.post(self.url_list, self.payload())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Game.objects.count(), 2)

    def test_update_game_ok(self):
        self.auth()
        self.pass_otp()
        data = self.payload()
        data["game_name"] = "Cyberpunk 2077: Ultimate"
        r = self.client.put(self.detail(self.game.id), data)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.game.refresh_from_db()
        self.assertEqual(self.game.game_name, "Cyberpunk 2077: Ultimate")

    def test_partial_update_game_price(self):
        self.auth()
        self.pass_otp()
        r = self.client.patch(self.detail(self.game.id), {"price": "19.99"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.game.refresh_from_db()
        self.assertEqual(str(self.game.price), "19.99")

    def test_delete_game_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.delete(self.detail(self.game.id))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Game.objects.count(), 0)


# ==========================  REVIEW  ==========================
class ReviewCRUDTests(BaseAPITestCase):
    url_list = f"{API}/reviews/"

    def detail(self, pk):
        return f"{API}/reviews/{pk}/"

    def setUp(self):
        super().setUp()
        self.review = Review.objects.create(
            user=self.user, game=self.game, review_text="Отличная игра", rating=8,
        )

    def test_list_reviews_public(self):
        r = self.client.get(self.url_list)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_create_review_unauthorized(self):
        r = self.client.post(self.url_list, {
            "game": self.game.id, "review_text": "Норм", "rating": 7,
        })
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_review_ok(self):
        self.auth()  # отзыв создаётся без 2FA, только логин
        r = self.client.post(self.url_list, {
            "game": self.game.id, "review_text": "Топ", "rating": 10,
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        # user должен проставиться автоматически из запроса, а не из тела
        self.assertEqual(r.data["user"], self.user.id)

    def test_update_review_ok(self):
        self.auth()
        self.pass_otp()  # изменение требует 2FA
        r = self.client.patch(self.detail(self.review.id), {"rating": 10})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 10)

    def test_delete_review_ok(self):
        self.auth()
        self.pass_otp()
        r = self.client.delete(self.detail(self.review.id))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Review.objects.count(), 0)


# ==========================  PURCHASE  ==========================
class PurchaseCRUDTests(BaseAPITestCase):
    url_list = f"{API}/purchases/"

    def detail(self, pk):
        return f"{API}/purchases/{pk}/"

    def setUp(self):
        super().setUp()
        self.purchase = Purchase.objects.create(
            user=self.user, game=self.game, price_at_purchase="29.99",
        )

    def test_list_purchases_unauthorized(self):
        r = self.client.get(self.url_list)
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_list_own_purchases(self):
        self.auth()
        r = self.client.get(self.url_list)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # обычный пользователь видит только свои покупки
        self.assertEqual(len(r.data), 1)

    def test_create_purchase_ok(self):
        self.auth()
        r = self.client.post(self.url_list, {
            "game": self.game.id, "price_at_purchase": "19.99",
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["user"], self.user.id)

    def test_delete_purchase_ok(self):
        self.auth()
        self.pass_otp()  # удаление требует 2FA
        r = self.client.delete(self.detail(self.purchase.id))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Purchase.objects.count(), 0)


# ==========================  USER PROFILE  ==========================
class ProfileCRUDTests(BaseAPITestCase):
    url_list = f"{API}/profiles/"

    def test_list_profiles_unauthorized(self):
        r = self.client.get(self.url_list)
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_list_own_profile(self):
        UserProfile.objects.create(user=self.user, nickname="Тестер")
        self.auth()
        r = self.client.get(self.url_list)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # видит только свой профиль
        self.assertEqual(len(r.data), 1)

    def test_create_profile_ok(self):
        self.auth()  # у tester в setUp профиля ещё нет
        r = self.client.post(self.url_list, {"nickname": "Новичок", "balance": "0.00"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        # профиль привязался к текущему пользователю
        self.assertEqual(r.data["user"]["id"], self.user.id)


# ==========================  AUTH / REGISTER  ==========================
class AuthTests(BaseAPITestCase):
    def test_register_ok(self):
        r = self.client.post(f"{API}/auth/register/", {
            "username": "newuser", "password": "pass12345",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["success"])
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_username(self):
        r = self.client.post(f"{API}/auth/register/", {
            "username": "tester", "password": "whatever",
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(r.data["success"])

    def test_login_ok(self):
        r = self.client.post(f"{API}/user/login/", {
            "username": "tester", "password": "pass12345",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["is_authenticated"])

    def test_login_wrong_password(self):
        r = self.client.post(f"{API}/user/login/", {
            "username": "tester", "password": "wrongpass",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["is_authenticated"])

    def test_check_login_anonymous(self):
        r = self.client.get(f"{API}/user/check-login/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["is_authenticated"])
