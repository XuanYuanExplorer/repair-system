import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/views/auth/Login.vue'), meta: { guest: true, title: '登录' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/Register.vue'), meta: { guest: true, title: '注册与认证' } },
  { path: '/reset', name: 'reset', component: () => import('@/views/auth/ResetPassword.vue'), meta: { guest: true, title: '重置密码' } },

  { path: '/', name: 'home', component: () => import('@/views/home/Home.vue'), meta: { auth: true, tab: 'home', title: '服务大厅' } },

  { path: '/repair/submit', name: 'repair-submit', component: () => import('@/views/repair/Submit.vue'), meta: { auth: true, title: '报修提交' } },
  { path: '/repair/list', name: 'repair-list', component: () => import('@/views/repair/List.vue'), meta: { auth: true, tab: 'repair', title: '我的报修', keepAlive: true } },
  { path: '/repair/archive', name: 'repair-archive', component: () => import('@/views/repair/Archive.vue'), meta: { auth: true, title: '我的维修档案' } },
  { path: '/repair/:id(\\d+)', name: 'repair-detail', component: () => import('@/views/repair/Detail.vue'), meta: { auth: true, title: '工单跟踪' }, props: true },
  { path: '/repair/:id(\\d+)/rate', name: 'repair-rate', component: () => import('@/views/repair/Rate.vue'), meta: { auth: true, title: '确认与评价' }, props: true },

  { path: '/payment', name: 'payment', component: () => import('@/views/payment/Center.vue'), meta: { auth: true, tab: 'payment', title: '缴费中心', keepAlive: true } },
  { path: '/payment/bill/:id', name: 'bill-detail', component: () => import('@/views/payment/BillDetail.vue'), meta: { auth: true, title: '账单详情' }, props: true },
  { path: '/payment/result/:txnNo', name: 'pay-result', component: () => import('@/views/payment/Result.vue'), meta: { auth: true, title: '支付结果' }, props: true },
  { path: '/payment/records', name: 'pay-records', component: () => import('@/views/payment/Records.vue'), meta: { auth: true, title: '缴费记录与票据' } },

  { path: '/dorm', name: 'dorm', component: () => import('@/views/dorm/MyRoom.vue'), meta: { auth: true, tab: 'profile', title: '我的寝室' } },
  { path: '/dorm/members', name: 'dorm-members', component: () => import('@/views/dorm/Members.vue'), meta: { auth: true, title: '寝室成员' } },
  { path: '/dorm/duty', name: 'dorm-duty', component: () => import('@/views/dorm/Duty.vue'), meta: { auth: true, title: '值日与卫生' } },
  { path: '/dorm/notice', name: 'dorm-notice', component: () => import('@/views/dorm/Notice.vue'), meta: { auth: true, title: '公告与公约' } },

  { path: '/messages', name: 'messages', component: () => import('@/views/message/Center.vue'), meta: { auth: true, title: '消息中心' } },
  { path: '/profile', name: 'profile', component: () => import('@/views/profile/Profile.vue'), meta: { auth: true, tab: 'profile', title: '个人中心' } },
  { path: '/profile/edit', name: 'profile-edit', component: () => import('@/views/profile/Edit.vue'), meta: { auth: true, title: '编辑资料' } },
  { path: '/feedback', name: 'feedback', component: () => import('@/views/feedback/Feedback.vue'), meta: { auth: true, title: '意见反馈' } },
  { path: '/help', name: 'help', component: () => import('@/views/help/Help.vue'), meta: { auth: false, title: '帮助中心' } },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue'), meta: { title: '页面不存在' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (_to, _from, savedPosition) => savedPosition || { top: 0 },
})

export default router
