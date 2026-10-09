#!/usr/bin/env bash
# Первичная настройка сервера (Ubuntu 24.04) под CI/CD game-store:
#   Java 21 + Jenkins LTS (без мастера установки), плагины, админ-пользователь,
#   Multibranch Pipeline job «game-store-cicd», systemd-сервис приложения.
# Запуск: под root, один раз (повторный запуск безопасен).
set -euo pipefail

REPO_OWNER=kaiverx
REPO_NAME=game-store-cicd
JOB_NAME=game-store-cicd
APP_ROOT=/opt/game-store
APP_PORT=8000
JENKINS_HOME=/var/lib/jenkins
PUBLIC_IP=$(curl -4 -s --max-time 5 https://api.ipify.org || hostname -I | awk '{print $1}')

log() { echo -e "\n\033[1;32m==> $*\033[0m"; }
[ "$(id -u)" = 0 ] || { echo "Запусти под root"; exit 1; }
export DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------------- 1. пакеты
log "1/9 Системные пакеты (Java 21, git, python3-venv, rsync)"
apt-get update -qq
apt-get install -y -qq fontconfig openjdk-21-jre git python3-venv python3-pip rsync curl ca-certificates openssl >/dev/null
java -version 2>&1 | head -1

# ---------------------------------------------------------------- 2. Jenkins
log "2/9 Jenkins LTS"
if ! dpkg -s jenkins >/dev/null 2>&1; then
    KEYRING=/usr/share/keyrings/jenkins-keyring.asc
    : > "$KEYRING"
    for k in jenkins.io-2026.key jenkins.io-2023.key; do
        curl -fsSL "https://pkg.jenkins.io/debian-stable/$k" >> "$KEYRING" 2>/dev/null || true
    done
    echo "deb [signed-by=$KEYRING] https://pkg.jenkins.io/debian-stable binary/" > /etc/apt/sources.list.d/jenkins.list
    apt-get update -qq
    apt-get install -y -qq jenkins >/dev/null
fi
systemctl stop jenkins || true
dpkg -s jenkins | grep -E '^Version'

# порт: 8080, если свободен (или занят самим Jenkins), иначе 8090
JENKINS_PORT=8080
if ss -ltnpH "sport = :8080" | grep -qv java; then
    if ss -ltnpH "sport = :8080" | grep -q .; then JENKINS_PORT=8090; fi
fi
echo "Порт Jenkins: $JENKINS_PORT"

# ---------------------------------------------------------------- 3. systemd override
log "3/9 Параметры запуска Jenkins (без мастера установки)"
mkdir -p /etc/systemd/system/jenkins.service.d
cat > /etc/systemd/system/jenkins.service.d/override.conf <<EOF
[Service]
Environment="JENKINS_PORT=$JENKINS_PORT"
Environment="JAVA_OPTS=-Djava.awt.headless=true -Djenkins.install.runSetupWizard=false"
TimeoutStartSec=600
EOF
systemctl daemon-reload

# ---------------------------------------------------------------- 4. плагины
log "4/9 Плагины Jenkins"
PM_JAR=/opt/jenkins-plugin-manager.jar
if [ ! -f "$PM_JAR" ]; then
    TAG=$(curl -fsSLo /dev/null -w '%{url_effective}' https://github.com/jenkinsci/plugin-installation-manager-tool/releases/latest | sed 's#.*/tag/##')
    curl -fsSL -o "$PM_JAR" "https://github.com/jenkinsci/plugin-installation-manager-tool/releases/download/$TAG/jenkins-plugin-manager-${TAG#v}.jar"
fi
mkdir -p "$JENKINS_HOME/plugins"
java -jar "$PM_JAR" --war /usr/share/java/jenkins.war --plugin-download-directory "$JENKINS_HOME/plugins" \
    --plugins workflow-aggregator workflow-multibranch git github github-branch-source junit \
              pipeline-stage-view pipeline-graph-view timestamper ws-cleanup credentials-binding \
    2>&1 | tail -3

# ---------------------------------------------------------------- 5. init-скрипт
log "5/9 Админ-пользователь, права, job $JOB_NAME"
ADMIN_FILE=/root/jenkins-admin.txt
if [ ! -f "$ADMIN_FILE" ]; then
    echo "admin $(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 16)" > "$ADMIN_FILE"
    chmod 600 "$ADMIN_FILE"
fi
mkdir -p "$JENKINS_HOME/init.groovy.d"
install -m 600 -o jenkins -g jenkins "$ADMIN_FILE" "$JENKINS_HOME/init-admin.txt"
cat > "$JENKINS_HOME/init.groovy.d/10-setup.groovy" <<EOF
import jenkins.model.*
import hudson.security.*
import jenkins.branch.BranchSource
import com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger
import org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject
import org.jenkinsci.plugins.github_branch_source.*

def j = Jenkins.get()

// --- пользователь admin (создаётся только если его нет)
def f = new File('$JENKINS_HOME/init-admin.txt')
def realm = (j.securityRealm instanceof HudsonPrivateSecurityRealm) ? j.securityRealm : new HudsonPrivateSecurityRealm(false)
if (f.exists()) {
    def (u, p) = f.text.trim().split(' ')
    if (realm.getUser(u) == null) { realm.createAccount(u, p); println "[setup] user \$u created" }
    f.delete()
}
j.setSecurityRealm(realm)

// --- права: залогиненным всё, анонимам только чтение (для демонстрации)
def auth = new FullControlOnceLoggedInAuthorizationStrategy()
auth.setAllowAnonymousRead(true)
j.setAuthorizationStrategy(auth)
j.setNumExecutors(2)

// --- URL Jenkins (нужен для ссылок и webhook)
def loc = JenkinsLocationConfiguration.get()
loc.setUrl('http://$PUBLIC_IP:$JENKINS_PORT/')
loc.save()
j.save()

// --- Multibranch Pipeline job
if (j.getItem('$JOB_NAME') == null) {
    def mbp = j.createProject(WorkflowMultiBranchProject, '$JOB_NAME')
    mbp.setDisplayName('$JOB_NAME')
    mbp.setDescription('CI/CD игрового магазина (Django REST). Ветки feature/*, dev — CI; main — CI + CD.')
    def src
    try { src = new GitHubSCMSource('$REPO_OWNER', '$REPO_NAME', 'https://github.com/$REPO_OWNER/$REPO_NAME', true) }
    catch (Throwable e) { src = new GitHubSCMSource('$REPO_OWNER', '$REPO_NAME') }
    src.setId('$JOB_NAME-github')
    src.setTraits([new BranchDiscoveryTrait(3)])
    mbp.getSourcesList().add(new BranchSource(src))
    mbp.addTrigger(new PeriodicFolderTrigger('1d'))   // страховочное сканирование раз в сутки
    mbp.save()
    mbp.scheduleBuild2(0)
    println "[setup] job $JOB_NAME created"
}
EOF
chown -R jenkins:jenkins "$JENKINS_HOME"

# ---------------------------------------------------------------- 6. приложение
log "6/9 Каталоги и systemd-сервис приложения game-store"
mkdir -p "$APP_ROOT/app" "$APP_ROOT/shared/static"
if [ ! -f "$APP_ROOT/env" ]; then
    cat > "$APP_ROOT/env" <<EOF
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$(openssl rand -hex 32)
DJANGO_ALLOWED_HOSTS=$PUBLIC_IP,localhost,127.0.0.1
DJANGO_DB_PATH=$APP_ROOT/shared/db.sqlite3
DJANGO_STATIC_ROOT=$APP_ROOT/shared/static
EOF
fi
chmod 640 "$APP_ROOT/env"
chown -R jenkins:jenkins "$APP_ROOT"

cat > /etc/systemd/system/game-store.service <<EOF
[Unit]
Description=Game Store (Django REST API, gunicorn)
After=network.target
ConditionPathExists=$APP_ROOT/venv/bin/gunicorn

[Service]
User=jenkins
Group=jenkins
WorkingDirectory=$APP_ROOT/app
EnvironmentFile=$APP_ROOT/env
ExecStart=$APP_ROOT/venv/bin/gunicorn app.wsgi:application --bind 0.0.0.0:$APP_PORT --workers 2 --access-logfile -
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable game-store >/dev/null 2>&1

# jenkins может перезапускать только этот сервис
cat > /etc/sudoers.d/jenkins-game-store <<EOF
jenkins ALL=(root) NOPASSWD: /usr/bin/systemctl restart game-store, /usr/bin/systemctl status game-store --no-pager
EOF
chmod 440 /etc/sudoers.d/jenkins-game-store
visudo -cf /etc/sudoers.d/jenkins-game-store >/dev/null

# ---------------------------------------------------------------- 7. firewall
log "7/9 Firewall"
if ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow OpenSSH >/dev/null; ufw allow "$JENKINS_PORT/tcp" >/dev/null; ufw allow "$APP_PORT/tcp" >/dev/null
    echo "ufw: открыты $JENKINS_PORT и $APP_PORT"
else
    echo "ufw выключен — порты не ограничиваются"
fi

# ---------------------------------------------------------------- 8. запуск
log "8/9 Запуск Jenkins"
systemctl enable jenkins >/dev/null 2>&1
systemctl restart jenkins
for i in $(seq 1 90); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$JENKINS_PORT/login" || true)
    [ "$code" = "200" ] && break
    sleep 2
done
echo "Jenkins отвечает: HTTP $code"

# ---------------------------------------------------------------- 9. проверка
log "9/9 Проверка"
sleep 5
if curl -fs "http://127.0.0.1:$JENKINS_PORT/job/$JOB_NAME/api/json" >/dev/null; then
    echo "job $JOB_NAME: OK"
else
    echo "job $JOB_NAME не найден — смотри: journalctl -u jenkins | grep setup"
fi
journalctl -u jenkins --since "-5min" --no-pager | grep -E '\[setup\]|SEVERE' | tail -5 || true

cat <<EOF

=====================================================================
 ГОТОВО
 Jenkins:   http://$PUBLIC_IP:$JENKINS_PORT/
 Логин:     $(cut -d' ' -f1 "$ADMIN_FILE")
 Пароль:    $(cut -d' ' -f2 "$ADMIN_FILE")      (сохранён в $ADMIN_FILE)
 Webhook:   http://$PUBLIC_IP:$JENKINS_PORT/github-webhook/
 Приложение (после первого деплоя из main): http://$PUBLIC_IP:$APP_PORT/api/games/
=====================================================================
EOF
