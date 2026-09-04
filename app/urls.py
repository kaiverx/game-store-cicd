#корневая маршрутизация 
from django.conf import settings#доступ к настройкам проекта
from django.contrib import admin#модуль админки
from django.urls import path, include#функция для описания маршрута, подключает файлы маршрутов другого  приложения
from django.conf.urls.static import static#функция для раздачи медиафайлов в реж разработки
#список маршрутов 
urlpatterns = [
    path('admin/', admin.site.urls),#все маршруты кт начинаются с admin отдаётся админке 
    path('api/', include('store.urls')),#все марш кт начинаются с api передаётся в store/urls
]

if settings.DEBUG:#только если debug==true добавляет марш для раздачи медиафайлов 
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)