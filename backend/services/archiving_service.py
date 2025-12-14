import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class ArchivingService:
    def __init__(self, base_dir: str = None):
        """아카이빙 서비스 초기화
        
        Args:
            base_dir: 프로젝트 루트 디렉토리 경로
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent
        self.base_dir = Path(base_dir)
        self.archive_dir = self.base_dir / "backend" / "data" / "archives"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def save_conversation(
        self,
        session_id: str,
        messages: List[Dict],
        metadata: Optional[Dict] = None
    ):
        """대화 기록 저장
        
        Args:
            session_id: 세션 ID
            messages: 대화 메시지 리스트
            metadata: 추가 메타데이터
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{timestamp}.json"
        filepath = self.archive_dir / filename
        
        archive_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "messages": messages,
            "metadata": metadata or {}
        }
        
        filepath.write_text(
            json.dumps(archive_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return filepath
    
    def load_archive(self, session_id: str) -> Optional[Dict]:
        """특정 세션의 아카이브 로드
        
        Args:
            session_id: 세션 ID
            
        Returns:
            아카이브 데이터 또는 None
        """
        # 가장 최근 아카이브 찾기
        archives = list(self.archive_dir.glob(f"{session_id}_*.json"))
        if not archives:
            return None
        
        latest = max(archives, key=lambda p: p.stat().st_mtime)
        return json.loads(latest.read_text(encoding="utf-8"))
    
    def list_archives(self, limit: int = 100) -> List[Dict]:
        """모든 아카이브 목록 조회
        
        Args:
            limit: 최대 반환 개수
            
        Returns:
            아카이브 메타데이터 리스트
        """
        archives = []
        for archive_file in sorted(
            self.archive_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            try:
                data = json.loads(archive_file.read_text(encoding="utf-8"))
                archives.append({
                    "session_id": data.get("session_id"),
                    "timestamp": data.get("timestamp"),
                    "datetime": data.get("datetime"),
                    "message_count": len(data.get("messages", [])),
                    "filename": archive_file.name
                })
            except Exception as e:
                print(f"아카이브 로드 실패 {archive_file}: {e}")
        
        return archives
    
    def get_archive_by_session(self, session_id: str) -> Optional[List[Dict]]:
        """세션의 모든 아카이브 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            아카이브 데이터 리스트
        """
        archives = []
        for archive_file in sorted(
            self.archive_dir.glob(f"{session_id}_*.json"),
            key=lambda p: p.stat().st_mtime
        ):
            try:
                data = json.loads(archive_file.read_text(encoding="utf-8"))
                archives.append(data)
            except Exception as e:
                print(f"아카이브 로드 실패 {archive_file}: {e}")
        
        return archives if archives else None


# 싱글톤 인스턴스
_archiving_service: Optional[ArchivingService] = None


def get_archiving_service() -> ArchivingService:
    """ArchivingService 싱글톤 인스턴스 반환"""
    global _archiving_service
    if _archiving_service is None:
        _archiving_service = ArchivingService()
    return _archiving_service

