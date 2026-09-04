<script setup>
import { ref, onBeforeMount, computed } from 'vue'
import axios from 'axios'

const reviews = ref([])
const games = ref([])
const reviewToAdd = ref({})
const reviewToEdit = ref({})
const stats = ref({})

const filters = ref({ review_text: '', rating_min: '', rating_max: '' })

const filteredReviews = computed(() => {
  return reviews.value.filter(r => {
    if (filters.value.review_text && !r.review_text.toLowerCase().includes(filters.value.review_text.toLowerCase())) return false
    if (filters.value.rating_min && r.rating < Number(filters.value.rating_min)) return false
    if (filters.value.rating_max && r.rating > Number(filters.value.rating_max)) return false
    return true
  })
})

function clearFilters() { filters.value = { review_text: '', rating_min: '', rating_max: '' } }

async function fetchReviews() {
  const r = await axios.get("/api/reviews/")
  reviews.value = r.data
}

async function fetchGames() {
  const r = await axios.get("/api/games/")
  games.value = r.data
}

async function fetchStats() {
  const r = await axios.get("/api/reviews/stats/")
  stats.value = r.data
}

async function onReviewAdd() {
  await axios.post("/api/reviews/", { ...reviewToAdd.value })
  await fetchReviews()
  await fetchStats()
  reviewToAdd.value = {}
}

async function onUpdateReview() {
  await axios.put(`/api/reviews/${reviewToEdit.value.id}/`, { ...reviewToEdit.value })
  await fetchReviews()
}

async function onReviewEditClick(review) {
  reviewToEdit.value = { ...review }
}

async function onRemoveClick(review) {
  if (confirm('Удалить отзыв?')) {
    await axios.delete(`/api/reviews/${review.id}/`)
    await fetchReviews()
    await fetchStats()
  }
}

async function onExportExcel() {
  const response = await axios.get("/api/reviews/export-excel/", { responseType: "blob" })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement("a")
  link.href = url
  link.setAttribute("download", "reviews.xlsx")
  document.body.appendChild(link)
  link.click()
  link.remove()
}

onBeforeMount(async () => {
  await fetchReviews()
  await fetchGames()
  await fetchStats()
})
</script>

<template>
  <div class="container">
    <h1>Отзывы</h1>

    <div class="mb-3 p-2 border rounded bg-light d-flex justify-content-between align-items-center">
      <div>
        Всего: <strong>{{ stats.count }}</strong> |
        Средняя оценка: <strong>{{ stats.avg?.toFixed(1) }}</strong> |
        Макс: <strong>{{ stats.max }}</strong> |
        Мин: <strong>{{ stats.min }}</strong>
      </div>
      <button class="btn btn-success btn-sm" @click="onExportExcel">
        <i class="bi bi-file-earmark-excel"></i> Экспорт в Excel
      </button>
    </div>

    <form @submit.prevent.stop="onReviewAdd">
      <div class="row">
        <div class="col">
          <div class="form-floating">
            <select class="form-select" v-model="reviewToAdd.game" required>
              <option :value="g.id" v-for="g in games">{{ g.game_name }}</option>
            </select>
            <label>Игра</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="reviewToAdd.review_text" required />
            <label>Текст отзыва</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="number" class="form-control" v-model="reviewToAdd.rating" min="1" max="10" required />
            <label>Оценка (1-10)</label>
          </div>
        </div>
        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>
      </div>
    </form>

    <div class="row mb-2 mt-2">
      <div class="col">
        <input class="form-control form-control-sm" v-model="filters.review_text" placeholder="Фильтр по тексту" />
      </div>
      <div class="col">
        <input class="form-control form-control-sm" type="number" v-model="filters.rating_min" placeholder="Оценка от" min="1" max="10" />
      </div>
      <div class="col">
        <input class="form-control form-control-sm" type="number" v-model="filters.rating_max" placeholder="Оценка до" min="1" max="10" />
      </div>
      <div class="col-auto">
        <button class="btn btn-secondary btn-sm" @click="clearFilters">Сбросить</button>
      </div>
    </div>

    <div v-for="item in filteredReviews" class="item mb-2 p-2 border rounded">
      <div>
        <strong>Игра #{{ item.game }}</strong> — Оценка: {{ item.rating }}/10
        <br/><small>{{ item.review_text }}</small>
      </div>
      <div>
        <button class="btn btn-success me-1" @click="onReviewEditClick(item)" data-bs-toggle="modal" data-bs-target="#editReviewModal">
          <i class="bi bi-pencil-fill"></i>
        </button>
        <button class="btn btn-danger" @click="onRemoveClick(item)">
          <i class="bi bi-x"></i>
        </button>
      </div>
    </div>

    <div class="modal fade" id="editReviewModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h1 class="modal-title fs-5">редактировать</h1>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="form-floating mb-2">
              <select class="form-select" v-model="reviewToEdit.game">
                <option :value="g.id" v-for="g in games">{{ g.game_name }}</option>
              </select>
              <label>Игра</label>
            </div>
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="reviewToEdit.review_text" />
              <label>Текст отзыва</label>
            </div>
            <div class="form-floating mb-2">
              <input type="number" class="form-control" v-model="reviewToEdit.rating" min="1" max="10" />
              <label>Оценка (1-10)</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
            <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateReview">Сохранить</button>
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
