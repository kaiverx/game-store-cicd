import datetime#модуль для работы с датой и временем
import pyotp#библиотека для двухфакторной аутентификации генерит и проверяет одноразовые коды TOTP 
from io import BytesIO#позволяет работать с бинарными данными как с файлом но не создавая файл на диске. Нужен для экспорта генерит xlsx в память и сразу ответ отдаётся

import pandas as pd#для работы с табл данных pd сокращение

from django.core.cache import cache#система кэширования джанги 
from django.contrib.auth import authenticate, login, logout#проверяет логин+пароль, возвращает пользователя, login создаёт сессию  logout уничтожает 
from django.http import HttpResponse#базовый класс http ответа для экспорта excel(отдаётся файл а не джейсон)

from rest_framework import viewsets, serializers#модуль с вьюсетами, мини сериалезация для логина и статы
from rest_framework.viewsets import GenericViewSet#пустой вьюсет без готового круд
from rest_framework.decorators import action#декоратор для добавления своих эндов сверх стандартного круд
from rest_framework.response import Response#класс ответа DRF (превращает питон словарь в джейсон)
from rest_framework.permissions import BasePermission, IsAuthenticated#базовый класс для написания своих правил доступа,IsAuthenticated готовое право, только залогиненые
from django.db.models import Avg, Count, Max, Min#функции агрегации для бд нужны для статистики . Джанго передаёт их в sql
#импорт моделей и сериализаторов
from .models import Developer, Game, UserProfile, Purchase, Review
from .serializers import DeveloperSerializer, GameSerializer, UserProfileSerializer, PurchaseSerializer, ReviewSerializer

#кастомное право доступа, пропускает только тех кто прошёл двухэтапку
#после успешного ввода OTP кода кладём в кэш otp_good_<id> = true на 5 мин пока флаг живёт южер считается прошедшим 2FA и может делать защищенные операции. серез 5 мин флаг протухает нужно вводить код заново
class OTPRequired(BasePermission):#наследование от базового класса DRF
    def has_permission(self, request, view):#метод который DRF вызывает перед каждым запросом  возвращает тру елси пропустить фалсе если зепретить вернуть 403, request текущий запрос, view вьюха к кт обращаются
        return bool(request.user and cache.get(f'otp_good_{request.user.id}', False))#request.user проверка на то что пользователь вообще есть, cache.get(...) лезем в кэш по ключу вида otp_good_5 (где 5 id юзера) если тру то пользователь прошёл OTP если ключа нет фалзе
