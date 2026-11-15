/**
 * 接口类型：与后端 services 的 serializer 一一对应（字段名以 /api/v1/openapi.json 为准）。
 * 契约变更时运行 `npx openapi-typescript http://127.0.0.1:8000/api/v1/openapi.json -o src/api/schema.d.ts`
 * 与本文件比对，避免前后端漂移。
 */

export interface Envelope<T> {
  code: number
  message: string
  data: T
  trace_id: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

/* ---------------- 认证 ---------------- */

export interface RoomBrief {
  room: string
  room_id: number | null
  bed_no: number | null
  bed_position: string | null
  is_leader: boolean
}

export interface SessionUser extends RoomBrief {
  id: number
  name: string
  student_no: string | null
  worker_no: string | null
  role: 'student' | 'worker' | 'admin'
  college: string | null
  class_name: string | null
  grade: number | null
  avatar_url: string | null
  phone: string
}

export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: SessionUser
}

export interface StudentCheck {
  student_no: string
  name_masked: string
  room: string
  bed_no: number
  bed_position: string
  matched: boolean
  reason?: string | null
}

export interface DeviceItem {
  id: number
  device_name: string
  ip: string
  last_active_at: string | null
  revoked: boolean
}

/* ---------------- 首页 ---------------- */

export interface HomeSummary {
  greeting: string
  room_no: string
  user_name: string
  subtitle: string
  today: string
  due: { amount: string; count: number }
  orders: { active_count: number }
  latest_order: {
    id: number
    order_no: string
    short_no: string
    title: string
    status: string
    status_label: string
    status_en: string
    worker_name: string | null
    expect_text: string
    percent: number
  } | null
  unread: { total: number; by_type: Record<string, number> }
  notices: { id: number; title: string; date: string; type: string }[]
  bill_cta: { id: number; title: string; amount: string } | null
  services: { key: string; label: string; en: string; icon: string; to: string; hot: boolean }[]
}

export interface PublicNotice {
  id: number
  title: string
  date: string
  type: string
}

/* ---------------- 报修 ---------------- */

export interface SlotItem {
  code: string
  label: string
  start: string
  end: string
  capacity: number
  booked: number
  left: number
  full: boolean
}

export interface SlotResult {
  date: string
  items: SlotItem[]
}

export interface OrderBrief {
  id: number
  order_no: string
  status: string
  status_label: string
  status_en: string
  category: string
  category_label: string
  title: string
  location_desc: string
  created_at: string
  submitted_text: string
  worker_name: string | null
  expect_text: string | null
  percent: number
  rating: number | null
  duration_days: number | null
  is_timeout: boolean
  repair_round: number
}

export interface OrderListResult extends Page<OrderBrief> {
  counts: Record<string, number>
}

export interface TimelineNode {
  type: string
  label: string
  at: string | null
  actor: string | null
  note: string | null
  state: 'done' | 'active' | 'todo'
}

export interface WorkerBrief {
  id: number
  name: string
  worker_no: string | null
  team: string | null
  phone: string
  avatar_url: string | null
}

export interface OrderDetail {
  id: number
  order_no: string
  status: string
  status_label: string
  status_en: string
  category: string
  category_label: string
  location_type: string
  location_desc: string
  description: string
  media_urls: string[]
  contact_phone: string
  require_presence: boolean
  preferred_date: string | null
  preferred_slot: string | null
  room: string
  created_at: string
  expect_finish_at: string | null
  fix_note: string | null
  material_fee: string
  repair_round: number
  progress: { percent: number; steps: string[]; current_index: number }
  can_edit: boolean
  can_cancel: boolean
  can_urge: boolean
  can_verify: boolean
  can_rate: boolean
  urge_cooldown_sec: number
  rating: { speed: number; attitude: number; quality: number; content: string; is_anonymous: boolean } | null
  worker: WorkerBrief | null
  timeline: TimelineNode[]
  last_message: { sender_name: string; content: string; at: string } | null
}

export interface ChatMessage {
  id: number
  sender_id: number
  sender_name: string
  sender_role: string
  content: string
  created_at: string
  mine: boolean
}

export interface ArchiveResult {
  total_count: number
  avg_duration_days: number
  good_rate: number
  since: string
  distribution: { category: string; label: string; count: number; percent: number; alert: boolean }[]
  repeat_alert: { room: string; category: string; text: string } | null
  recent_ratings: { score: number; content: string; created_at: string; anonymous: boolean }[]
}

export interface OrderCreateResult {
  id: number
  order_no: string
  status: string
}

/* ---------------- 账单 / 支付 ---------------- */

export interface Bill {
  id: number
  bill_no: string
  type: string
  type_label: string
  title: string
  period: string
  amount: string
  late_fee: string
  total: string
  status: string
  status_label: string
  due_date: string | null
  due_text: string | null
  urgent: boolean
  overdue_days: number
  paid_at: string | null
  payable: boolean
  mergeable: boolean
  source_type: string | null
  source_id: number | null
  receipt: { id: number; status: string; status_label: string; email: string } | null
  room_text: string | null
}

export interface BillDetail extends Bill {
  detail: {
    items: { label: string; value: string; unit?: string; formula?: string; reading?: string }[]
    remark: string | null
  }
  channel_options: { value: string; label: string; hint: string | null; disabled: boolean }[]
}

export interface BillSummary {
  unpaid_count: number
  unpaid_amount: string
  overdue_count: number
  overdue_amount: string
  paid_count: number
  due_count: number
  due_amount: string
  semester_total: string
  semester_label: string
}

