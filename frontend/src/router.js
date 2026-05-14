import { createRouter, createWebHistory } from 'vue-router'
import InterviewCenter from './views/InterviewCenter.vue'
import InterviewDetail from './views/InterviewDetail.vue'
import JDManager from './views/JDManager.vue'
import ResumeBuilder from './views/ResumeBuilder.vue'
import ResumeLibrary from './views/ResumeLibrary.vue'
import SettingsPanel from './views/SettingsPanel.vue'

export const routes = [
  {
    path: '/',
    redirect: '/resumes'
  },
  {
    path: '/resumes',
    name: 'resumes',
    component: ResumeLibrary,
    meta: { title: '简历库', navKey: 'resumes', propsKey: 'resumes' }
  },
  {
    path: '/builder',
    name: 'builder',
    component: ResumeBuilder,
    meta: { title: '在线构建', navKey: 'builder', propsKey: 'builder' }
  },
  {
    path: '/jds',
    name: 'jds',
    component: JDManager,
    meta: { title: 'JD 管理', navKey: 'jds', propsKey: 'jds' }
  },
  {
    path: '/interview',
    name: 'interview',
    component: InterviewCenter,
    meta: { title: '面试与报告', navKey: 'interview', propsKey: 'interviewCenter' }
  },
  {
    path: '/interview/:id',
    name: 'interview-detail',
    component: InterviewDetail,
    meta: { title: '面试详情', navKey: 'interview', propsKey: 'interviewDetail' }
  },
  {
    path: '/history',
    redirect: '/interview'
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsPanel,
    meta: { title: '系统设置', navKey: 'settings', propsKey: 'settings' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/resumes'
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})
