<script setup>
import { ref, onBeforeMount, computed } from 'vue'
import axios from 'axios'
import { useUserStore } from '@/stores/user_store'
import { storeToRefs } from 'pinia'

const userStore = useUserStore()
const { userInfo } = storeToRefs(userStore)

const profiles = ref([])
const stats = ref({})
const profileToEdit = ref({})
const filters = ref({ username: '' })

const profileToAdd = ref({ nickname: '' })
const avatarFileRef = ref()
const avatarPreview = ref('')
const editAvatarFileRef = ref()
const editAvatarPreview = ref('')

const filteredProfiles = computed(() => {
  return profiles.value.filter(p => {
    if (filters.value.username && !(p.user?.username || '').toLowerCase().includes(filters.value.username.toLowerCase())) return false
    return true
  })
})

function clearFilters() { filters.value = { username: '' } }

function onAvatarChange() {
  const file = avatarFileRef.value?.files[0]
  avatarPreview.value = file ? URL.createObjectURL(file) : ''
}

function onEditAvatarChange() {
  const file = editAvatarFileRef.value?.files[0]
  editAvatarPreview.value = file ? URL.createObjectURL(file) : ''
}

async function fetchProfiles() {
  const r = await axios.get("/api/profiles/")
  profiles.value = r.data
}

async function fetchStats() {
  const r = await axios.get("/api/profiles/stats/")
  stats.value = r.data
}

async function onProfileAdd() {
  const formData = new FormData()
  formData.append('nickname', profileToAdd.value.nickname)
  formData.append('balance', 0)
  if (avatarFileRef.value?.files[0]) {
    formData.append('avatar', avatarFileRef.value.files[0])
  }
  await axios.post("/api/profiles/", formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  await fetchProfiles()
  await fetchStats()
  profileToAdd.value = { nickname: '' }
  avatarPreview.value = ''
  if (avatarFileRef.value) avatarFileRef.value.value = ''
}

async function onUpdateProfile() {
  const formData = new FormData()
  formData.append('nickname', profileToEdit.value.nickname)
  formData.append('balance', profileToEdit.value.balance)
  if (editAvatarFileRef.value?.files[0]) {
    formData.append('avatar', editAvatarFileRef.value.files[0])
  }
  await axios.put(`/api/profiles/${profileToEdit.value.id}/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  await fetchProfiles()
}

async function onProfileEditClick(profile) {
  profileToEdit.value = { ...profile }
  editAvatarPreview.value = profile.avatar || ''
  if (editAvatarFileRef.value) editAvatarFileRef.value.value = ''
}

async function onRemoveClick(profile) {
  if (!userInfo.value?.is_superuser) return
  if (confirm(`Удалить профиль "${profile.user?.username}"?`)) {
    await axios.delete(`/api/profiles/${profile.id}/`)
    await fetchProfiles()
    await fetchStats()
  }
}

async function onExportExcel() {
  const response = await axios.get("/api/profiles/export-excel/", { responseType: "blob" })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement("a")
  link.href = url
  link.setAttribute("download", "profiles.xlsx")
  document.body.appendChild(link)
  link.click()
  link.remove()
}

onBeforeMount(async () => {
  await fetchProfiles()
  await fetchStats()
})
</script>

<template>
  <div class="container">
    <h1>{{ userInfo?.is_superuser ? 'Все профили' : 'Мой профиль' }}</h1>

    <div class="mb-3 p-2 border rounded bg-light d-flex justify-content-between align-items-center">
      <div>
        Всего: <strong>{{ stats.count }}</strong>
      </div>
      <button v-if="userInfo?.is_superuser" class="btn btn-success btn-sm" @click="onExportExcel">
        <i class="bi bi-file-earmark-excel"></i> Экспорт в Excel
      </button>
    </div>

    <div v-if="userInfo?.is_authenticated && profiles.length === 0" class="mb-3 p-2 border rounded">
      <h5>Создать профиль</h5>
      <div class="row">
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="profileToAdd.nickname" />
            <label>Никнейм</label>
          </div>
        </div>
        <div class="col">
          <input type="file" class="form-control" ref="avatarFileRef" @change="onAvatarChange" />
        </div>
        <div class="col-auto d-flex align-items-center">
          <img v-if="avatarPreview" :src="avatarPreview" style="max-height: 60px;" />
        </div>
        <div class="col-auto d-flex align-items-center">
          <button class="btn btn-primary" @click="onProfileAdd">Создать профиль</button>
        </div>
      </div>
    </div>

    <div class="row mb-2 mt-2" v-if="userInfo?.is_superuser">
      <div class="col">
        <input class="form-control form-control-sm" v-model="filters.username" placeholder="Фильтр по пользователю" />
      </div>
      <div class="col-auto">
        <button class="btn btn-secondary btn-sm" @click="clearFilters">Сбросить</button>
      </div>
    </div>

    <div v-for="item in filteredProfiles" class="item mb-2 p-2 border rounded">
      <div class="d-flex align-items-center gap-3">
        <div v-if="item.avatar">
          <img :src="item.avatar" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%;" />
        </div>
        <div>
          <strong>{{ item.nickname || item.user?.username }}</strong>
          <br/><small class="text-muted">{{ item.user?.username }} — Баланс: {{ item.balance }}₽</small>
        </div>
      </div>
      <div>
        <button class="btn btn-success me-1" @click="onProfileEditClick(item)" data-bs-toggle="modal" data-bs-target="#editProfileModal">
          <i class="bi bi-pencil-fill"></i>
        </button>
        <button v-if="userInfo?.is_superuser" class="btn btn-danger" @click="onRemoveClick(item)">
          <i class="bi bi-x"></i>
        </button>
      </div>
    </div>

    <div class="modal fade" id="editProfileModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h1 class="modal-title fs-5">редактировать</h1>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="profileToEdit.nickname" />
              <label>Никнейм</label>
            </div>
            <div class="form-floating mb-2">
              <input type="number" class="form-control" v-model="profileToEdit.balance" />
              <label>Баланс</label>
            </div>
            <div class="form-floating mb-2">
              <input type="file" class="form-control" ref="editAvatarFileRef" @change="onEditAvatarChange" />
              <label>Аватар</label>
            </div>
            <div v-if="editAvatarPreview" class="mt-2">
              <img :src="editAvatarPreview" style="max-height: 100px;" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
            <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateProfile">Сохранить</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
