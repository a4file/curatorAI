from fastapi import APIRouter
from fastapi.responses import Response
from PIL import Image
import qrcode
import io
from typing import Optional

router = APIRouter(prefix="/api", tags=["qr"])


@router.get("/qr")
async def generate_qr_code(url: Optional[str] = None):
    """QR 코드 생성
    
    Args:
        url: QR 코드에 인코딩할 URL (기본값: 현재 서버 URL)
    """
    if url is None:
        # 실제 배포 환경에서는 환경 변수나 설정에서 가져와야 함
        url = "http://localhost:8000"
    
    # QR 코드 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # 이미지 생성
    img = qr.make_image(fill_color="black", back_color="white")
    
    # PNG 형식으로 반환
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return Response(content=img_buffer.getvalue(), media_type="image/png")


@router.get("/qr/info")
async def get_qr_info():
    """QR 코드에 포함될 URL 정보 반환"""
    # 실제 배포 환경에서는 환경 변수에서 가져와야 함
    base_url = "http://localhost:8000"
    return {
        "url": base_url,
        "qr_code_url": f"{base_url}/api/qr?url={base_url}"
    }

