import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image


class DataService:
    def __init__(self, base_dir: str = None):
        """데이터 서비스 초기화
        
        Args:
            base_dir: 프로젝트 루트 디렉토리 경로 (None이면 현재 스크립트 기준 상대 경로)
        """
        if base_dir is None:
            # backend/services/에서 상위 디렉토리로 이동
            base_dir = Path(__file__).parent.parent.parent
        self.base_dir = Path(base_dir)
        self.img_dir = self.base_dir / "img"
        self.text_dir = self.base_dir / "text"
        self.artworks_file = self.base_dir / "backend" / "data" / "artworks.json"
        self.artworks_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.artworks_cache: Optional[List[Dict]] = None
        self.artist_note_cache: Optional[str] = None
        
    def load_artworks(self) -> List[Dict]:
        """img 폴더의 작품 이미지 메타데이터 로드
        
        Returns:
            작품 정보 리스트
        """
        if self.artworks_cache is not None:
            return self.artworks_cache
            
        artworks = []
        
        if not self.img_dir.exists():
            return artworks
            
        # 작품 이미지 파일 목록 가져오기
        image_files = sorted(self.img_dir.glob("*.jpg"))
        
        for img_file in image_files:
            # 파일명에서 작품 정보 파싱
            # 형식: 곽한승_작품명_크기_Mixed Media_연도.jpg
            filename = img_file.stem
            parts = filename.split("_")
            
            if len(parts) >= 4:
                artist = parts[0]
                artwork_name = parts[1]
                size = parts[2]
                medium = parts[3]
                year = parts[4] if len(parts) > 4 else None
                
                # 이미지 메타데이터 가져오기
                try:
                    with Image.open(img_file) as img:
                        width, height = img.size
                except Exception:
                    width, height = None, None
                
                artwork_info = {
                    "filename": img_file.name,
                    "filepath": str(img_file.relative_to(self.base_dir)),
                    "artist": artist,
                    "name": artwork_name,
                    "size": size,
                    "medium": medium,
                    "year": year,
                    "width": width,
                    "height": height,
                }
                artworks.append(artwork_info)
        
        # 작품 정보를 JSON 파일로 저장
        self.artworks_file.write_text(
            json.dumps(artworks, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        self.artworks_cache = artworks
        return artworks
    
    def get_artwork_by_name(self, name: str) -> Optional[Dict]:
        """작품명으로 작품 정보 조회
        
        Args:
            name: 작품명
            
        Returns:
            작품 정보 딕셔너리 또는 None
        """
        artworks = self.load_artworks()
        for artwork in artworks:
            if artwork["name"].lower() == name.lower():
                return artwork
        return None
    
    def get_artwork_image_path(self, artwork: Dict) -> Path:
        """작품의 이미지 파일 경로 반환
        
        Args:
            artwork: 작품 정보 딕셔너리
            
        Returns:
            이미지 파일 경로
        """
        return self.base_dir / artwork["filepath"]
    
    def load_artist_note(self) -> str:
        """작가 노트 파일 읽기
        
        Returns:
            작가 노트 텍스트
        """
        if self.artist_note_cache is not None:
            return self.artist_note_cache
            
        note_file = self.text_dir / "작가노트.txt"
        
        if not note_file.exists():
            return ""
        
        self.artist_note_cache = note_file.read_text(encoding="utf-8")
        return self.artist_note_cache
    
    def get_all_artwork_images(self) -> List[Path]:
        """모든 작품 이미지 파일 경로 반환
        
        Returns:
            이미지 파일 경로 리스트
        """
        artworks = self.load_artworks()
        return [self.base_dir / artwork["filepath"] for artwork in artworks]
    
    def get_artist_name(self) -> str:
        """작가 이름 반환
        
        Returns:
            작가 이름 (기본값: "곽한승")
        """
        artworks = self.load_artworks()
        if artworks and len(artworks) > 0:
            # 첫 번째 작품에서 작가 이름 추출
            return artworks[0].get("artist", "곽한승")
        return "곽한승"
    
    def search_artworks_by_prefix(self, prefix: str, limit: int = 10) -> List[Dict]:
        """접두사로 작품 검색 (자동완성용)
        
        Args:
            prefix: 검색할 접두사
            limit: 최대 반환 개수
            
        Returns:
            작품 정보 리스트
        """
        artworks = self.load_artworks()
        prefix_lower = prefix.lower()
        
        # 작품명으로 필터링
        matches = [
            artwork for artwork in artworks
            if artwork["name"].lower().startswith(prefix_lower)
        ]
        
        # 중복 제거 (같은 작품명은 하나만)
        seen_names = set()
        unique_matches = []
        for artwork in matches:
            name = artwork["name"]
            if name not in seen_names:
                seen_names.add(name)
                unique_matches.append(artwork)
                if len(unique_matches) >= limit:
                    break
        
        return unique_matches
    
    def get_collection_artworks(self, base_name: str) -> List[Dict]:
        """컬렉션 작품 가져오기 (작품명이 같고 끝에 숫자가 있는 것들)
        
        Args:
            base_name: 기본 작품명 (예: "Atonement", "Flock")
            
        Returns:
            컬렉션 작품 리스트
        """
        artworks = self.load_artworks()
        base_name_lower = base_name.lower()
        
        # 작품명이 base_name으로 시작하고 끝에 숫자가 있는 것들 찾기
        collection = []
        for artwork in artworks:
            name = artwork["name"]
            name_lower = name.lower()
            
            # base_name으로 시작하는지 확인
            if name_lower.startswith(base_name_lower):
                # 끝에 숫자가 있는지 확인 (예: Atonement1, Flock2)
                remaining = name_lower[len(base_name_lower):]
                if remaining and remaining[0].isdigit():
                    collection.append(artwork)
        
        # 숫자 순서로 정렬
        collection.sort(key=lambda x: x["name"])
        return collection
    
    def get_artwork_image_urls(self, artwork_name: str) -> List[str]:
        """작품의 이미지 URL 리스트 반환 (컬렉션 포함)
        
        Args:
            artwork_name: 작품명
            
        Returns:
            이미지 URL 리스트
        """
        # 먼저 정확한 작품명으로 찾기
        artwork = self.get_artwork_by_name(artwork_name)
        if not artwork:
            return []
        
        # 컬렉션인지 확인 (작품명 끝에 숫자가 있는지)
        import re
        match = re.match(r'^(.+?)(\d+)$', artwork_name)
        if match:
            # 컬렉션 작품인 경우
            base_name = match.group(1)
            collection = self.get_collection_artworks(base_name)
            if collection:
                return [f"/img/{artwork['filename']}" for artwork in collection]
        
        # 단일 작품인 경우
        return [f"/img/{artwork['filename']}"]


# 싱글톤 인스턴스
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """DataService 싱글톤 인스턴스 반환"""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service

