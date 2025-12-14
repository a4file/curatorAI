from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 현재 파일의 위치
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent
BASE_DIR = _backend_dir.parent

# Python path 설정: 프로젝트 루트를 가장 먼저 추가
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
# backend 디렉토리도 추가 (fallback용)
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# import 시도
try:
    # 방법 1: 프로젝트 루트 기준 절대 import
    from backend.api.conversation import router as conversation_router
    from backend.api.qr import router as qr_router
except ImportError:
    try:
        # 방법 2: backend 디렉토리 기준 상대 import
        from api.conversation import router as conversation_router
        from api.qr import router as qr_router
    except ImportError:
        # 방법 3: 상대 import
        from .api.conversation import router as conversation_router
        from .api.qr import router as qr_router

# FastAPI 앱 생성
app = FastAPI(
    title="아담",
    description="갤러리 큐레이터 AI 시스템 (모델명: 아담)",
    version="1.0.0"
)

# CORS 설정 (QR 코드 접근을 위한 모바일/웹 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(conversation_router)
app.include_router(qr_router)

# BASE_DIR은 이미 위에서 정의됨

# 정적 파일 서빙 (프론트엔드)
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# 이미지 파일 서빙
img_dir = BASE_DIR / "img"
if img_dir.exists():
    app.mount("/img", StaticFiles(directory=str(img_dir)), name="img")

# 텍스트 파일 서빙
text_dir = BASE_DIR / "text"
if text_dir.exists():
    app.mount("/text", StaticFiles(directory=str(text_dir)), name="text")


@app.get("/")
async def root():
    """루트 경로 - 프론트엔드 인덱스 페이지"""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "아담 API", "docs": "/docs"}


@app.get("/admin")
async def admin():
    """관리 페이지 - QR 코드 표시"""
    admin_file = frontend_dir / "admin.html"
    if admin_file.exists():
        return FileResponse(str(admin_file))
    return {"message": "관리 페이지를 찾을 수 없습니다."}


@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    # 직접 app 객체를 전달하여 실행
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # 직접 실행 시 reload는 False
    )

