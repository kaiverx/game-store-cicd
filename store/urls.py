#маршрутизация апи 
from rest_framework.routers import DefaultRouter#DefaultRouter роутер DRF который автоматически создаёт url для вьюсетов 
from . import views#импорт всего модуля views чтобы обращаться к views.GameViewSet

router = DefaultRouter()#создаём экземпляр роутера , регистрация будет регаться здесь
#r'games' raw строка в рав строке символ \ не считается спецсимволом для юрл патернов это привычка\стандарт, по сути просто строка 'games'
#регистрация вьюсетов под url префиксом одна эта строка автоматически создаёт все маршруты круд для игр 
#пишем одну строку router.register и она генерит 7 маршрутов сам без роута пришлось бы руками прописывать path для каждого действия каждой модели - десятки строк. роутер знает структуру viewset и делает это автоматом 
router.register(r'games', views.GameViewSet)
router.register(r'developers', views.DeveloperViewSet)
router.register(r'profiles', views.UserProfilesViewSet)
router.register(r'purchases', views.PurchaseViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'user', views.UserProfileViewSet, basename='user')#basename базовое имя для генерации имён маршрутов , обычно роутер сам вычисляет имя из queryset но в userprofile и registerviewset это genericset без queryset, роуту неоткуда взять имя нужно указать вручную 
router.register(r'auth', views.RegisterViewSet, basename='auth')

urlpatterns = router.urls#router.urls свойство роута кт возвращает готовый список всех сгенереных  маршрутов urlpatterns  стандартное имя переменной кт джанго ищет в файле маршрутов 
