#модель в джанго это пайтон класс кт описывает одну таблицу в бд, один класс= одна табл, одно поле класса=один столбец табл, один объект класса(запись)= одна строка табл
from django.db import models#всё для описания таблиц все типы
from django.contrib.auth.models import User#встроеная модель user из системы аутентификации, готовая таблица пользователей
#модель разраба 
class Developer(models.Model):#модел модел превращает обычный класс в модель бд, бд даёт .object, .save(), .delete(). автоматом создаёт таблицу симеенм store_developer(приложение_модель) и добавляет автоматическое поле id
    developer_name = models.CharField(max_length=100)#CharField исп для названий и имен max_length обязательный арг 
    country = models.CharField(max_length=50)
    foundation_date = models.DateField()#DataField поле для даты 
    picture = models.ImageField("Изображение", null=True, blank=True, upload_to="developers")#ImageField поле для загруж картинки в бд хранится не картинка а путь к ней, сам файл хранится на диске в папке media требует pillow первый арг - имя название поля, второй арг Null=true разрешение хранить в бд знач Null, третий арг blank=True - разрешение оставлять поле пустым в формах/валидации blank нужен для разрешения не заполнять поле, последний арг в какую подпапку складывать файлы

    def __str__(self):#метод стр питоновский определяет как выглядит объект при пеяати/преоб в строку
        #когда гдето отобразится объект Developer(в админке, в консоли) покажется название а не developer object(1)
        return self.developer_name
#модель игры 
class Game(models.Model):
    STATUS_CHOICES = [ #список допустимых вариантов для поля статуса. каждый элем кортеж из двух знач первое beta - реально хранится в бд, второе Beta что показывается человеку
        ('beta', 'Beta'),
        ('released', 'Released'),
        ('early access', 'Early Access'),
        ('coming soon', 'Coming Soon'),
    ]

    game_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=7, decimal_places=2)#DecimalField  поле для точных десятичных чисел от Float отличается тем что не теряет копейки на округлении maxdigits всего 7цифр в числе decimalplaces из них 2 после запятой
    score = models.FloatField(default=0)#FloatField число с плав запятой 
    info = models.TextField()#TextField поле длинного текста без огр длины 
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='coming soon')#чар со статусом привязка списков вариантов 
    system_requirements = models.TextField()
    developer = models.ForeignKey(Developer, on_delete=models.CASCADE)#ForeginKay внешний ключ связь многие к одному много игр принадлежат одному разрабу, в бдшке это столбец developer_id из табл Developer, второй арг обязательный, что дулать с играмиесли удалят разраба, CASCADE каскадное удаление автоматически удаляются все игры другие варики PROTECT запретить удаление , SET_NULL обнулить связь 
    picture = models.ImageField("Изображение", null=True, blank=True, upload_to="games")

    def __str__(self):
        return self.game_name
#профиль юзера, по факту расширение встроенного user, у дефолтного джанговского user содержится тока логин/пароль/мэйл
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')#OneToOneField связь один к одному  у одного типа один профиль. User - связываем во встройкой, Ondelete удалили типа удаляем профайл, related_name имя обратной связи позволяет из объекта user достучаться до профиля user.profile
    nickname = models.CharField(max_length=100, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avatar = models.ImageField("Аватар", null=True, blank=True, upload_to="avatars")
    otp_key = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):#строковое представление профиля - логин связаного пользователя. Идём по связи user в модель User и берём оть туда username
        return self.user.username
#модель покупки 
class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)#DateTimeField  дата и время auto_now_add ставится один раз при создании а просто auto_now обнуляется при каждомс сохр(дата посл сохранения)
    price_at_purchase = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):#строковое представление логин юзера-название игры исп f строку идём по связям двум сраззу
        return f"{self.user.username} — {self.game.game_name}"
#модель отзыва
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    review_text = models.TextField()
    rating = models.PositiveIntegerField()#PositiveIntegerField целое не отриц число оценка в отзыве
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.game.game_name}"
