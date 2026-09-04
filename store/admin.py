#регистрация моделей в админке 
#джанго сам даёт админ панель по адресу /admin/ готовый интерфейс для управления данными но по умолчанию он не знает про модели
from django.contrib import admin
from .models import Developer, Game, UserProfile, Purchase, Review

admin.site.register(Developer)#регистрация модели в админке после этого в админ появляется раздел для управления этими записями
admin.site.register(Game)
admin.site.register(UserProfile)
admin.site.register(Purchase)
admin.site.register(Review)
