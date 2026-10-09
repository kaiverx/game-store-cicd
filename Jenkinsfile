// CI/CD конвейер для game-store (Django REST Framework).
// Тип: Declarative Pipeline, хранится в репозитории (Pipeline as Code).
//
// Логика по веткам:
//   feature/*, dev  -> CI: установка зависимостей, проверки, автотесты
//   main            -> CI + CD: те же шаги + деплой на сервер и smoke-тест
pipeline {
    agent any

    options {
        timestamps()                                    // время у каждой строки лога
        timeout(time: 20, unit: 'MINUTES')              // защита от зависших сборок
        buildDiscarder(logRotator(numToKeepStr: '20'))  // храним последние 20 сборок
        disableConcurrentBuilds()                       // одна сборка ветки за раз
    }

    environment {
        VENV = "${WORKSPACE}/.venv"
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PYTHONDONTWRITEBYTECODE = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty="format:%h %an: %s"'
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv "$VENV"
                    "$VENV/bin/pip" install --quiet --upgrade pip
                '''
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    "$VENV/bin/pip" install --quiet -r requirements.txt
                    "$VENV/bin/pip" install --quiet unittest-xml-reporting
                    "$VENV/bin/pip" freeze | grep -iE "^(django|djangorestframework|pillow|gunicorn)=="
                '''
            }
        }

        stage('Static checks') {
            steps {
                // конфигурация проекта и отсутствие незакоммиченных изменений моделей
                sh '''
                    "$VENV/bin/python" manage.py check
                    "$VENV/bin/python" manage.py makemigrations --check --dry-run
                '''
            }
        }

        stage('Unit tests') {
            steps {
                sh '''
                    "$VENV/bin/python" manage.py test store -v 2 \
                        --testrunner xmlrunner.extra.djangotestrunner.XMLTestRunner
                '''
            }
            post {
                always {
                    // отчёт по тестам во вкладке Tests и график трендов
                    junit allowEmptyResults: false, testResults: 'TEST-*.xml'
                }
            }
        }

        stage('Deploy') {
            when { branch 'main' }   // CD только для стабильной ветки
            steps {
                sh 'bash deploy/deploy.sh'
            }
        }
    }

    post {
        success { echo "Сборка ${env.BRANCH_NAME} #${env.BUILD_NUMBER}: УСПЕХ" }
        failure { echo "Сборка ${env.BRANCH_NAME} #${env.BUILD_NUMBER}: ОШИБКА — смотри лог стадии" }
        cleanup { cleanWs() }
    }
}
