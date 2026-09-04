<script setup>
import { ref, onBeforeMount, computed } from 'vue'
import axios from 'axios'

const developers = ref([])
const developerToAdd = ref({})
const developerToEdit = ref({})
const developerPictureRef = ref()
const developerAddImageUrl = ref()
const developerEditPictureRef = ref()
const developerEditImageUrl = ref()
const currentImageUrl = ref('')
const stats = ref({})

const filters = ref({ developer_name: '', country: '' })

const filteredDevelopers = computed(() => {
  return developers.value.filter(d => {
    if (filters.value.developer_name && !d.developer_name.toLowerCase().includes(filters.value.developer_name.toLowerCase())) return false
    if (filters.value.country && !d.country.toLowerCase().includes(filters.value.country.toLowerCase())) return false
    return true
  })
})

function clearFilters() { filters.value = { developer_name: '', country: '' } }

function developerAddPictureChange(event) {
  const file = event.target.files[0]
  developerAddImageUrl.value = file ? URL.createObjectURL(file) : null
}

function developerEditPictureChange(event) {
  const file = event.target.files[0]
  developerEditImageUrl.value = file ? URL.createObjectURL(file) : null
}

async function fetchDevelopers() {
  const r = await axios.get("/api/developers/")
  developers.value = r.data
}

async function fetchStats() {
  const r = await axios.get("/api/developers/stats/")
  stats.value = r.data
}

async function onDeveloperAdd() {
  const formData = new FormData()
  if (developerPictureRef.value?.files[0]) formData.append('picture', developerPictureRef.value.files[0])
  formData.append('developer_name', developerToAdd.value.developer_name)
  formData.append('country', developerToAdd.value.country)
  formData.append('foundation_date', developerToAdd.value.foundation_date)
  await axios.post("/api/developers/", formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  await fetchDevelopers()
  await fetchStats()
  developerToAdd.value = {}
  developerAddImageUrl.value = null
  if (developerPictureRef.value) developerPictureRef.value.value = ''
}

async function onUpdateDeveloper() {
  const formData = new FormData()
  if (developerEditPictureRef.value?.files[0]) formData.append('picture', developerEditPictureRef.value.files[0])
  formData.append('developer_name', developerToEdit.value.developer_name)
  formData.append('country', developerToEdit.value.country)
  formData.append('foundation_date', developerToEdit.value.foundation_date)
  await axios.put(`/api/developers/${developerToEdit.value.id}/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  await fetchDevelopers()
  await fetchStats()
  developerEditImageUrl.value = null
  if (developerEditPictureRef.value) developerEditPictureRef.value.value = ''
}

async function onDeveloperEditClick(developer) {
  developerToEdit.value = { ...developer }
  developerEditImageUrl.value = developer.picture || null
}

async function onRemoveClick(developer) {
  if (confirm(`Удалить "${developer.developer_name}"?`)) {
    await axios.delete(`/api/developers/${developer.id}/`)
    await fetchDevelopers()
    await fetchStats()
  }
}

function openImageModal(url) { currentImageUrl.value = url }

async function onExportExcel() {
  const response = await axios.get("/api/developers/export-excel/", { responseType: "blob" })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement("a")
  link.href = url
  link.setAttribute("download", "developers.xlsx")
  document.body.appendChild(link)
  link.click()
  link.remove()
}

onBeforeMount(async () => {
  await fetchDevelopers()
  await fetchStats()
})
</script>

<template>
  <div class="container">
    <h1>Разработчики</h1>

    <div class="mb-3 p-2 border rounded bg-light d-flex justify-content-between align-items-center">
      <div>Всего: <strong>{{ stats.count }}</strong></div>
      <button class="btn btn-success btn-sm" @click="onExportExcel">
        <i class="bi bi-file-earmark-excel"></i> Экспорт в Excel
      </button>
    </div>

    <form @submit.prevent.stop="onDeveloperAdd">
      <div class="row">
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="developerToAdd.developer_name" required />
            <label>Название</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="developerToAdd.country" required />
            <label>Страна</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="date" class="form-control" v-model="developerToAdd.foundation_date" required />
            <label>Дата основания</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="file" class="form-control" ref="developerPictureRef" @change="developerAddPictureChange" />
            <label>Фото</label>
          </div>
        </div>
        <div class="col-auto">
          <img :src="developerAddImageUrl" style="max-height: 60px;" alt="" />
        </div>
        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>
      </div>
    </form>

    <div class="row mb-2 mt-2">
      <div class="col">
        <input class="form-control form-control-sm" v-model="filters.developer_name" placeholder="Фильтр по названию" />
      </div>
      <div class="col">
        <input class="form-control form-control-sm" v-model="filters.country" placeholder="Фильтр по стране" />
      </div>
      <div class="col-auto">
        <button class="btn btn-secondary btn-sm" @click="clearFilters">Сбросить</button>
      </div>
    </div>

    <div v-for="item in filteredDevelopers" class="item mb-2 p-2 border rounded">
      <div>
        <strong>{{ item.developer_name }}</strong> - {{ item.country }} ({{ item.foundation_date }})
      </div>
      <div v-if="item.picture" class="item-photo">
        <img :src="item.picture" style="max-height: 60px; cursor: pointer;" alt="Фото"
          @click="openImageModal(item.picture)" data-bs-toggle="modal" data-bs-target="#developerImageModal" />
      </div>
      <div v-else>Нет фото</div>
      <div>
        <button class="btn btn-success me-1" @click="onDeveloperEditClick(item)" data-bs-toggle="modal" data-bs-target="#editDeveloperModal">
          <i class="bi bi-pencil-fill"></i>
        </button>
        <button class="btn btn-danger" @click="onRemoveClick(item)">
          <i class="bi bi-x"></i>
        </button>
      </div>
    </div>

    <div class="modal fade" id="editDeveloperModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h1 class="modal-title fs-5">редактировать</h1>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="developerToEdit.developer_name" />
              <label>Название</label>
            </div>
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="developerToEdit.country" />
              <label>Страна</label>
            </div>
            <div class="form-floating mb-2">
              <input type="date" class="form-control" v-model="developerToEdit.foundation_date" />
              <label>Дата основания</label>
            </div>
            <div class="form-floating mb-2">
              <input type="file" class="form-control" ref="developerEditPictureRef" @change="developerEditPictureChange" />
              <label>Фото</label>
            </div>
            <div v-if="developerEditImageUrl">
              <img :src="developerEditImageUrl" style="max-height: 100px;" alt="" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
            <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateDeveloper">Сохранить</button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="developerImageModal" tabindex="-1">
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
