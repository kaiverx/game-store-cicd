#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os#модуль для работы с операционкой 
import sys#сус модуль  доступа к системным параметрам интерпритатора (аргументы cmdшки)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')#словарь, методсловаря(ключ и значение) путь для настроек проекта
    try:
        from django.core.management import execute_from_command_line#принимает список аргументов и запускает ту команду которую вписал
    except ImportError as exc:#сохраняем ошибку в переменную
        raise ImportError(#ошибка выбрасывается и видно чем вызвана эта ошибка
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)#при запуске python manage.py runserver 8000, запускает соотв команду


if __name__ == '__main__':#проверка на корректный запуск файла, чтобы маин запускался только при прямом запуске????
    main()
