"""业务错误：HTTP 表达语义，code 表达具体原因（见后端文档 7.3）。"""
from enum import IntEnum


class ErrCode(IntEnum):
    OK = 0
    # 1xxx 认证与通用
    UNAUTHORIZED = 1001
    TOKEN_INVALID = 1002
    FORBIDDEN = 1003
    RATE_LIMITED = 1004
    NOT_FOUND = 1404
    # 2xxx 账号
    STUDENT_NOT_FOUND = 2001
    DORM_NOT_MATCHED = 2002
    SMS_CODE_INVALID = 2003
    PASSWORD_REUSED = 2004
    BAD_CREDENTIALS = 2005
    ACCOUNT_LOCKED = 2006
    ACCOUNT_DISABLED = 2007
    STUDENT_EXISTS = 2008
    BED_OCCUPIED = 2009
    WEAK_PASSWORD = 2010
    # 3xxx 报修
    ORDER_STATE_INVALID = 3001
    SLOT_FULL = 3002
    URGE_TOO_FREQUENT = 3003
    MEDIA_LIMIT = 3004
    ORDER_LOCKED = 3005
    RATE_CLOSED = 3006
    ALREADY_RATED = 3007
    # 4xxx 账单支付
    BILL_ALREADY_PAID = 4001
    PENALTY_NOT_MERGEABLE = 4002
    TXN_CLOSED = 4003
    GATEWAY_UNAVAILABLE = 4004
    AMOUNT_MISMATCH = 4005
    # 5xxx 通用资源
    FILE_TYPE_UNSUPPORTED = 5001
    FILE_TOO_LARGE = 5002
    NOT_VERIFIED = 5003
    CONFLICT = 5004
    # 9xxx
    INTERNAL = 9000


HTTP_STATUS: dict[int, int] = {
    ErrCode.OK: 200,
    ErrCode.UNAUTHORIZED: 401,
    ErrCode.TOKEN_INVALID: 401,
    ErrCode.FORBIDDEN: 403,
    ErrCode.RATE_LIMITED: 429,
    ErrCode.NOT_FOUND: 404,
    ErrCode.STUDENT_NOT_FOUND: 422,
    ErrCode.DORM_NOT_MATCHED: 422,
    ErrCode.SMS_CODE_INVALID: 422,
    ErrCode.PASSWORD_REUSED: 422,
    ErrCode.BAD_CREDENTIALS: 401,
    ErrCode.ACCOUNT_LOCKED: 423,
    ErrCode.ACCOUNT_DISABLED: 403,
    ErrCode.STUDENT_EXISTS: 409,
    ErrCode.BED_OCCUPIED: 409,
    ErrCode.WEAK_PASSWORD: 422,
    ErrCode.ORDER_STATE_INVALID: 409,
    ErrCode.SLOT_FULL: 409,
    ErrCode.URGE_TOO_FREQUENT: 429,
    ErrCode.MEDIA_LIMIT: 422,
    ErrCode.ORDER_LOCKED: 422,
    ErrCode.RATE_CLOSED: 409,
    ErrCode.ALREADY_RATED: 409,
    ErrCode.BILL_ALREADY_PAID: 409,
    ErrCode.PENALTY_NOT_MERGEABLE: 422,
    ErrCode.TXN_CLOSED: 409,
    ErrCode.GATEWAY_UNAVAILABLE: 502,
    ErrCode.AMOUNT_MISMATCH: 422,
    ErrCode.FILE_TYPE_UNSUPPORTED: 415,
    ErrCode.FILE_TOO_LARGE: 413,
    ErrCode.NOT_VERIFIED: 422,
    ErrCode.CONFLICT: 409,
    ErrCode.INTERNAL: 500,
}

DEFAULT_MESSAGES: dict[int, str] = {
    ErrCode.UNAUTHORIZED: "请先登录",
    ErrCode.TOKEN_INVALID: "登录状态已失效，请重新登录",
    ErrCode.FORBIDDEN: "无操作权限",
    ErrCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
    ErrCode.NOT_FOUND: "资源不存在",
    ErrCode.STUDENT_NOT_FOUND: "学号不存在或非本校在册学生",
    ErrCode.DORM_NOT_MATCHED: "未匹配到住宿记录，请联系宿管",
    ErrCode.SMS_CODE_INVALID: "验证码错误或已过期",
    ErrCode.PASSWORD_REUSED: "新密码与最近 3 次使用过的密码重复",
    ErrCode.BAD_CREDENTIALS: "账号或密码错误",
    ErrCode.ACCOUNT_LOCKED: "登录失败次数过多，账号已锁定 15 分钟",
    ErrCode.ACCOUNT_DISABLED: "账号已停用，请联系宿管中心",
    ErrCode.STUDENT_EXISTS: "该学号已注册，请直接登录",
    ErrCode.BED_OCCUPIED: "床位已被占用，请联系宿管",
    ErrCode.WEAK_PASSWORD: "密码强度不足：至少 6 位且包含字母与数字",
    ErrCode.ORDER_STATE_INVALID: "当前状态不允许该操作，请刷新后重试",
    ErrCode.SLOT_FULL: "该时段已约满，请选择其他时段",
    ErrCode.URGE_TOO_FREQUENT: "催单过于频繁，请稍后再试",
    ErrCode.MEDIA_LIMIT: "照片数量或大小超出限制",
    ErrCode.ORDER_LOCKED: "工单已开工，不可修改或取消",
    ErrCode.RATE_CLOSED: "评价已关闭",
    ErrCode.ALREADY_RATED: "该工单已评价",
    ErrCode.BILL_ALREADY_PAID: "账单已支付",
    ErrCode.PENALTY_NOT_MERGEABLE: "罚金账单不支持合并支付",
    ErrCode.TXN_CLOSED: "支付单已关闭或超时，请重新发起",
    ErrCode.GATEWAY_UNAVAILABLE: "支付网关查询失败，请稍后刷新",
    ErrCode.AMOUNT_MISMATCH: "支付金额与账单不符，请重新下单",
    ErrCode.FILE_TYPE_UNSUPPORTED: "文件类型不支持",
    ErrCode.FILE_TOO_LARGE: "文件超过大小限制",
    ErrCode.NOT_VERIFIED: "未完成实名/认证",
    ErrCode.CONFLICT: "数据已变更，请刷新后重试",
    ErrCode.INTERNAL: "服务器内部错误",
}


class BizError(Exception):
    def __init__(self, code: ErrCode | int, message: str | None = None, data=None, *, http_status: int | None = None):
        self.code = int(code)
        self.message = message or DEFAULT_MESSAGES.get(self.code, "请求失败")
        self.data = data
        self.http_status = http_status or HTTP_STATUS.get(self.code, 400)
        super().__init__(self.message)


class GatewayError(Exception):
    """外部网关异常（支付/短信），由 service 转成 4004。"""
