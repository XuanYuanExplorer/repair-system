import { ref } from 'vue'

/**
 * 列表脏标记：详情页发生状态变更（取消 / 催单 / 确认 / 评价）后置 true，
 * keep-alive 的列表页 onActivated 时据此静默刷新，避免每次返回都请求。
 */
export const repairDirty = ref(false)
export const billDirty = ref(false)