#аутентификация и OTP
class UserProfileViewSet(GenericViewSet):#наследует GenericViewSet вьюсет без автоматического круд, контейнер для кастомных действий(логин, OTP ...)
    permission_classes = [IsAuthenticated]#право ао умолчанию для всего вьюсета: только залогиненые
    #мини сериализатор внутри вьюсета для валидации OTP запроса, не привязан к модели 
    class OTPSerializer(serializers.Serializer):
        key = serializers.CharField()#поле которое ждёт строку с введённым кодом
    #мини сериализатор для логина, ожидает юзернаме и пароль
    class LoginSerializer(serializers.Serializer):
        username = serializers.CharField()
        password = serializers.CharField()

    @action(detail=False, url_path="check-login", methods=['GET'], permission_classes=[])#декоратор DRF кт добавляет доп энд к вьюсету помимо стандартного круд, detail=false действие относится к коллекции (url /api/userprofile/logn/) а не к конкретному объекту если быд бы false то (/api/userprofile/5/login/), url_path- кусок url Для этого действия, methods - какими http методами вызывается, permission_classes - пустой список = проава не требуются(доступно всем даже не залогиненым)
    def get_check_login(self, request, *args, **kwargs):#эндпоинт GET /api/.../check-login/ отвечает фронту залогинен ли текущий юзер, permission_classes доступен всем, args kwargs приём любых доп аргументов, request.user.is_authenticated - либо тру либо фалсе залогинен/нет
        return Response({#response DRF сам превращает словарь в джейсон
            'is_authenticated': self.request.user.is_authenticated
        })
    #эндпоинт который логинит пользователя POST /api/.../login/ 
    @action(detail=False, url_path="login", methods=['POST'], permission_classes=[])
    def use_login(self, request, *args, **kwargs):
        #request.data тело запроса что прислал фронт .get(username) безопастно достаём поле 
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)# проверяет пару логин/пароль по базе если верно то возвращает объект user если неверно None, пароли в бд кэшированы, authenticate сам сравнивает хэши не расшифровывая
        if user:#если аутентификация прошла login создаёт сессию записывает в серверную сессию и в куки браузера, что этот юзер теперь залогинен, дальше при каждом запросе джанго будет знать кто это
            login(request, user)
        return Response({
            'is_authenticated': bool(user)#тру если вошёл фалсе если нет отдаём фронту
        }) #Athenticate только проверяет  пароль логин запоминает в сессии.
    #POST /api/.../logout/ logout(request) уничтожает сессию
    @action(detail=False, url_path="logout", methods=['POST'], permission_classes=[])
    def use_logout(self, request, *args, **kwargs):
        logout(request)
        return Response({'success': True})
    #POST /api/.../otp-login/  тут permission_classes не указан -> действует классовый isAuthenticated(сначала обычный логин потом OTP)
    @action(detail=False, url_path='otp-login', methods=['POST'])
    def otp_login(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)#метод ORM найти профиль этого юзера а если его нет создать. Возвращает кортеж (объект, создан ли), profile, _ = распаковка кортежа _ соглашение "переменная мусорка" флаг создан ли , поэтому в _
        if not profile.otp_key:#если у профиля нет секретного ключа OTP 
            profile.otp_key = pyotp.random_base32()# генерит случайный секретный ключ (строка в кодировке base32). Это корень всей 2FA из него генерятся коды. ключ общий для сервака и прилоджения аутентификатора юзера
            profile.save()#сохранение ключа в БД

        totp = pyotp.TOTP(profile.otp_key)# создаётся объект  TOTP на основе секретного ключа TOTP умеет генерить текущий 6 значный код и проверяет введённый
        #валидация входных данных тем самым мини сериализатором, ожидаем поле key(код)
        serializer = self.OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)#isvalid проверяет данные если поля key нет автоматически вернёт ошибку 400 
        #totp.verify(код, valid_window=1) проверяет введённый код pyotp сам вычисляет какой код должен быть сейчас (по секретному ключу + текущ времени) и сравнивает
        success = False
        if totp.verify(serializer.validated_data['key'], valid_window=1):#valid_window допускает коды из соседних 30 секундных окон(предыдущее и следующее)/ Это на случай если часмы юзера чуть расходятся с сервером или он ввёл код на границе смены 
            cache.set(f'otp_good_{request.user.id}', True, 300)#кладём в кэш флаг (этот юзер прошёл OTP) на 300 секунд  третий арг set время жизни в секундах. Именно этот флаг потом проверяет OTPRequired
            success = True

        return Response({'success': success})#фронту отдаём {"success": true/false}
    #GET /api/.../otp-status/ сообщает фронту прошёл ли юзер OTP прямо щас, фронт решает показать кнопку создания\удаления
    @action(detail=False, url_path='otp-status', methods=['GET'])
    def get_otp_status(self, request, *args, **kwargs):
        otp_good = cache.get(f'otp_good_{request.user.id}', False)
        return Response({'otp_good': otp_good})
    #выдача ключа qr
    @action(detail=False, url_path='otp-key', methods=['GET'])
    def get_otp_key(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)#get_or_create Генерация ключа если его нет
        if not profile.otp_key:
            profile.otp_key = pyotp.random_base32()
            profile.save()
        totp = pyotp.TOTP(profile.otp_key)
        return Response({
            'otp_key': profile.otp_key,
            'otp_uri': totp.provisioning_uri(name=request.user.username, issuer_name='GameStore')#totp.provisioning_uri генрит спец юрл формата otpauth://, если этот юрл закодить в qr гугл аутентификатор его отсканит и автоматом добавит акк, name=request.user.username под каким именем покажется в приложухе issuer_name='GameStore' название сервиса(издателя)
        })
    #GET /api/.../info/ отдаёт всё что нужно знать о тек пользователе одним запросом permission_classes=[] доступ всем
    @action(detail=False, url_path='info', methods=['GET'], permission_classes=[])
    def get_info(self, request, *args, **kwargs):
        is_auth = request.user.is_authenticated#залогинен ли 
        otp_good = cache.get(f'otp_good_{request.user.id}', False) if is_auth else False#тернарное выражение короткий иф елсе в одну строку, берём флаг OTP из кэша но только если залогинен
        return Response({
            'is_authenticated': is_auth,#вошёл ли
            'is_superuser': request.user.is_superuser if is_auth else False,#админ ли request.user.is_superuser встроеный флаг
            'username': request.user.username if is_auth else None,#логин
            'otp_good': otp_good,#прошёл ли 2fa
        })

