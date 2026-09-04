<script setup>
import { ref, onBeforeMount, computed } from 'vue'
import axios from 'axios'

const games = ref([])
const developers = ref([])
const gameToAdd = ref({})
const gameToEdit = ref({})
const gamePictureRef = ref()
const gameAddImageUrl = ref()
const gameEditPictureRef = ref()
const gameEditImageUrl = ref()
const currentImageUrl = ref('')
const stats = ref({})

const filters = ref({ game_name: '', status: '', developer_name: '' })

const filteredGames = computed(() => {
  return games.value.filter(g => {
    if (filters.value.game_name && !g.game_name.toLowerCase().includes(filters.value.game_name.toLowerCase())) return false
    if (filters.value.status && g.status !== filters.value.status) return false
    if (filters.value.developer_name && !(g.developer?.developer_name || '').toLowerCase().includes(filters.value.developer_name.toLowerCase())) return false
    return true
  })
})

function clearFilters() { filters.value = { game_name: '', status: '', developer_name: '' } }

function gameAddPictureChange(event) {
  const file = event.target.files[0]
  gameAddImageUrl.value = file ? URL.createObjectURL(file) : null
}

function gameEditPictureChange(event) {
  const file = event.target.files[0]
  gameEditImageUrl.value = file ? URL.createObjectURL(file) : null
}

async function fetchGames() {
  const r = await axios.get("/api/games/")
  games.value = r.data
}

async function fetchDevelopers() {
  const r = await axios.get("/api/developers/")
  developers.value = r.data
}

async function fetchStats() {
  const r = await axios.get("/api/games/stats/")
  stats.value = r.data
}

