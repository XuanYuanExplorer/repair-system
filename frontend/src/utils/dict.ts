/** 枚举字典：文案与颜色只在这里维护，模板中禁止写三元表达式。 */

export type Tone = 'ink' | 'red' | 'solid' | 'gray'

export interface DictItem {
  label: string
  en?: string
  tone: Tone
}

/** 工单状态（与后端 repair_service.STATUS 一一对应） */
export const ORDER_STATUS: Record<string, DictItem> = {
  pending: { label: '待受理', en: 'PENDING', tone: 'ink' },
  assigned: { label: '已派单', en: 'ASSIGNED', tone: 'ink' },
  fixing: { label: '维修中', en: 'FIXING', tone: 'red' },
  verify: { label: '待确认', en: 'VERIFY', tone: 'red' },
  done: { label: '已完成', en: 'DONE', tone: 'gray' },
  cancelled: { label: '已取消', en: 'CLOSED', tone: 'gray' },
}

export const ORDER_STATUS_TABS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待受理' },
  { value: 'assigned', label: '已派单' },
  { value: 'fixing', label: '维修中' },
  { value: 'verify', label: '待确认' },
  { value: 'done', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
]

export const CATEGORY: Record<string, { label: string; en: string }> = {
  water: { label: '水电', en: 'WATER' },
  door: { label: '门窗', en: 'DOOR' },
  furniture: { label: '家具', en: 'FURNITURE' },
  network: { label: '网络', en: 'NETWORK' },
  ac: { label: '空调', en: 'AIRCON' },
  public: { label: '公共区域', en: 'PUBLIC' },
}

export const CATEGORY_LIST = Object.entries(CATEGORY).map(([value, v]) => ({ value, ...v }))

/** 室内可报修位置（与后端 location_desc 拼装规则一致） */
export const ROOM_SPOTS = ['空调主机', '热水器', '网口', '门锁', '桌椅', '衣柜', '卫浴']
export const PUBLIC_AREAS = ['走廊', '楼道', '公共卫浴', '洗衣房', '公共厨房']

export const BILL_STATUS: Record<string, DictItem> = {
  unpaid: { label: '待缴', tone: 'ink' },
  paid: { label: '已缴', tone: 'gray' },
  overdue: { label: '已逾期', tone: 'red' },
  cancelled: { label: '已关闭', tone: 'gray' },
}

export const BILL_TYPE: Record<string, string> = {
  electricity: '电费',
  accommodation: '住宿费',
  water: '水费',
  penalty: '违约金',
  material: '维修材料费',
}

export const FEEDBACK_TYPE: Record<string, string> = {
  attitude: '服务态度',
  quality: '维修质量',
  charge: '收费疑问',
  suggestion: '设施建议',
}

export const FEEDBACK_STATUS: Record<string, DictItem> = {
  submitted: { label: '处理中', tone: 'ink' },
  replied: { label: '已回复', tone: 'ink' },
  closed: { label: '已关闭', tone: 'gray' },
}

export const MESSAGE_TYPE: Record<string, { label: string; en: string }> = {
  order: { label: '工单提醒', en: 'ORDER' },
  bill: { label: '账单提醒', en: 'BILL' },
  notice: { label: '通知公告', en: 'NOTICE' },
  paid: { label: '缴费成功', en: 'PAID' },
  system: { label: '系统消息', en: 'SYSTEM' },
}

export const NOTICE_TYPE: Record<string, string> = {
  notice: '通知',
  check: '查寝',
  utility: '停水停电',
  safety: '安全',
}

export const HYGIENE_LEVEL: Record<string, DictItem> = {
  excellent: { label: '优秀', tone: 'ink' },
  good: { label: '良好', tone: 'ink' },
  pass: { label: '合格', tone: 'gray' },
  fail: { label: '不合格', tone: 'red' },
}

export function statusOf(map: Record<string, DictItem>, key: string | null | undefined): DictItem {
  return (key && map[key]) || { label: key || '未知', tone: 'gray' }
}