#ModelViewSet делает все круд операции автоматически 
class DeveloperViewSet(viewsets.ModelViewSet):
    queryset = Developer.objects.all()#с какими данными работает весь вьюсет, он работает со всемии полями девелопера
    serializer_class = DeveloperSerializer#каким сериализатором превращать объекты в джейсон и обратно 
    #права по действию переопределение метода который DRF вызывает чтобы узнать какие права применить к текущему запросу, возвращает список объектов прав
    def get_permissions(self):
        #проверяет входит ли текущее действиев список изменяющих данные операции
        if self.action in ['create', 'update', 'partial_update', 'destroy']:#self.action какое действие сейчас выполняется DRF сам проставляет сюда строку list список retrieve один объект create update partial_update destroy 
            return [IsAuthenticated(), OTPRequired()] #если да (ктото хочет изменить данные ) возвращает isAuthenticated должен быть залогинен и должен пройти 2FA, тут с круглыми скобками создаются объекты прав (экземпляры классов) потому что get_permition должен вернуть готовые экземпляры 
        return []#для остальных действий (список просмотр одного статистика экспорт) прав не требуется -> доступно всем
    #сериализатор внутри вьюсета для оформления ответа статистики, нужно чтобы отдать статистику в акуратном валидированным виде
    class StatsSerializer(serializers.Serializer):
        count = serializers.IntegerField()
    #статистика Эндпоинт GET /api/developers/stats/ возвращает колво разрабов 
    @action(detail=False, methods=["GET"], url_path="stats")
    def get_stats(self, request):
        stats = Developer.objects.aggregate(count=Count("*"))#агрегация подсчёт сводных данных повсей таблице, aggregate метод ORM для вычисления сводных значений(сумма, среднее, кол-во) Django переведёт это в sql с Count() - функция посчитать кол-во строк * считать все записи, count под каким именем положить результат, вернут словарь count:42
        return Response(self.StatsSerializer(instance=stats).data)#пропускаем результат через сериализатор instance передаём готовый объект (словарь: 42) для сериализации, .data итоговый результат в виде готового к отдаче словаря response отправляем клиенту count 42 
    #собирает всех разрабов в excel файл и отдаёт на скачивание GET /api/developers/export-excel/
    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):
        try:
            qs = Developer.objects.all()#берём всех разрабов 
            data = []#пустой список куда соберём строки будущей таблицы
            for item in qs:#цикл по каждому разрабу
                data.append({#добавляем в список словарь, где ключ = название столбца, значение = данные, каждый словарь одна строка excel
                    "ID": item.id,#берём поля объекта
                    "Название": item.developer_name,
                    "Страна": item.country,
                    "Дата основания": str(item.foundation_date),#дату превращаем в строку str чтобы коррекно записать в эксель
                })#итог data- список словарей [{"ID":1,"Название":"CD Projekt",...}, {...}]
            df = pd.DataFrame(data)#создаём DataFrame таблицу pandas из списка словарей pandas сам разложит ключи словарей->столбцы, элем списка-> строки это таблица в памяти
            output = BytesIO()#создаём буфер в памяти (файл кт нет на диске) эксель запишется сюда а не в файл на серваке
            with pd.ExcelWriter(output, engine="openpyxl") as writer:#открываем писатель excel  with ...  as менеджер контекста гарантирует что после блока ресурс правильно закроется, engine какой библиотекой писать xlsx 
                df.to_excel(writer, index=False, sheet_name="Разработчики")#записываем таблицу эксель index - недобавлятть  служебный столбец с номерами строк пандас без этого в эксель появился бы лишний безымянный столбец, sheet_name название листа в книге excel 
            output.seek(0)#перемотать буфер в начало, после записи курсор в буфере стоит в конце  чтобы прочитать всё содержимое надо вернуть на позицию 0 в начало 
            today = datetime.datetime.now().strftime("%Y-%m-%d")#datetime текущие дата и время strftime форматируем в строку по шаблону %Y - год, %m - месяц, %d - день
            filename = f"developers_{today}.xlsx"#собираем имя файла в f строку 
            response = HttpResponse(#httpresponse сырой http ответ не response/json потому что отдаём файл а не данные
                output.read(),#читаем всё содержимое буфера (байты эксель файла) - тело ответа 
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",#MIME - тип файла сообщает браузеру это Excel файл по нему браузер поймсёт что делать это длинная строка официальный MIME тип для xlsx
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'#устанавливаем http Заголовок ответа, attachment говорит браузеру: скачать файл как вложение  а не открыть окно в окне именно изза attachement браузер покажет диалог сохранить файл
            return response#отдаём файл
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), OTPRequired()]
        return []
    #стата с числами возвращает словарь с четырьмя числами {'count': 50, 'avg': 29.99, 'max': 59.99, 'min': 0}
    class StatsSerializer(serializers.Serializer):
        count = serializers.IntegerField()
        avg = serializers.FloatField()
        max = serializers.FloatField()
        min = serializers.FloatField()

    @action(detail=False, methods=["GET"], url_path="stats")
    def get_stats(self, request):
        stats = Game.objects.aggregate(
            count=Count("*"),
            avg=Avg("price"),
            max=Max("price"),
            min=Min("price"),
        )
        return Response(self.StatsSerializer(instance=stats).data)

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):
        try:
            qs = Game.objects.all()
            data = []
            for item in qs:
                data.append({
                    "ID": item.id,
                    "Название": item.game_name,
                    "Цена": str(item.price),
                    "Оценка": item.score,
                    "Статус": item.status,
                    "Разработчик": item.developer.developer_name if item.developer else "",# item.developer.developer_name идём по foreginKey в связаную таблицу и берём имя разраба if item.developer else тернарное выражение если разраб есть то берём имя если нет None, если у игры нет разраба
                })
            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Игры")
            output.seek(0)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"games_{today}.xlsx"
            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class UserProfilesViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    #просмотр профиля требует хотябы логина IsAuthenticated а не открыт всем удаление только с OTP
    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), OTPRequired()]
        return [IsAuthenticated()]
    #метод кт определяет какие записи вообще доступны в этом запросе. DRF вызывает его для списка/просмотра, мы переопределяем чтобы ограничить видимость
    def get_queryset(self):
        qs = super().get_queryset()#берём базовый queryset (все профили, UserProfile.objects.all()) super - обращение к родительскому методу
        if not self.request.user.is_authenticated:#если юзер не залогинен -> qs.none() возвращает пустой queryset(вообще ничего) аноним не видит ни одного профиля
            return qs.none()
        if self.request.user.is_superuser:#это админ
            user_id = self.request.query_params.get('user_id')#self.request.query_params.get читаем query параметр из url (например /api/userprofiles/?user_id=5) query_params - параметры после ?  в адресе
            if user_id:#если админ указал конкретного юзера фильтруемого по нему. Если не указал - админ видит всех 
                qs = qs.filter(user=user_id)#метод ORM оставить только записи где поле user равно указанному, переводится в sql WHERE user_id = ...
        else:
            qs = qs.filter(user=self.request.user)#если это обычный юзер -> показываем только его собственный профиль, чужие не видят
        return qs

    def perform_create(self, serializer):# метод вызываемый при создании объекта 
        serializer.save(user=self.request.user) #сохраняем профиь насильно проставляя user = текущий залогиненый клиент не может создвать профиль на чужого юзера 

    class StatsSerializer(serializers.Serializer):
        count = serializers.IntegerField()
        avg = serializers.FloatField()
        max = serializers.FloatField()
        min = serializers.FloatField()

    @action(detail=False, methods=["GET"], url_path="stats")
    def get_stats(self, request):
        stats = UserProfile.objects.aggregate(
            count=Count("*"),
            avg=Avg("balance"),
            max=Max("balance"),
            min=Min("balance"),
        )
        return Response(self.StatsSerializer(instance=stats).data)
    #если не админ выгрузка сразу запрещена
    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):
        if not self.request.user.is_superuser:
            return Response({'error': 'Нет доступа'}, status=403)
        try:
            qs = UserProfile.objects.all()
            data = []
            for item in qs:
                data.append({
                    "ID": item.id,
                    "Пользователь": item.user.username,
                    "Баланс": str(item.balance),
                })
            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Профили")
            output.seek(0)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"profiles_{today}.xlsx"
            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), OTPRequired()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_authenticated:
            return qs.none()
        if self.request.user.is_superuser:
            user_id = self.request.query_params.get('user_id')
            if user_id:
                qs = qs.filter(user=user_id)
        else:
            qs = qs.filter(user=self.request.user)
        return qs

    class StatsSerializer(serializers.Serializer):
        count = serializers.IntegerField()
        avg = serializers.FloatField()
        max = serializers.FloatField()
        min = serializers.FloatField()

    @action(detail=False, methods=["GET"], url_path="stats")
    def get_stats(self, request):
        stats = self.get_queryset().aggregate(#стата и экспорт считается с учётом фильтров, юзер в стате видит только свои покупки а не всех 
            count=Count("*"),
            avg=Avg("price_at_purchase"),
            max=Max("price_at_purchase"),
            min=Min("price_at_purchase"),
        )
        return Response(self.StatsSerializer(instance=stats).data)

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):
        try:
            qs = self.get_queryset()
            data = []
            for item in qs:
                data.append({
                    "ID": item.id,
                    "Пользователь": item.user.username,
                    "Игра": item.game.game_name,
                    "Цена покупки": str(item.price_at_purchase),
                    "Дата покупки": str(item.purchase_date),
                })
            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Покупки")
            output.seek(0)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"purchases_{today}.xlsx"
            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    #читать отзывы может любой user_id фильтр работает только для админа 
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), OTPRequired()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return []

    def get_queryset(self):
        qs = super().get_queryset()
        # суперюзер может фильтровать по юзеру
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            user_id = self.request.query_params.get('user_id')
            if user_id:
                qs = qs.filter(user=user_id)
        return qs

    class StatsSerializer(serializers.Serializer):
        count = serializers.IntegerField()
        avg = serializers.FloatField()
        max = serializers.IntegerField()
        min = serializers.IntegerField()

    @action(detail=False, methods=["GET"], url_path="stats")
    def get_stats(self, request):
        stats = self.get_queryset().aggregate(
            count=Count("*"),
            avg=Avg("rating"),
            max=Max("rating"),
            min=Min("rating"),
        )
        return Response(self.StatsSerializer(instance=stats).data)

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):
        try:
            qs = self.get_queryset()
            data = []
            for item in qs:
                data.append({
                    "ID": item.id,
                    "Пользователь": item.user.username,
                    "Игра": item.game.game_name,
                    "Текст отзыва": item.review_text,
                    "Оценка": item.rating,
                })
            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Отзывы")
            output.seek(0)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"reviews_{today}.xlsx"
            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)

