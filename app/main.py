import os, uuid, hashlib, secrets, mimetypes, asyncio, zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, String, Integer, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "files"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'mistport.db'}")
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "2048"))
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class StoredFile(Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(512))
    stored_name: Mapped[str] = mapped_column(String(128), unique=True)
    size: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str] = mapped_column(String(255), default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    share_code: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    downloads: Mapped[int] = mapped_column(Integer, default=0)

Base.metadata.create_all(engine)
app = FastAPI(title="MistPort 文件传输", version="2.2.0")

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def safe_name(name: str) -> str:
    name = Path(name.replace("\\", "/")).name
    name = "".join(c for c in name if c.isalnum() or c in " ._-()[]")
    return name[:240] or "download"

def remove_expired(db: Session) -> int:
    now = datetime.utcnow()
    rows = db.scalars(select(StoredFile).where(StoredFile.expires_at <= now)).all()
    for item in rows:
        (UPLOAD_DIR / item.stored_name).unlink(missing_ok=True)
        db.delete(item)
    if rows:
        db.commit()
    return len(rows)

def new_receive_code(db: Session) -> str:
    # Codes belonging to unexpired files remain reserved. Expired codes may be reused.
    now = datetime.utcnow()
    for _ in range(1000):
        code = f"{secrets.randbelow(1_000_000):06d}"
        exists = db.scalar(
            select(StoredFile.id).where(
                StoredFile.share_code == code,
                StoredFile.expires_at > now
            ).limit(1)
        )
        if not exists:
            return code
    raise HTTPException(503, "暂时无法生成接收码，请稍后重试")

async def cleanup_expired():
    while True:
        try:
            with SessionLocal() as db:
                remove_expired(db)
        except Exception as exc:
            print(f"[cleanup] {exc}", flush=True)
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_cleanup():
    app.state.cleanup_task = asyncio.create_task(cleanup_expired())

@app.on_event("shutdown")
async def stop_cleanup():
    task = getattr(app.state, "cleanup_task", None)
    if task:
        task.cancel()

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "MistPort", "version": "2.2.0"}

@app.post("/api/upload")
async def upload(
    files: list[UploadFile] = File(...),
    expiry_hours: int = Form(1),
    upload_kind: str = Form("files")
):
    if expiry_hours not in (1, 3, 6, 12, 24):
        raise HTTPException(400, "有效期只能选择 1、3、6、12 或 24 小时")
    if upload_kind not in ("files", "folder"):
        raise HTTPException(400, "不支持的上传类型")
    results = []

    # A folder is kept as one ZIP package so its directory structure survives download.
    if upload_kind == "folder":
        if not files:
            raise HTTPException(400, "文件夹为空")
        fid = str(uuid.uuid4())
        stored = f"{fid}.blob"
        target = UPLOAD_DIR / stored
        total_size = 0
        folder_name = "文件夹"
        try:
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for up in files:
                    raw_path = (up.filename or "file").replace("\\", "/")
                    parts = [part for part in raw_path.split("/") if part not in ("", ".", "..")]
                    if not parts:
                        continue
                    if len(parts) > 1 and folder_name == "文件夹":
                        folder_name = safe_name(parts[0])
                    relative_path = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
                    if not relative_path:
                        relative_path = parts[-1]
                    with archive.open(relative_path, "w") as member:
                        while chunk := await up.read(1024 * 1024):
                            total_size += len(chunk)
                            if total_size > MAX_FILE_MB * 1024 * 1024:
                                raise HTTPException(413, f"文件夹总大小超过 {MAX_FILE_MB} MB 限制")
                            member.write(chunk)
            if total_size == 0:
                raise HTTPException(400, "文件夹中没有可上传的文件")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            with SessionLocal() as db:
                remove_expired(db)
                code = new_receive_code(db)
                now = datetime.utcnow()
                item = StoredFile(
                    id=fid, original_name=f"{folder_name}.zip", stored_name=stored,
                    size=target.stat().st_size, mime="application/zip", sha256=digest,
                    created_at=now, expires_at=now + timedelta(hours=expiry_hours),
                    share_code=code, downloads=0
                )
                db.add(item); db.commit()
                results.append({"name": item.original_name, "size": item.size, "code": item.share_code,
                    "created_at": item.created_at.isoformat() + "Z", "expires_at": item.expires_at.isoformat() + "Z",
                    "expiry_hours": expiry_hours})
        except Exception:
            target.unlink(missing_ok=True)
            raise
    else:
        for up in files:
            fid = str(uuid.uuid4())
            stored = f"{fid}.blob"
            target = UPLOAD_DIR / stored
            h = hashlib.sha256()
            size = 0
            try:
                with target.open("wb") as out:
                    while chunk := await up.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_FILE_MB * 1024 * 1024:
                            raise HTTPException(413, f"单个文件超过 {MAX_FILE_MB} MB 限制")
                        h.update(chunk); out.write(chunk)
            except Exception:
                target.unlink(missing_ok=True)
                raise
            try:
                with SessionLocal() as db:
                    remove_expired(db)
                    code = new_receive_code(db)
                    now = datetime.utcnow()
                    item = StoredFile(id=fid, original_name=safe_name(up.filename or "download"), stored_name=stored,
                        size=size, mime=up.content_type or mimetypes.guess_type(up.filename or "")[0] or "application/octet-stream",
                        sha256=h.hexdigest(), created_at=now, expires_at=now + timedelta(hours=expiry_hours),
                        share_code=code, downloads=0)
                    db.add(item); db.commit()
                    results.append({"name": item.original_name, "size": item.size, "code": item.share_code,
                        "created_at": item.created_at.isoformat() + "Z", "expires_at": item.expires_at.isoformat() + "Z",
                        "expiry_hours": expiry_hours})
            except Exception:
                target.unlink(missing_ok=True)
                raise
    return {"files": results, "message": "上传成功，接收码已生成"}

from pydantic import BaseModel

class ReceiveRequest(BaseModel):
    code: str

@app.post("/api/receive")
def receive(body: ReceiveRequest):
    code = body.code.strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(400, "请输入 6 位数字接收码")
    with SessionLocal() as db:
        f = db.scalar(select(StoredFile).where(StoredFile.share_code == code))
        if not f:
            raise HTTPException(404, "接收码不存在或已失效")
        if f.expires_at <= datetime.utcnow():
            (UPLOAD_DIR / f.stored_name).unlink(missing_ok=True)
            db.delete(f)
            db.commit()
            raise HTTPException(410, "文件已过期并自动删除")
        path = UPLOAD_DIR / f.stored_name
        if not path.exists():
            db.delete(f)
            db.commit()
            raise HTTPException(404, "文件已不存在")
        f.downloads += 1
        db.commit()
        return FileResponse(path, filename=f.original_name, media_type=f.mime)

@app.get("/api/recent")
def recent(db: Session = Depends(db_session)):
    now = datetime.utcnow()
    rows = db.scalars(
        select(StoredFile)
        .where(StoredFile.expires_at > now)
        .order_by(StoredFile.created_at.desc())
        .limit(8)
    ).all()
    result = []
    for f in rows:
        p = Path(f.original_name)
        stem, suffix = p.stem, p.suffix
        if len(stem) <= 2:
            masked = stem[:1] + "•••" + suffix
        else:
            masked = stem[:2] + "••••" + stem[-1:] + suffix
        result.append({
            "id": f.id,
            "name": masked,
            "size": f.size,
            "created_at": f.created_at.isoformat() + "Z",
            "downloads": f.downloads
        })
    return {"items": result}

FRONTEND = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="static")