async function onGameAdd() {
  const formData = new FormData()
  if (gamePictureRef.value?.files[0]) formData.append('picture', gamePictureRef.value.files[0])
  formData.append('game_name', gameToAdd.value.game_name)
  formData.append('price', gameToAdd.value.price)
  formData.append('score', gameToAdd.value.score || 0)
  formData.append('info', gameToAdd.value.info)
  formData.append('status', gameToAdd.value.status)
  formData.append('system_requirements', gameToAdd.value.system_requirements)
  formData.append('developer_id', gameToAdd.value.developer_id)
  await axios.post("/api/games/", formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  await fetchGames()
  await fetchStats()
  gameToAdd.value = {}
  gameAddImageUrl.value = null
  if (gamePictureRef.value) gamePictureRef.value.value = ''
}

async function onUpdateGame() {
  const formData = new FormData()
  if (gameEditPictureRef.value?.files[0]) formData.append('picture', gameEditPictureRef.value.files[0])
  formData.append('game_name', gameToEdit.value.game_name)
  formData.append('price', gameToEdit.value.price)
  formData.append('score', gameToEdit.value.score || 0)
  formData.append('info', gameToEdit.value.info)
  formData.append('status', gameToEdit.value.status)
  formData.append('system_requirements', gameToEdit.value.system_requirements)
  formData.append('developer_id', gameToEdit.value.developer_id)
  await axios.put(`/api/games/${gameToEdit.value.id}/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  await fetchGames()
  await fetchStats()
  gameEditImageUrl.value = null
  if (gameEditPictureRef.value) gameEditPictureRef.value.value = ''
}

async function onGameEditClick(game) {
  gameToEdit.value = { ...game, developer_id: game.developer?.id }
  gameEditImageUrl.value = game.picture || null
}

async function onRemoveClick(game) {
  if (confirm(`Удалить "${game.game_name}"?`)) {
    await axios.delete(`/api/games/${game.id}/`)
    await fetchGames()
    await fetchStats()
  }
}

function openImageModal(url) { currentImageUrl.value = url }

async function onExportExcel() {
  const response = await axios.get("/api/games/export-excel/", { responseType: "blob" })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement("a")
  link.href = url
  link.setAttribute("download", "games.xlsx")
  document.body.appendChild(link)
  link.click()
  link.remove()
}

onBeforeMount(async () => {
  await fetchGames()
  await fetchDevelopers()
  await fetchStats()
})
</script>

<template>
  <div class="container">
    <h1>Игры</h1>

    <div class="mb-3 p-2 border rounded bg-light d-flex justify-content-between align-items-center">
      <div>
        Всего: <strong>{{ stats.count }}</strong> |
        Средняя цена: <strong>{{ stats.avg?.toFixed(2) }}₽</strong> |
        Макс: <strong>{{ stats.max }}₽</strong> |
        Мин: <strong>{{ stats.min }}₽</strong>
      </div>
      <button class="btn btn-success btn-sm" @click="onExportExcel">
        <i class="bi bi-file-earmark-excel"></i> Экспорт в Excel
      </button>
    </div>

    <form @submit.prevent.stop="onGameAdd">
      <div class="row">
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="gameToAdd.game_name" required />
            <label>Название</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="number" class="form-control" v-model="gameToAdd.price" required />
            <label>Цена</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="number" class="form-control" v-model="gameToAdd.score" step="0.1" />
            <label>Оценка</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="gameToAdd.info" required />
            <label>Описание</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <select class="form-select" v-model="gameToAdd.status" required>
              <option value="beta">Beta</option>
              <option value="released">Released</option>
              <option value="early access">Early Access</option>
              <option value="coming soon">Coming Soon</option>
            </select>
            <label>Статус</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="gameToAdd.system_requirements" required />
            <label>Системные требования</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <select class="form-select" v-model="gameToAdd.developer_id" required>
              <option :value="d.id" v-for="d in developers">{{ d.developer_name }}</option>
            </select>
            <label>Разработчик</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="file" class="form-control" ref="gamePictureRef" @change="gameAddPictureChange" />
            <label>Фото</label>
          </div>
        </div>
        <div class="col-auto">
          <img :src="gameAddImageUrl" style="max-height: 60px;" alt="" />
        </div>
        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>
      </div>
    </form>

    <div class="row mb-2 mt-2">
      <div class="col">
        <input class="form-control form-control-sm" v-model="filters.game_name" placeholder="Фильтр по названию" />
      </div>
      <div class="col">
        <select class="form-select form-select-sm" v-model="filters.status">
          <option value="">Все статусы</option>
          <option value="beta">Beta</option>
          <option value="released">Released</option>
          <option value="early access">Early Access</option>
          <option value="coming soon">Coming Soon</option>
        </select>
      </div>
      <div class="col">
        <input class="form-control form-control-sm" v-model="filters.developer_name" placeholder="Фильтр по разработчику" />
      </div>
      <div class="col-auto">
        <button class="btn btn-secondary btn-sm" @click="clearFilters">Сбросить</button>
      </div>
    </div>

    <div v-for="item in filteredGames" class="item mb-2 p-2 border rounded">
      <div>
        <strong>{{ item.game_name }}</strong> - {{ item.developer?.developer_name }} ({{ item.price }}₽, {{ item.status }})
        <br/><small>{{ item.info }} | {{ item.system_requirements }} | Оценка: {{ item.score }}</small>
      </div>
      <div v-if="item.picture" class="item-photo">
        <img :src="item.picture" style="max-height: 60px; cursor: pointer;" alt="Фото"
          @click="openImageModal(item.picture)" data-bs-toggle="modal" data-bs-target="#gameImageModal" />
      </div>
      <div v-else>Нет фото</div>
      <div>
        <button class="btn btn-success me-1" @click="onGameEditClick(item)" data-bs-toggle="modal" data-bs-target="#editGameModal">
          <i class="bi bi-pencil-fill"></i>
        </button>
        <button class="btn btn-danger" @click="onRemoveClick(item)">
          <i class="bi bi-x"></i>
        </button>
      </div>
    </div>

    <div class="modal fade" id="editGameModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h1 class="modal-title fs-5">редактировать</h1>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="gameToEdit.game_name" />
              <label>Название</label>
            </div>
            <div class="form-floating mb-2">
              <input type="number" class="form-control" v-model="gameToEdit.price" />
              <label>Цена</label>
            </div>
            <div class="form-floating mb-2">
              <input type="number" class="form-control" v-model="gameToEdit.score" step="0.1" />
              <label>Оценка</label>
            </div>
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="gameToEdit.info" />
              <label>Описание</label>
            </div>
            <div class="form-floating mb-2">
              <select class="form-select" v-model="gameToEdit.status">
                <option value="beta">Beta</option>
                <option value="released">Released</option>
                <option value="early access">Early Access</option>
                <option value="coming soon">Coming Soon</option>
              </select>
              <label>Статус</label>
            </div>
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="gameToEdit.system_requirements" />
              <label>Системные требования</label>
            </div>
            <div class="form-floating mb-2">
              <select class="form-select" v-model="gameToEdit.developer_id">
                <option :value="d.id" v-for="d in developers">{{ d.developer_name }}</option>
              </select>
              <label>Разработчик</label>
            </div>
            <div class="form-floating mb-2">
              <input type="file" class="form-control" ref="gameEditPictureRef" @change="gameEditPictureChange" />
              <label>Фото</label>
            </div>
            <div v-if="gameEditImageUrl">
              <img :src="gameEditImageUrl" style="max-height: 100px;" alt="" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
            <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateGame">Сохранить</button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="gameImageModal" tabindex="-1">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-body text-center">
            <img :src="currentImageUrl" style="max-width: 100%; max-height: 70vh;" alt="" />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
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
.item-photo { margin-right: 10px; }
</style>
