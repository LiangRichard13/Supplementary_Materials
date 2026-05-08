import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../HomePage.vue'
import SurveyView from '../SurveyView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomePage
  },
  {
    path: '/survey',
    name: 'Survey',
    component: SurveyView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
