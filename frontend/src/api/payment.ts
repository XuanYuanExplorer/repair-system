import { http } from './client'
import type { Bill, BillDetail, BillRecords, BillSummary, Page, PaymentCreated, TxnResult } from './types'

export const paymentApi = {
  summary: () => http.get<BillSummary>('/bills/summary'),

  list: (params: { status?: string; page?: number; page_size?: number }) => http.get<Page<Bill>>('/bills', { params }),

  detail: (id: number | string) => http.get<BillDetail>(`/bills/${id}`),

  records: (params?: { year?: string; type?: string }) => http.get<BillRecords>('/bills/records', { params }),

  applyReceipt: (billId: number, email?: string) =>
    http.post<{ id: number; status: string }>(`/bills/${billId}/receipt`, { email: email || null, title: '个人' }),

  receiptFile: (receiptId: number) => http.download(`/receipts/${receiptId}/file`, undefined, `receipt-${receiptId}.pdf`),

  exportRecords: () => http.download('/bills/records/export', undefined, 'bills.csv'),

  create: (billIds: number[], channel: string, idempotencyKey: string) =>
    http.post<PaymentCreated>('/payment/create', { bill_ids: billIds, channel }, { headers: { 'Idempotency-Key': idempotencyKey } }),

  txn: (txnNo: string) => http.get<TxnResult>(`/payment/transactions/${txnNo}`),

  mockPay: (txnNo: string, success = true) => http.post<{ txn_no: string; mock_status: string }>(`/payment/mock/pay?txn_no=${encodeURIComponent(txnNo)}&success=${success}`),
}
