import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 布局组件
import AppLayout from '@/components/layout/AppLayout.vue'
import PublicLayout from '@/components/layout/PublicLayout.vue'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import PlanLayout from '@/components/layout/PlanLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '/',
        component: PublicLayout,
        children: [
          {
            path: '',
            name: 'Home',
            component: () => import('@/views/HomePage.vue'),
          },
          {
            path: 'login',
            name: 'Login',
            redirect: '/',
          },
          {
            path: 'register',
            name: 'Register',
            redirect: '/',
          },
        ],
      },
      {
        path: '/chat',
        component: AuthLayout,
        children: [
          {
            path: '',
            name: 'Chat',
            component: () => import('@/views/ChatPage.vue'),
          },
          {
            path: ':sessionId',
            name: 'ChatSession',
            component: () => import('@/views/ChatSessionPage.vue'),
          },
        ],
      },
      {
        path: '/plans',
        component: AuthLayout,
        children: [
          {
            path: '',
            name: 'PlanList',
            component: () => import('@/views/PlanListPage.vue'),
          },
        ],
      },
      {
        path: '/plans/:planId',
        component: PlanLayout,
        children: [
          {
            path: '',
            name: 'PlanDetail',
            component: () => import('@/views/PlanDetailPage.vue'),
          },
        ],
      },
      {
        path: '/trips/:tripId',
        component: AuthLayout,
        children: [
          {
            path: '',
            name: 'TripExecute',
            component: () => import('@/views/TripExecutePage.vue'),
          },
        ],
      },
      {
        path: '/travelogues',
        component: AuthLayout,
        children: [
          {
            path: '',
            name: 'TravelogueList',
            component: () => import('@/views/TravelogueListPage.vue'),
          },
          {
            path: ':id',
            name: 'Travelogue',
            component: () => import('@/views/TraveloguePage.vue'),
          },
        ],
      },
      {
        path: '/share/:code',
        component: PublicLayout,
        children: [
          {
            path: '',
            name: 'SharedView',
            component: () => import('@/views/TraveloguePage.vue'),
          },
        ],
      },
      {
        path: '/profile',
        component: AuthLayout,
        children: [
          {
            path: '',
            name: 'Profile',
            component: () => import('@/views/ProfilePage.vue'),
          },
          {
            path: 'preferences',
            name: 'Preferences',
            component: () => import('@/views/PreferencePage.vue'),
          },
        ],
      },
      {
        path: '/:pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('@/views/NotFoundPage.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫（暂时禁用登录保护 — 后端未就绪）
router.beforeEach(() => {
  return true
})

export default router
