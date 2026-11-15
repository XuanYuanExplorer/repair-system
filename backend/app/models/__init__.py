"""模型统一导出：Alembic / create_all 依赖此处的导入。"""
from app.models.bill import Bill, PaymentTransaction, PaymentTxnBill, Receipt
from app.models.common import AuditLog, File, OutboxEvent
from app.models.content import Faq, Notice, NoticeReceipt
from app.models.dorm import DormAsset, DormBed, DormFacility, DormRoom, DormRule, RoomChangeRequest
from app.models.duty import DutyRule, DutySchedule, HygieneCheck
from app.models.feedback import Feedback, FeedbackReply
from app.models.message import Message, MessagePreference, PushLog
from app.models.repair import RepairEvent, RepairMessage, RepairOrder, RepairRating, RepairSlot, RepairUrge
from app.models.user import LoginDevice, PasswordHistory, RefreshToken, User

__all__ = [
    "Bill",
    "PaymentTransaction",
    "PaymentTxnBill",
    "Receipt",
    "AuditLog",
    "File",
    "OutboxEvent",
    "Faq",
    "Notice",
    "NoticeReceipt",
    "DormAsset",
    "DormBed",
    "DormFacility",
    "DormRoom",
    "DormRule",
    "RoomChangeRequest",
    "DutyRule",
    "DutySchedule",
    "HygieneCheck",
    "Feedback",
    "FeedbackReply",
    "Message",
    "MessagePreference",
    "PushLog",
    "RepairEvent",
    "RepairMessage",
    "RepairOrder",
    "RepairRating",
    "RepairSlot",
    "RepairUrge",
    "LoginDevice",
    "PasswordHistory",
    "RefreshToken",
    "User",
]
