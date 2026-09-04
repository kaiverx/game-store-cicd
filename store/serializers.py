#по факту это мостик между питоновскими объектами и фронтом
#база данных хранит питоновские объекты модели а фронт отдаёт джейсоны по хттпшке, на прямую не получиться объект отправить в бравзер, надо в текст конвертировать
#сериализация  - объект модели -> json (когда отдаём данные фронту), game(...) -> {id:1 gamename:...}
#десиаризация - обратный эффект + проверка что данные корректные
#ModelSerializer - особый вид сериализатора, который сам генерит поля из модели, сам понимает и не нужно каждое поле прописывать DRF сам понимает типы  что число что строка
#DRF - джанго рест фреймворк библиотека для построения rest api, джанго отдаёт хтмл страницы а вью нужны джейсоны, DRF даёт сериализаторы для превращения моделей в джейсоны, вьюсеты для автоматического круд, роуты для генерации url и систему прав доступа 
from rest_framework import serializers#модуль DRF содержит всё для сериализации
from django.contrib.auth.models import User#встроенная модель пользователей 
from .models import Developer, Game, UserProfile, Purchase, Review# импорт моделей .model означает из текущего пакета 

class DeveloperSerializer(serializers.ModelSerializer):#наследжуется от ModelSerializer
    class Meta:#вложенный класс с настройками сериализатора (конфиг)
        model = Developer#на основе какой модели строить поля
        fields = ['id', 'developer_name', 'country', 'foundation_date', 'picture']#какие именно поля включать в JSON DRF сам определит типы полей
#решает задачу как отдавать и принимать связь, для чтения и записи нужно разное
class GameSerializer(serializers.ModelSerializer):
    developer = DeveloperSerializer(read_only=True)#поле для чтения(отдачи данных), вложеный сериализатор, вкладывает полный объект разработчика внутрь игры, read_only поле только для чтения, отдаётся клиенту, результатом будет не developer: 5 а фулл объект
    developer_id = serializers.PrimaryKeyRelatedField(
        queryset=Developer.objects.all(), write_only=True, source='developer'
    )#поле для записи (приём данных) когда фронт создаёт игру он не присылает весь объект а только id  
    #PrimaryKeyRelatedField поле которое представляет связь через первичный ключ id
    #queryset обязательный арг для записываемого related поля: среди каких объектов искать разработчика по присланному id. DRF возьмёт id, найдёт в этом queryset нужного Developer и проверит существует(валидация) 
    #write_only поле только для записи оно принимается при создании обновления но не отдаётся в json обратно(чтобы не дублировать для чтения уже есть)
    #source куда класть значение, фронт присылает поле developer_id но в модели поле называется developer.  source говорит  что нужно значение из developer_id записать в модельное поле developer
    class Meta:#перечисление всех полей игр 
        model = Game
        fields = ['id', 'game_name', 'price', 'score', 'info', 'status',
                  'system_requirements', 'developer', 'developer_id', 'picture']
#сериализатор для встроенной модели User, отдаёт только id username email и не отдаёт пароль и прочие поля
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
#вложенный сериализатор внутрь профиля загоняем объект пользователя read_only пользователя через профиль менять нельзя только показывать
# вот так выглядит {"id": 1, "user": {"id": 3, "username": "vasya", "email": "..."}, "nickname": "Vasyan", "balance": "150.00", "avatar": "/media/avatars/..."}
class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'nickname', 'balance', 'avatar']
#есть переопределение метода
class PurchaseSerializer(serializers.ModelSerializer):
    #переопределение нужно чтобы проставить кто делает покупку, но брать пользователя из тела запроса нельзя- тогда любой бы мог прислать чужой user_id и оформить покупку от чужого имени. Поэтому нужно брать пользователя из самого запроса (кто залогинен), а не из присланых
    def create(self, validated_data):#метод кт вызывается когда сериализатор создаёт новый объект при  POST, validated словарь уже проверенных данных которые прислальфронт 
        #проверка на то что запрос доступен
        if 'request' in self.context:#self.content контент сериализатора словарь с доп данными кт вью передаёт в сериализатор DRF автоматом кладёт туда request(текущий http запрос)
            #validated_data ставим пользователя насильно игнорируя ответ фронта
            validated_data['user'] = self.context['request'].user#текущий залогиненый пользователь, из мидлвере приходит 
        return super().create(validated_data)#родительский метод create кт создаёт запись в бд super- обращение к методу родительского класса 
   
    class Meta:
        model = Purchase
        fields = ['id', 'user', 'game', 'purchase_date', 'price_at_purchase']
        read_only_fields = ['user'] # поле user Только для чтение, оно не принимается от фронта, даже если ктото пришлёт user в теле запроса DRF его проигнорирует
#тож самое что и у прошлого
class ReviewSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        if 'request' in self.context:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = Review
        fields = ['id', 'user', 'game', 'review_text', 'rating', 'created_at']
        read_only_fields = ['user']