#регистрация
class RegisterViewSet(GenericViewSet):#GenericViewSet без круд только кастомные действия
    permission_classes = []#доступно всем

    class RegisterSerializer(serializers.Serializer):
        username = serializers.CharField()
        password = serializers.CharField()
        email = serializers.EmailField(required=False, allow_blank=True)#поле кт проверяет что значение похоже на email(allow blank=true можно прислать пустое значение)
    #POST /api/register/register/ импорт user внутри метода  
    @action(detail=False, url_path='register', methods=['POST'], permission_classes=[])
    def register(self, request, *args, **kwargs):
        from django.contrib.auth.models import User
        serializer = self.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']#достаются прооверенные данные validated_data словарь очищеных данных у имеёл .get('email', '') берем безопастно, если нет то пустая строка
        password = serializer.validated_data['password']
        email = serializer.validated_data.get('email', '')

        if User.objects.filter(username=username).exists():
            return Response({'success': False, 'error': 'Пользователь с таким именем уже существует'}, status=400)

        user = User.objects.create_user(username=username, password=password, email=email)#User.objects.create спец метод создания пользователя автоматически хэширует пароль
        login(request, user)#сразу логинится пользователь создаём новую сессию 
        return Response({'success': True, 'username': user.username})

#юзеры без профиля список юзеров у которых ещё нет профиля
class UsersWithoutProfileViewSet(GenericViewSet):
    permission_classes = []

    @action(detail=False, methods=["GET"], url_path="without-profile")
    def get_without_profile(self, request):
        from django.contrib.auth.models import User
        users_with_profile = UserProfile.objects.values_list('user_id', flat=True)#берём список id пользователей у кт есть профиль,values_list вытащить только одно полде а не целые объекты, flat true вернуть плоский список [3,6,12]  а не кортежи без flat каждый элемент был бы кортежем из одного значения
        users = User.objects.exclude(id__in=users_with_profile).values('id', 'username')#противоположностьь filter все кроме указаных 
        return Response(list(users))
