"""种子数据：与测试文档 §2.2 的账号矩阵和数据要点保持一致。

账号密码：学生 / 维修工 Abc123456，管理员 Admin@123。
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.seed_media import ensure_seed_photos
from app.core.timeutil import local_today, utcnow, week_start_of
from app.models import (
    Bill,
    DormAsset,
    DormBed,
    DormFacility,
    DormRoom,
    DormRule,
    DutyRule,
    DutySchedule,
    Faq,
    Feedback,
    HygieneCheck,
    Message,
    MessagePreference,
    Notice,
    NoticeReceipt,
    Receipt,
    RepairEvent,
    RepairMessage,
    RepairOrder,
    RepairRating,
    RepairSlot,
    User,
)

PWD = hash_password("Abc123456")
ADMIN_PWD = hash_password("Admin@123")


def at(day: date, hour: int = 9, minute: int = 0) -> datetime:
    """本地时间 → 库内 naive UTC。"""
    local = datetime.combine(day, time(hour, minute))
    return local - timedelta(hours=8)


async def seed(session: AsyncSession) -> None:
    if await session.scalar(select(func.count()).select_from(User)):
        return

    today = local_today()
    rnd = random.Random(20240612)
    ensure_seed_photos()

    # ---------------- 用户 ----------------
    admin = User(
        username="admin", name="宿管中心", phone="13900000000", password_hash=ADMIN_PWD,
        role="admin", status=1, email="dorm@example.edu",
    )
    worker = User(
        name="张建国", phone="13800000000", password_hash=PWD, role="worker", gender=1,
        worker_no="WX0087", worker_team="维修班组", status=1,
    )
    lin = User(
        student_no="20223601", name="林晓阳", phone="13888888880", password_hash=PWD, role="student", gender=1,
        college="计算机学院", class_name="2201", grade=2022, emergency_name="林父", emergency_phone="13912345521",
        email="linxy@example.edu", status=1,
    )
    wang = User(
        student_no="20223602", name="王一诺", phone="13888882210", password_hash=PWD, role="student", gender=1,
        college="计算机学院", class_name="2201", grade=2022, status=1,
    )
    li = User(
        student_no="20223603", name="李夏", phone="15011110917", password_hash=PWD, role="student", gender=1,
        college="软件工程", class_name="2202", grade=2022, status=1,
    )
    chen = User(
        student_no="20223604", name="陈屿", phone="18722223364", password_hash=PWD, role="student", gender=1,
        college="物联网工程", class_name="2203", grade=2022, status=1,
    )
    zhao = User(
        student_no="20223701", name="赵一鸣", phone="13655556666", password_hash=PWD, role="student", gender=1,
        college="机械工程学院", class_name="2104", grade=2021, status=1,
    )
    zhou = User(
        student_no="20223702", name="周予安", phone="13744445555", password_hash=PWD, role="student", gender=2,
        college="外国语学院", class_name="2101", grade=2021, status=1,
    )
    banned = User(
        student_no="20223801", name="孙浩", phone="13533334444", password_hash=PWD, role="student", gender=1,
        college="理学院", class_name="2002", grade=2020, status=0,
    )
    no_bed = User(
        student_no="20229999", name="未分配", phone="13422223333", password_hash=PWD, role="student", gender=1,
        college="化学工程学院", class_name="2205", grade=2022, status=1,
    )
    fresh = User(
        student_no="20223610", name="张可", phone="13211112222", password_hash="", role="student", gender=1,
        college="计算机学院", class_name="2204", grade=2022, status=1,
    )
    session.add_all([admin, worker, lin, wang, li, chen, zhao, zhou, banned, no_bed, fresh])
    await session.flush()

    # ---------------- 寝室 ----------------
    r412 = DormRoom(building="3号楼", room_no="412", floor=4, room_type="标准四人间", area=Decimal("22.0"), capacity=4, leader_id=wang.id)
    r201 = DormRoom(building="5号楼", room_no="201", floor=2, room_type="标准四人间", area=Decimal("20.5"), capacity=4, leader_id=zhao.id)
    r410 = DormRoom(building="3号楼", room_no="410", floor=4, room_type="标准四人间", area=Decimal("22.0"), capacity=4, leader_id=None)
    r305 = DormRoom(building="6号楼", room_no="305", floor=3, room_type="标准四人间", area=Decimal("21.0"), capacity=4, leader_id=zhou.id)
    session.add_all([r412, r201, r410, r305])
    await session.flush()

    session.add_all(
        [
            DormBed(room_id=r412.id, bed_no=1, position="upper", student_id=wang.id, check_in_at=date(2022, 9, 1)),
            DormBed(room_id=r412.id, bed_no=2, position="lower", student_id=li.id, check_in_at=date(2022, 9, 1)),
            DormBed(room_id=r412.id, bed_no=3, position="lower", student_id=lin.id, check_in_at=date(2022, 9, 1)),
            DormBed(room_id=r412.id, bed_no=4, position="upper", student_id=chen.id, check_in_at=date(2022, 9, 1)),
            DormBed(room_id=r201.id, bed_no=1, position="lower", student_id=zhao.id, check_in_at=date(2021, 9, 1)),
            DormBed(room_id=r410.id, bed_no=1, position="upper", student_id=fresh.id, check_in_at=date(2022, 9, 1)),
            DormBed(room_id=r305.id, bed_no=1, position="lower", student_id=zhou.id, check_in_at=date(2021, 9, 1)),
        ]
    )
    session.add_all(
        [
            DormFacility(room_id=r412.id, name="空调", category="ac", status="normal", enabled_year=2019),
            DormFacility(room_id=r412.id, name="热水器", category="water", status="fault", enabled_year=2019, fault_note="加热异常，水温不足"),
            DormFacility(room_id=r412.id, name="桌椅 · 衣柜", category="furniture", status="normal", enabled_year=2019),
            DormFacility(room_id=r412.id, name="卫浴", category="water", status="normal", enabled_year=2019),
            DormFacility(room_id=r201.id, name="空调", category="ac", status="normal", enabled_year=2021),
            DormFacility(room_id=r201.id, name="热水器", category="water", status="normal", enabled_year=2021),
        ]
    )
    session.add_all(
        [
            DormAsset(room_id=r412.id, name="吸尘器", holder_id=wang.id, borrowed_at=at(today - timedelta(days=4), 19, 20), status="borrowed"),
            DormAsset(room_id=r412.id, name="工具箱", holder_id=chen.id, borrowed_at=at(today - timedelta(days=12), 10, 0), returned_at=at(today - timedelta(days=10), 18, 0), status="available"),
        ]
    )
    for i, content in enumerate(
        [
            "23:00 后熄灯、佩戴耳机、保持安静",
            "值日按周轮换，当值日生负责全部区域",
            "访客 22:00 前离开，留宿须报备宿管",
            "公共物品用后归位，损坏主动申报",
        ],
        1,
    ):
        session.add(DormRule(room_id=r412.id, seq=i, content=content, updated_by=wang.id))

    # ---------------- 报修时段 ----------------
    for offset in range(0, 8):
        d = today + timedelta(days=offset)
        for building in ("3号楼", "5号楼", "6号楼"):
            for code, start, end in (("09-11", time(9), time(11)), ("14-16", time(14), time(16)), ("16-18", time(16), time(18))):
                booked = 0
                if building == "3号楼" and offset == 0:
                    booked = 6 if code == "14-16" else (2 if code == "16-18" else 1)
                session.add(
                    RepairSlot(building=building, slot_date=d, slot_code=code, start_time=start, end_time=end, capacity=6, booked=booked)
                )

    # ---------------- 工单 ----------------
    def add_order(
        *,
        no: str,
        category: str,
        desc: str,
        location: str,
        created: datetime,
        status: str,
        student: User = lin,
        room: DormRoom = r412,
        bed: int = 3,
        worker_id: int | None = None,
        material_fee: str = "0.00",
        slot: str | None = None,
        slot_date: date | None = None,
        fix_note: str | None = None,
        done_at: datetime | None = None,
    ) -> RepairOrder:
        order = RepairOrder(
            order_no=no,
            student_id=student.id,
            room_id=room.id,
            bed_no=bed,
            category=category,
            location_type="in_room" if location.startswith(room.building) else "public",
            location_desc=location,
            description=desc,
            media_urls=([f"/uploads/seed/photo-{i}.png" for i in (1, 2, 3)] if category == "ac" else []),
            preferred_date=slot_date,
            preferred_slot=slot,
            require_presence=1,
            contact_phone=student.phone,
            status=status,
            worker_id=worker_id,
            created_at=created,
            updated_at=created,
            material_fee=Decimal(material_fee),
            fix_note=fix_note,
            done_at=done_at,
        )
        session.add(order)
        return order

    day0 = today
    o371 = add_order(
        no="WX" + day0.strftime("%Y%m%d") + "-0371",
        category="ac",
        desc="空调启动后不制冷，出常温风，已连续运转 2 小时，过滤网近期清洗过。",
        location="3号楼412室·室内—空调主机",
        created=at(day0, 9, 41),
        status="fixing",
        worker_id=worker.id,
        material_fee="36.00",
        slot="16-18",
        slot_date=day0,
    )
    o371.expect_finish_at = at(day0, 18, 0)
    o371.assigned_at = at(day0, 9, 58)
    o371.accepted_at = at(day0, 10, 15)
    o371.started_at = at(day0, 16, 5)
    await session.flush()
    session.add_all(
        [
            RepairEvent(order_id=o371.id, event_type="submit", to_status="pending", actor_id=lin.id, actor_name=lin.name, actor_role="student", note="附 3 张照片", created_at=at(day0, 9, 41)),
            RepairEvent(order_id=o371.id, event_type="assign", from_status="pending", to_status="assigned", actor_id=admin.id, actor_name="宿管中心", actor_role="admin", note="已派单", created_at=at(day0, 9, 58)),
            RepairEvent(order_id=o371.id, event_type="accept_job", from_status="assigned", to_status="fixing", actor_id=worker.id, actor_name=worker.name, actor_role="worker", created_at=at(day0, 10, 15)),
            RepairEvent(order_id=o371.id, event_type="comment", from_status="fixing", to_status="fixing", actor_id=worker.id, actor_name=worker.name, actor_role="worker", note="已备料：压缩机电容 ×1", created_at=at(day0, 10, 16)),
        ]
    )
    session.add(
        RepairMessage(order_id=o371.id, sender_id=worker.id, sender_role="worker", content="已到楼下，马上上来", created_at=at(day0, 16, 2))
    )

    o215 = add_order(
        no="WX20240528-0215", category="water", desc="卫生间水龙头接口漏水，持续滴水，地面已积水。",
        location="3号楼412室·卫生间—水龙头", created=at(date(2024, 5, 28), 15, 40), status="done",
        worker_id=worker.id, material_fee="36.00", fix_note="更换水龙头阀芯，试水正常", done_at=at(date(2024, 5, 29), 10, 20),
    )
    o098 = add_order(
        no="WX20240410-0098", category="furniture", desc="书桌抽屉滑轨脱落，抽屉无法正常推拉。",
        location="3号楼412室·室内—书桌", created=at(date(2024, 4, 10), 20, 12), status="done",
        worker_id=worker.id, fix_note="更换滑轨一副", done_at=at(date(2024, 4, 12), 16, 30),
    )
    o_verify = add_order(
        no="WX20240610-0362", category="door", desc="寝室门锁芯卡顿，钥匙转动困难，需要多次尝试才能开锁。",
        location="3号楼412室·室内—门锁", created=at(today - timedelta(days=2), 8, 30), status="verify",
        worker_id=worker.id, material_fee="36.00", fix_note="更换门锁芯，测试开关顺畅",
    )
    o_verify.fixed_at = at(today - timedelta(days=1), 17, 0)
    o_assigned = add_order(
        no="WX" + (today - timedelta(days=1)).strftime("%Y%m%d") + "-0358", category="network",
        desc="寝室内网口无法上网，指示灯不亮，已排除网线问题。", location="3号楼412室·室内—网口",
        created=at(today - timedelta(days=1), 19, 10), status="assigned", worker_id=worker.id,
    )
    o_assigned.assigned_at = at(today - timedelta(days=1), 19, 40)
    o_pending = add_order(
        no="WX" + today.strftime("%Y%m%d") + "-0374", category="water",
        desc="热水器加热到 40 度左右就不再升温，洗澡水温不够。", location="3号楼412室·室内—热水器",
        created=at(today, 8, 15), status="pending",
    )
    o_cancel1 = add_order(
        no="WX20240305-0042", category="furniture", desc="衣柜门合页松动，柜门关不严。", location="3号楼412室·室内—衣柜",
        created=at(date(2024, 3, 5), 12, 0), status="cancelled",
    )
    o_cancel1.cancelled_at = at(date(2024, 3, 5), 13, 10)
    o_cancel1.cancel_reason = "自行修复"
    o_cancel2 = add_order(
        no="WX20231211-0912", category="public", desc="公共洗衣房 2 号机排水不畅，积水严重。", location="3号楼·公共区域—洗衣房",
        created=at(date(2023, 12, 11), 9, 0), status="cancelled",
    )
    o_cancel2.cancelled_at = at(date(2023, 12, 11), 10, 0)
    o_cancel2.cancel_reason = "重复提交，已合并处理"

    # 其余历史工单：覆盖 6 个类别与多种状态，凑满 26 条
    history_specs = [
        ("water", "洗手池下水缓慢，积水约 2 厘米。", "卫生间—洗手池"),
        ("water", "淋浴喷头出水不均，多个孔位堵塞。", "卫生间—淋浴"),
        ("water", "阳台地漏返味，偶尔有污水上涌。", "阳台—地漏"),
        ("water", "热水器指示灯不亮，无法加热。", "室内—热水器"),
        ("water", "水表读数与实际用水量差异较大。", "室内—水表"),
        ("door", "阳台推拉门轨道变形，推拉费力。", "阳台—推拉门"),
        ("door", "寝室门把手松动，螺丝滑丝。", "室内—门把手"),
        ("door", "窗户限位器损坏，无法固定开启角度。", "室内—窗户"),
        ("network", "无线网络信号弱，频繁断连。", "室内—路由器"),
        ("network", "网络延迟高，晚高峰无法正常上课。", "室内—网口"),
        ("furniture", "床板横梁异响，翻身声音较大。", "室内—床铺"),
        ("ac", "空调遥控器失灵，无法调节温度。", "室内—空调遥控器"),
        ("water", "卫生间排风扇噪音大。", "卫生间—排风扇"),
        ("door", "防盗链脱扣，无法正常挂上。", "室内—门链"),
        ("network", "校园网认证失败，提示账号异常。", "室内—网络"),
        ("furniture", "椅子靠背断裂，存在安全隐患。", "室内—椅子"),
        ("water", "洗手池水龙头出水小。", "卫生间—水龙头"),
        ("door", "纱窗破损，蚊虫进入。", "阳台—纱窗"),
    ]
    historical = []
    base_day = today - timedelta(days=35)
    for idx, (cat, desc, loc) in enumerate(history_specs):
        d = base_day - timedelta(days=idx * 21 + rnd.randint(0, 6))
        st = "done" if idx % 5 != 0 else "done"
        o = add_order(
            no=f"WX{d.strftime('%Y%m%d')}-{1000 + idx * 7}",
            category=cat,
            desc=desc,
            location=f"3号楼412室·{loc}",
            created=at(d, 9 + idx % 8, 10 + idx % 40),
            status=st,
            worker_id=worker.id,
            fix_note="已处理并测试正常",
            done_at=at(d + timedelta(days=1), 15, 0),
        )
        historical.append((o, d, idx))

    await session.flush()

    # 评价：0215 / 0098 / 部分历史工单
    session.add(
        RepairRating(order_id=o215.id, student_id=lin.id, worker_id=worker.id, speed=5, attitude=5, quality=4,
                     avg_score=Decimal("4.7"), content="上门及时，一次修好", is_anonymous=0, created_at=at(date(2024, 5, 30), 9, 0))
    )
    session.add(
        RepairRating(order_id=o098.id, student_id=lin.id, worker_id=worker.id, speed=5, attitude=5, quality=5,
                     avg_score=Decimal("5.0"), content="处理稍慢，态度很好", is_anonymous=0, created_at=at(date(2024, 4, 13), 10, 0))
    )
    for o, d, idx in historical[:8]:
        score = Decimal(str([5.0, 4.7, 4.3, 5.0, 4.0, 4.7, 5.0, 4.3][idx % 8]))
        session.add(
            RepairRating(order_id=o.id, student_id=lin.id, worker_id=worker.id, speed=5, attitude=5, quality=4,
                         avg_score=score, content=None, is_anonymous=1, created_at=at(d + timedelta(days=2), 12, 0))
        )

    # ---------------- 账单 ----------------
    def bill(no, type_, period, title, amount, due, status, owner=lin, room=r412, bed=3, detail=None, late="0.00",
             overdue_days=0, source_id=None, paid_at=None):
        b = Bill(
            bill_no=no, student_id=owner.id, room_id=room.id if room else None, bed_no=bed, type=type_, period=period,
            title=title, amount=Decimal(amount), late_fee=Decimal(late), due_date=due, status=status,
            detail=detail, overdue_days=overdue_days, source_type="repair_order" if source_id else None,
            source_id=source_id, paid_at=paid_at,
        )
        session.add(b)
        return b

    b1 = bill(
        "B202405-0158", "electricity", f"{today.year}-05", f"超定额电费 · {today.year} 年 5 月", "158.00", today + timedelta(days=3), "unpaid",
        detail={
            "meter_reading": "06-01 09:00 · 远传表计",
            "items": [
                {"label": "本月用量", "value": "239", "unit": "度"},
                {"label": "免费定额", "value": "160", "unit": "度"},
                {"label": "超额电量", "value": "79", "unit": "度 × ¥2.00"},
            ],
            "formula": "（239 − 160）× 2.00 元/度",
            "remark": "按《学生宿舍水电管理办法》第十一条执行",
        },
    )
    bill(
        "B202406-1200", "accommodation", "2023-2024 春季学期", "住宿费 · 2023–2024 春季学期", "1200.00",
        today + timedelta(days=18), "unpaid",
        detail={"items": [{"label": "学年标准", "value": "1200.00", "unit": "元"}], "remark": "按学年一次性收取"},
    )
    bill(
        "B202406-0036", "material", f"{today.year}-06", "维修材料费 · 工单 0371", "36.00", today + timedelta(days=16), "unpaid",
        detail={"items": [{"label": "压缩机电容", "value": "36.00", "unit": "元"}], "remark": "工单完工确认后生成"},
        source_id=o371.id,
    )

    paid_specs = [
        ("B202406-0102", "water", f"{today.year}-06", "水费 · 6 月", "42.00", 3, "wechat"),
        ("B202406-0091", "electricity", f"{today.year}-06", "超定额电费 · 6 月", "88.00", 9, "campus_card"),
        ("B202405-0077", "electricity", f"{today.year}-05", "超定额电费 · 5 月", "136.00", 33, "wechat"),
        ("B202405-0065", "accommodation", "2023-2024 秋季学期", "住宿费 · 秋季学期", "1200.00", 41, "campus_card"),
        ("B202404-0051", "water", f"{today.year}-04", "水费 · 4 月", "36.00", 62, "alipay"),
        ("B202404-0044", "electricity", f"{today.year}-04", "超定额电费 · 4 月", "104.00", 70, "wechat"),
        ("B202403-0031", "electricity", f"{today.year}-03", "超定额电费 · 3 月", "96.00", 98, "wechat"),
        ("B202403-0022", "water", f"{today.year}-03", "水费 · 3 月", "48.00", 105, "alipay"),
        ("B202402-0019", "electricity", f"{today.year}-02", "超定额电费 · 2 月", "72.00", 126, "wechat"),
        ("B202401-0012", "water", f"{today.year}-01", "水费 · 1 月", "40.00", 158, "campus_card"),
        ("B202312-0009", "electricity", f"{today.year - 1}-12", "超定额电费 · 12 月", "118.00", 190, "wechat"),
        ("B202311-0007", "material", f"{today.year - 1}-11", "维修材料费 · 工单 0215", "36.00", 210, "alipay"),
        ("B202311-0006", "water", f"{today.year - 1}-11", "水费 · 11 月", "44.00", 220, "wechat"),
        ("B202310-0004", "electricity", f"{today.year - 1}-10", "超定额电费 · 10 月", "86.00", 250, "wechat"),
        ("B202309-0002", "accommodation", "2022-2023 学年补缴", "住宿费补缴", "200.00", 280, "campus_card"),
        ("B202309-0001", "water", f"{today.year - 1}-09", "水费 · 9 月", "38.00", 300, "alipay"),
        ("B202308-0001", "electricity", f"{today.year - 1}-08", "超定额电费 · 8 月", "66.00", 330, "wechat"),
        ("B202307-0001", "penalty", f"{today.year - 1}-07", "违规电器罚金", "50.00", 360, "wechat"),
    ]
    for idx, (no, type_, period, title, amount, days_ago, channel) in enumerate(paid_specs):
        paid_day = today - timedelta(days=days_ago)
        b = bill(
            no, type_, period, title, amount, paid_day, "paid",
            detail={"items": [{"label": "应缴金额", "value": amount, "unit": "元"}]},
            paid_at=at(paid_day, 10, 12),
        )
        b.updated_at = at(paid_day, 10, 12)

    # 逾期账单：周予安（测试文档 20223702）
    bill(
        "B202311-0088", "water", f"{today.year - 1}-11", "水费 · 11 月", "42.00", today - timedelta(days=5), "overdue",
        owner=zhou, room=r305, bed=1, late="2.00", overdue_days=5,
        detail={"items": [{"label": "应缴金额", "value": "42.00", "unit": "元"}]},
    )

    # 票据（已缴账单中部分已开票）
    paid_bills = (await session.scalars(select(Bill).where(Bill.student_id == lin.id, Bill.status == "paid").order_by(Bill.paid_at.desc()))).all()
    for idx, b in enumerate(paid_bills[:6]):
        session.add(
            Receipt(
                receipt_no=f"RC{b.paid_at.strftime('%Y%m%d')}{b.id:04d}",
                bill_id=b.id,
                title="个人",
                email=lin.email,
                status="sent" if idx % 2 == 0 else "issued",
                file_url=f"/uploads/receipts/RC{b.paid_at.strftime('%Y%m%d')}{b.id:04d}.pdf",
                issued_at=b.paid_at,
            )
        )

    # ---------------- 公告 ----------------
    n_pinned = Notice(
        scope="all", type="check", title="安全大查寝通知", is_pinned=1, require_receipt=1,
        content="本周四 21:00 开展消防安全检查，请留在寝室配合，检查违规电器。\n检查范围：3 号楼、5 号楼全部寝室。\n请提前整理插线板与大功率电器，违规物品将统一登记保管。",
        publisher_name="宿管中心", published_at=at(today - timedelta(days=2), 16, 0),
    )
    n_water = Notice(
        scope="building", building="3号楼", type="utility", title="3 号楼停水检修通知",
        content="6 月 15 日 08:00–16:00 对 3 号楼给水管道进行检修，期间暂停供水。\n请提前储备生活用水，检修完成后自动恢复。",
        publisher_name="宿管中心", published_at=at(today - timedelta(days=1), 9, 30),
    )
    n_ac = Notice(
        scope="all", type="notice", title="空调滤网集中清洗安排",
        content="后勤处将于下周对 3 号楼空调滤网进行集中清洗，具体时间以楼层通知为准。\n清洗期间请留人在寝室配合。",
        publisher_name="后勤处", published_at=at(today - timedelta(days=5), 14, 0),
    )
    n_expired = Notice(
        scope="all", type="notice", title="寒假封楼通知",
        content="寒假期间宿舍楼封闭管理，封楼时间以校历为准。",
        publisher_name="宿管中心", published_at=at(today - timedelta(days=90), 10, 0),
        expire_at=at(today - timedelta(days=30), 10, 0),
    )
    session.add_all([n_pinned, n_water, n_ac, n_expired])
    await session.flush()
    session.add_all(
        [
            NoticeReceipt(notice_id=n_water.id, user_id=lin.id, is_read=1, read_at=at(today - timedelta(days=1), 12, 0)),
            NoticeReceipt(notice_id=n_ac.id, user_id=lin.id, is_read=1, read_at=at(today - timedelta(days=4), 9, 0)),
        ]
    )

    # ---------------- FAQ ----------------
    session.add_all(
        [
            Faq(category="报修", question="报修后多久上门？", sort=1, is_self_help=False,
                answer="一般工单 24 小时内响应，水电类急修 4 小时内上门，可在工单详情页实时查看进度。"),
            Faq(category="报修", question="跳闸后如何复位？", sort=2, is_self_help=True,
                answer="打开门口配电箱，先拔掉大功率电器，再按下漏电保护器蓝色复位按钮；仍跳闸请报修「水电」类。"),
            Faq(category="报修", question="水龙头漏水如何临时关阀？", sort=3, is_self_help=True,
                answer="关闭洗手池下方的角阀（顺时针旋转），若角阀失效请关闭室内总阀并立即报修。"),
            Faq(category="缴费", question="电费定额与计价方式？", sort=4, is_self_help=False,
                answer="每人每月免费定额 40 度，超出部分按 2.00 元/度计费，账期结束后 5 个工作日内生成账单。"),
            Faq(category="缴费", question="电子票据如何开具与发送邮箱？", sort=5, is_self_help=False,
                answer="在「缴费记录」中选择已缴账单，点击「申请票据」填写邮箱，系统将在 5 分钟内开具并发送 PDF 票据。"),
        ]
    )

    # ---------------- 消息 ----------------
    unread_specs = [
        ("order", "工单 0371 已派单", "张建国师傅已接单，预计 18:00 上门", 1),
        ("order", "师傅已到达楼下", "请提前准备开门并清理工位", 2),
        ("order", "维修进度更新", "已备料：压缩机电容 ×1，即将上门", 3),
        ("bill", "账单到期提醒", "超定额电费 · 2026 年 5 月 · ¥158.00 · 剩 3 天", 5),
        ("notice", "周四 21:00 安全查寝", "请配合留寝，检查违规电器", 26),
        ("notice", "3 号楼停水检修", "6 月 15 日 08:00–16:00 停水，请提前储水", 30),
    ]
    for idx, (t, title, content, hours_ago) in enumerate(unread_specs):
        session.add(
            Message(
                user_id=lin.id, type=t, title=title, content=content, is_read=0,
                biz_type="bill_due" if idx == 3 else None,
                biz_id=b1.id if idx == 3 else None,
                created_at=utcnow() - timedelta(hours=hours_ago),
            )
        )
    read_specs = [
        ("paid", "¥158.00 支付成功", "超定额电费 · 5 月 · 已到账"),
        ("order", "工单已完成", "WX20240528-0215 已完成，欢迎评价"),
        ("order", "工单已受理", "WX20240528-0215 已受理"),
        ("bill", "账单已生成", "住宿费 · 春季学期 ¥1,200.00"),
        ("notice", "空调滤网集中清洗安排", "下周集中清洗，请留人配合"),
        ("system", "欢迎使用宿舍服务平台", "已为你绑定 3 号楼 412 室 · 床位 3"),
    ]
    for idx, (t, title, content) in enumerate(read_specs):
        session.add(
            Message(user_id=lin.id, type=t, title=title, content=content, is_read=1, read_at=utcnow() - timedelta(days=2),
                    created_at=utcnow() - timedelta(days=3, hours=idx))
        )
    for i in range(6):
        session.add(
            Message(user_id=lin.id, type="system", title="服务公告", content="平台已完成例行维护。", is_read=1,
                    read_at=utcnow() - timedelta(days=9), created_at=utcnow() - timedelta(days=10, hours=i))
        )
    session.add(MessagePreference(user_id=lin.id, sms_types=["bill", "notice"], wechat_types=["bill", "notice"]))
    session.add(MessagePreference(user_id=wang.id, sms_types=["bill"], wechat_types=["bill", "notice"]))

    # ---------------- 值日与卫生 ----------------
    anchor = today - timedelta(days=2)  # 使今日轮值到 林晓阳
    session.add(
        DutyRule(
            room_id=r412.id, mode="daily", member_order=[wang.id, li.id, lin.id, chen.id],
            areas=["地面", "桌面", "阳台", "卫浴"], anchor_date=anchor,
        )
    )
    week_start = week_start_of(today)
    for i in range(7):
        d = week_start + timedelta(days=i)
        idx = (d - anchor).days % 4
        session.add(
            DutySchedule(
                room_id=r412.id, week_start=week_start, weekday=i + 1,
                user_id=[wang.id, li.id, lin.id, chen.id][idx], duty_date=d,
                areas=["地面", "桌面", "阳台", "卫浴"],
                reminded_at=at(today, 8, 0) if d == today else None,
            )
        )

    session.add_all(
        [
            HygieneCheck(room_id=r412.id, check_date=today - timedelta(days=4), week_no=14, score=92, level="excellent",
                         deductions=[], inspector="宿管中心", rectify_status="none"),
            HygieneCheck(room_id=r412.id, check_date=today - timedelta(days=11), week_no=13, score=85, level="good",
                         deductions=[{"item": "阳台堆物", "score": -5}], requirement="清理阳台堆物，保持通道畅通",
                         inspector="宿管中心", rectify_status="required"),
            HygieneCheck(room_id=r412.id, check_date=today - timedelta(days=18), week_no=12, score=90, level="good",
                         deductions=[], inspector="宿管中心", rectify_status="none"),
        ]
    )

    # ---------------- 反馈 ----------------
    session.add_all(
        [
            Feedback(fb_no="FB0612-02", user_id=lin.id, type="charge", order_id=o371.id, status="submitted",
                     content="工单 0371 生成了 ¥36.00 材料费账单，但空调仍在保修期内，请核实费用是否应收取。",
                     created_at=at(today - timedelta(days=1), 20, 0)),
            Feedback(fb_no="FB0520-11", user_id=lin.id, type="suggestion", status="replied",
                     content="建议在每层走廊增加共享雨伞架，梅雨季非常需要。",
                     reply="已纳入暑期改造计划，感谢建议。", replied_at=at(today - timedelta(days=20), 10, 0),
                     satisfaction=5, created_at=at(today - timedelta(days=24), 15, 0)),
        ]
    )

    await session.commit()
