import { createRouter, createWebHistory } from 'vue-router'
import DeveloperCRUD from '../components/DeveloperCRUD.vue'
import GameCRUD from '../components/GameCRUD.vue'
import UserProfileCRUD from '../components/UserProfileCRUD.vue'
import PurchaseCRUD from '../components/PurchaseCRUD.vue'
import ReviewCRUD from '../components/ReviewCRUD.vue'
import LoginForm from '../components/LoginForm.vue'

const routes = [
  { path: '/developers', component: DeveloperCRUD },
  { path: '/games', component: GameCRUD },
  { path: '/profiles', component: UserProfileCRUD },
  { path: '/purchases', component: PurchaseCRUD },
  { path: '/reviews', component: ReviewCRUD },
  { path: '/login', component: LoginForm },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
