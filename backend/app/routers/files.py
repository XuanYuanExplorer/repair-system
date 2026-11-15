"""文件上传：magic bytes 白名单 + 大小限制 + 随机文件名 + SHA256 去重。"""
import hashlib
import uuid
from datetime import date
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy import select

from app.config import settings
from app.core.errors import BizError, ErrCode
from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.models import File as FileModel

router = APIRouter(prefix="/files", tags=["文件"])

ALLOWED = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/webp": "webp",
    "video/mp4": "mp4",
}


def sniff_mime(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"mif1"):
        return "image/heic"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        return "video/mp4"
    return None


@router.post("", summary="上传图片 / 视频（返回可引用的 URL）")
async def upload(
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile = File(...),
    biz_type: str = Form(default="repair"),
):
    head = await file.read(2048)
    mime = sniff_mime(head)
    if mime not in ALLOWED:
        raise BizError(ErrCode.FILE_TYPE_UNSUPPORTED)
    limit_mb = settings.max_video_mb if mime.startswith("video") else settings.max_image_mb
    ext = ALLOWED[mime]
    name = f"{biz_type}/{date.today():%Y%m}/{uuid.uuid4().hex}.{ext}"
    path = Path(settings.upload_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)

    size = len(head)
    hasher = hashlib.sha256(head)
    async with aiofiles.open(path, "wb") as f:
        await f.write(head)
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit_mb * 1024 * 1024:
                await f.close()
                path.unlink(missing_ok=True)
                raise BizError(ErrCode.FILE_TOO_LARGE, f"文件超过 {limit_mb}MB 限制")
            hasher.update(chunk)
            await f.write(chunk)

    sha = hasher.hexdigest()
    existing = await session.scalar(
        select(FileModel).where(FileModel.sha256 == sha, FileModel.owner_id == user.id)
    )
    url = f"{settings.upload_base_url}/{name}"
    if existing:
        path.unlink(missing_ok=True)
        return ok({"id": existing.id, "url": existing.url, "mime": existing.mime, "size": existing.size, "instant": True})

    row = FileModel(owner_id=user.id, biz_type=biz_type, path=name, url=url, mime=mime, size=size, sha256=sha)
    session.add(row)
    await session.commit()
    return ok({"id": row.id, "url": row.url, "mime": mime, "size": size, "instant": False})

