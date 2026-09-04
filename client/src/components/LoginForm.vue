<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user_store'
import { storeToRefs } from 'pinia'
import Cookies from 'js-cookie'
import axios from 'axios'

const username = ref('')
const password = ref('')
const otpKey = ref('')
const message = ref('')
const showRegister = ref(false)
const otpCode = ref('')

const regUsername = ref('')
const regPassword = ref('')
const regEmail = ref('')

const userStore = useUserStore()
const { userInfo } = storeToRefs(userStore)

function updateCsrf() {
  axios.defaults.headers.common['X-CSRFToken'] = Cookies.get("csrftoken")
}

async function onLogin() {
  updateCsrf()
  await userStore.login(username.value, password.value)
  if (userInfo.value.is_authenticated) {
    message.value = 'Вход выполнен успешно'
  } else {
    message.value = 'Неверный логин или пароль'
  }
}

async function onRegister() {
  updateCsrf()
  try {
    const r = await axios.post("/api/auth/register/", {
      username: regUsername.value,
      password: regPassword.value,
      email: regEmail.value,
    })
    if (r.data.success) {
      message.value = `Регистрация успешна! Вы вошли как ${r.data.username}`
      await userStore.checkLogin()
      showRegister.value = false
    }
  } catch (e) {
    message.value = e.response?.data?.error || 'Ошибка регистрации'
  }
}

async function onOtpLogin() {
  updateCsrf()
  const r = await axios.post("/api/user/otp-login/", { key: otpKey.value })
  if (r.data.success) {
    message.value = 'OTP подтверждён'
    await userStore.checkLogin()
  } else {
    message.value = 'Неверный OTP код'
  }
}

async function getOtpCode() {
  try {
    const r = await axios.get("/api/user/otp-key/")
    otpCode.value = r.data.otp_key
    message.value = ''
  } catch (e) {
    if (e.response?.status === 404 || e.response?.status === 500) {
      message.value = 'Сначала создайте профиль в разделе Профили'
    } else {
      message.value = 'Ошибка получения OTP ключа'
    }
  }
}

async function onLogout() {
  updateCsrf()
  await userStore.logout()
  message.value = 'Выход выполнен'
  otpCode.value = ''
}
</script>

<template>
  <div class="container">
    <h1>Авторизация</h1>

    <div v-if="message" class="alert alert-info mb-3">{{ message }}</div>

    <div v-if="!userInfo.is_authenticated">
      <div v-if="!showRegister" class="mb-3 p-2 border rounded">
        <h5>Вход</h5>
        <div class="row">
          <div class="col">
            <div class="form-floating">
              <input type="text" class="form-control" v-model="username" />
              <label>Логин</label>
            </div>
          </div>
          <div class="col">
            <div class="form-floating">
              <input type="password" class="form-control" v-model="password" />
              <label>Пароль</label>
            </div>
          </div>
          <div class="col-auto d-flex gap-2 align-items-center">
            <button class="btn btn-primary" @click="onLogin">Войти</button>
            <button class="btn btn-outline-secondary" @click="showRegister = true">Регистрация</button>
          </div>
        </div>
      </div>

      <div v-if="showRegister" class="mb-3 p-2 border rounded">
        <h5>Регистрация</h5>
        <div class="row">
          <div class="col">
            <div class="form-floating">
              <input type="text" class="form-control" v-model="regUsername" required />
              <label>Логин</label>
            </div>
          </div>
          <div class="col">
            <div class="form-floating">
              <input type="password" class="form-control" v-model="regPassword" required />
              <label>Пароль</label>
            </div>
          </div>
          <div class="col">
            <div class="form-floating">
              <input type="email" class="form-control" v-model="regEmail" />
              <label>Email (необязательно)</label>
            </div>
          </div>
          <div class="col-auto d-flex gap-2 align-items-center">
            <button class="btn btn-primary" @click="onRegister">Зарегистрироваться</button>
            <button class="btn btn-outline-secondary" @click="showRegister = false">Назад</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="userInfo.is_authenticated" class="mb-3 p-2 border rounded">
      <p>Вы вошли как <strong>{{ userInfo.username }}</strong>. OTP статус: <strong>{{ userInfo.otp_good ? 'подтверждён' : 'не подтверждён' }}</strong></p>

      <div v-if="!userInfo.otp_good" class="mb-3">
        <h5>Введите OTP код</h5>
        <div class="row">
          <div class="col">
            <div class="form-floating">
              <input type="text" class="form-control" v-model="otpKey" />
              <label>OTP код</label>
            </div>
          </div>
          <div class="col-auto d-flex gap-2 align-items-center">
            <button class="btn btn-success" @click="onOtpLogin">Подтвердить</button>
            <button class="btn btn-outline-secondary" @click="getOtpCode">Получить код</button>
          </div>
        </div>
        <div v-if="otpCode" class="mt-2 p-2 border rounded bg-light">
          <p class="mb-1"><small>Добавьте этот ключ в Google Authenticator вручную:</small></p>
          <strong>{{ otpCode }}</strong>
          <p class="mb-0 mt-1"><small class="text-muted">В приложении: + → Ввести ключ вручную → вставить ключ</small></p>
        </div>
      </div>

      <button class="btn btn-danger" @click="onLogout">Выйти</button>
    </div>
  </div>
</template>
