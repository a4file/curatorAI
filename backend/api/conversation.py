from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json

from ..services.curator_service import get_curator_service
from ..services.archiving_service import get_archiving_service

router = APIRouter(prefix="/api", tags=["conversation"])


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    artwork_names: Optional[List[str]] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str


class SessionResponse(BaseModel):
    session_id: str
    messages: List[dict]


@router.post("/chat", response_class=StreamingResponse)
async def chat(message_data: ChatMessage):
    """대화 메시지 처리 및 스트리밍 응답"""
    print(f"[API] /api/chat 호출됨: message={message_data.message[:50]}...")
    curator_service = get_curator_service()
    archiving_service = get_archiving_service()
    
    # 세션 ID 생성 또는 사용
    session_id = message_data.session_id or str(uuid.uuid4())
    print(f"[API] 세션 ID: {session_id}")
    
    def generate():
        response_text = ""
        image_urls = []
        try:
            print(f"[API] generate() 시작: message={message_data.message[:50]}...")
            # 메시지에서 작품명 추출하여 이미지 URL 가져오기
            from ..services.data_service import get_data_service
            data_service = get_data_service()
            
            # 메시지에서 작품명 찾기 (간단한 키워드 매칭)
            message_lower = message_data.message.lower()
            artworks = data_service.load_artworks()
            mentioned_artworks = []
            for artwork in artworks:
                if artwork["name"].lower() in message_lower:
                    mentioned_artworks.append(artwork["name"])
            
            # 언급된 작품의 이미지 URL 가져오기
            for artwork_name in mentioned_artworks:
                urls = data_service.get_artwork_image_urls(artwork_name)
                image_urls.extend(urls)
            
            # 중복 제거
            image_urls = list(dict.fromkeys(image_urls))
            
            for token in curator_service.generate_response(
                message=message_data.message,
                session_id=session_id,
                artwork_names=message_data.artwork_names
            ):
                response_text += token
                # SSE 형식으로 스트리밍
                yield f"data: {json.dumps({'token': token, 'session_id': session_id})}\n\n"
            
            # 이미지 URL 전송
            if image_urls:
                yield f"data: {json.dumps({'images': image_urls, 'session_id': session_id})}\n\n"
            
            # 대화 기록 저장
            try:
                conversation_history = curator_service.get_conversation_history(session_id)
                archiving_service.save_conversation(
                    session_id=session_id,
                    messages=conversation_history
                )
            except Exception as e:
                print(f"아카이빙 저장 실패: {e}")
            
            # 종료 메시지
            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
        except Exception as e:
            # 오류 발생 시 오류 메시지 전송
            error_msg = f"오류가 발생했습니다: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'session_id': session_id})}\n\n"
            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """세션의 대화 기록 조회"""
    curator_service = get_curator_service()
    
    messages = curator_service.get_conversation_history(session_id)
    
    return SessionResponse(
        session_id=session_id,
        messages=messages
    )


@router.post("/session/new")
async def create_session():
    """새 세션 생성"""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


@router.get("/status")
async def get_status():
    """서비스 상태 확인 (API 설정 등)"""
    curator_service = get_curator_service()
    
    return {
        "model_name": curator_service.model_name,
        "api_configured": curator_service.api_key is not None,
        "message": f"모델: {curator_service.model_name} 사용 중" if curator_service.api_key else "기본 응답 모드 사용 중"
    }


@router.get("/autocomplete")
async def autocomplete(q: str, limit: int = 10):
    """작품명 자동완성"""
    from ..services.data_service import get_data_service
    
    data_service = get_data_service()
    artworks = data_service.search_artworks_by_prefix(q, limit)
    
    return {
        "query": q,
        "artworks": [
            {
                "name": artwork["name"],
                "size": artwork.get("size"),
                "year": artwork.get("year"),
                "image_url": f"/img/{artwork['filename']}"
            }
            for artwork in artworks
        ]
    }

