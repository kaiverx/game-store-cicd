from django.core.management.base import BaseCommand

from faker import Faker
import random

from store.models import Developer, Game, UserProfile, Purchase, Review
from django.contrib.auth.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        fake = Faker(['ru_RU'])

        # очищаем старые данные
        self.stdout.write('Очищаем старые данные...')
        Review.objects.all().delete()
        Purchase.objects.all().delete()
        UserProfile.objects.all().delete()
        Game.objects.all().delete()
        Developer.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # генерируем разработчиков
        self.stdout.write('Генерируем разработчиков...')
        for _ in range(1000):
            Developer.objects.create(
                developer_name=fake.company(),
                country=fake.country(),
                foundation_date=fake.date_between(start_date='-30y', end_date='today'),
            )

        developers = list(Developer.objects.all())

        # генерируем игры
        self.stdout.write('Генерируем игры...')
        statuses = ['beta', 'released', 'early access', 'coming soon']
        for _ in range(1000):
            Game.objects.create(
                game_name=fake.catch_phrase(),
                price=fake.pydecimal(left_digits=4, right_digits=2, positive=True),
                score=round(fake.pyfloat(min_value=0, max_value=10), 1),
                info=fake.text(),
                status=random.choice(statuses),
                system_requirements=fake.text(max_nb_chars=200),
                developer=random.choice(developers),
            )

        games = list(Game.objects.all())

        # генерируем пользователей
        self.stdout.write('Генерируем пользователей...')
        for i in range(1000):
            username = f'user_{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': fake.email(),
                    'password': '1234',
                }
            )

        users = list(User.objects.filter(is_superuser=False))

        # генерируем профили
        self.stdout.write('Генерируем профили...')
        for user in users:
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'nickname': fake.first_name(),
                    'balance': fake.pydecimal(left_digits=6, right_digits=2, positive=True),
                }
            )

        # генерируем покупки
        self.stdout.write('Генерируем покупки...')
        for _ in range(1000):
            game = random.choice(games)
            Purchase.objects.create(
                user=random.choice(users),
                game=game,
                price_at_purchase=game.price,
            )

        # генерируем отзывы
        self.stdout.write('Генерируем отзывы...')
        for _ in range(1000):
            Review.objects.create(
                user=random.choice(users),
                game=random.choice(games),
                review_text=fake.text(),
                rating=random.randint(1, 10),
            )

        self.stdout.write('Готово! Данные сгенерированы.')