export interface BillRecords {
  groups: {
    month: string
    label: string
    en: string
    total: string
    items: {
      id: number
      title: string
      sub: string
      amount: string
      receipt_status: string | null
      receipt_id: number | null
      receipt_file: string | null
      can_apply_receipt: boolean
    }[]
  }[]
  overdue: { period: string; title: string; text: string }[]
  year_total: string
  year: string
}

export interface PaymentCreated {
  txn_no: string
  amount: string
  channel: string
  channel_label: string
  status: string
  expire_at: string
  countdown_sec: number
  pay_params: Record<string, unknown>
  bill_ids: number[]
  reused?: boolean
}

export interface TxnResult {
  txn_no: string
  status: 'processing' | 'success' | 'failed' | 'closed'
  raw_status: string
  amount: string
  channel: string
  channel_label: string
  paid_at: string | null
  created_at: string
  expire_at: string | null
  fail_reason: string | null
  bills: { id: number; title: string; amount: string }[]
  receipt_available: boolean
  receipt_applied: boolean
}

/* ---------------- 寝室 / 值日 ---------------- */

export interface Facility {
  id: number
  name: string
  category: string
  status: string
  status_label: string
  enabled_year: number | null
  fault_note: string | null
  last_repair_at: string | null
}

export interface MyRoom {
  id: number
  building: string
  room_no: string
  title: string
  floor: number
  room_type: string
  area: string
  subtitle: string
  capacity: number
  occupied: number
  leader_name: string | null
  leader_id: number | null
  my_bed: { bed_no: number; position: string; position_label: string; check_in_at: string | null }
  is_leader: boolean
  facilities: Facility[]
}

export interface Member {
  user_id: number
  bed_no: number
  position: string
  position_label: string
  name: string
  empty: boolean
  college: string | null
  class_name: string | null
  phone: string
  is_leader: boolean
  is_me: boolean
}

export interface MembersResult {
  room_id: number
  room: string
  capacity: number
  occupied: number
  can_edit: boolean
  is_leader: boolean
  items: Member[]
}

export interface AssetItem {
  id: number
  name: string
  status: string
  holder_name: string | null
  holder_is_me: boolean
  borrowed_at: string | null
  returned_at: string | null
  text: string
}

export interface DutyDay {
  id: number
  weekday: number
  weekday_cn: string
  date: string
  user_id: number | null
  user_name: string | null
  short_name: string | null
  areas: string[]
  is_today: boolean
  reminded: boolean
}

export interface DutySchedule {
  week_start: string
  week_no: number
  items: DutyDay[]
  today: DutyDay | null
  areas: string[]
  can_edit: boolean
  is_empty: boolean
  rule: { mode: string; member_order: number[]; areas: string[] }
}

export interface HygieneCheck {
  id: number
  check_date: string
  date_text: string
  week_no: number
  score: number
  level: string
  level_label: string
  deductions: { item: string; score: number }[]
  deduction_text: string
  requirement: string | null
  rectify_status: string
  rectify_media: string[]
  can_rectify: boolean
}

export interface HygieneResult extends Page<HygieneCheck> {
  average: number
  can_edit: boolean
}

/* ---------------- 公告 / 消息 ---------------- */

export interface Notice {
  id: number
  type: string
  type_label: string
  title: string
  summary: string
  content: string
  is_pinned: boolean
  require_receipt: boolean
  is_read: boolean
  receipt_at: string | null
  published_at: string
  date_text: string
  publisher: string
}

export interface NoticeList extends Page<Notice> {
  unread: number
  receipt_progress: { read: number; total: number; text: string }
}

export interface MessageItem {
  id: number
  type: string
  title: string
  content: string
  is_read: boolean
  biz_type: string | null
  biz_id: number | null
  created_at: string
  time_text: string
}

export interface MessageGroup {
  type: string
  label: string
  en: string
  total: number
  unread: number
  items: MessageItem[]
}

export interface MessageList {
  groups: MessageGroup[]
  items: MessageItem[]
  unread_total: number
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface MessagePreferences {
  sms_types: string[]
  wechat_types: string[]
  sms_on: boolean
  wechat_on: boolean
  note: string
}

/* ---------------- 个人 / 反馈 / 帮助 ---------------- */

export interface Profile {
  id: number
  name: string
  student_no: string | null
  worker_no: string | null
  role: string
  avatar_url: string | null
  gender: number
  college: string | null
  class_name: string | null
  grade: number | null
  email: string | null
  phone: string
  emergency_name: string | null
  emergency_phone: string | null
  verified: { student_no: string; college_class: string; dorm: string; readonly: boolean }
  security: { device_count: number; phone: string; emergency_text: string }
  subtitle: string
  version: string
}

export interface Feedback {
  id: number
  fb_no: string
  type: string
  type_label: string
  content: string
  media_urls: string[]
  status: string
  status_label: string
  reply: string | null
  replied_at: string | null
  satisfaction: number | null
  order_no: string | null
  created_text: string
  progress_text: string
  can_rate: boolean
}

export interface Faq {
  id: number
  category: string
  question: string
  answer: string
  is_self_help: boolean
  index: number
}

export interface Hotline {
  name: string
  phone: string
  time: string
  note?: string
}

export interface UploadResult {
  id: number
  url: string
  mime: string
  size: number
  instant: boolean
}
