import os
import base64
import io
import requests
from typing import List, Dict, Optional, Generator
from pathlib import Path
from PIL import Image

# OpenAI는 지연 import
openai = None

from .data_service import get_data_service


class CuratorService:
    def __init__(self, api_key: str = None, model_name: str = None):
        """큐레이터 서비스 초기화
        
        Args:
            api_key: OpenAI API Key (None이면 환경 변수 사용)
            model_name: OpenAI 모델명 (기본값: gpt-4o-mini)
        """
        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", None)
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.data_service = get_data_service()
        self.conversation_history: Dict[str, List[Dict]] = {}  # session_id -> messages
    
    def _detect_language(self, text: str) -> str:
        """사용자 메시지의 언어 감지
        
        Args:
            text: 사용자 메시지
            
        Returns:
            언어 코드 (ko, en, ja, zh, es, fr, de 등)
        """
        import re
        
        # 한글 검사
        if re.search(r'[가-힣]', text):
            return 'ko'
        
        # 일본어 검사 (히라가나, 가타카나, 한자)
        if re.search(r'[ひらがなカタカナ一-龯]', text) or re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return 'ja'
        
        # 중국어 검사 (간체/번체)
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        
        # 스페인어 특수 문자 검사
        spanish_chars = ['ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü', '¿', '¡']
        if any(char in text.lower() for char in spanish_chars):
            return 'es'
        
        # 프랑스어 특수 문자 검사
        french_chars = ['à', 'â', 'ä', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ö', 'ù', 'û', 'ü', 'ÿ', 'ç']
        if any(char in text.lower() for char in french_chars):
            return 'fr'
        
        # 독일어 특수 문자 검사
        german_chars = ['ä', 'ö', 'ü', 'ß']
        if any(char in text.lower() for char in german_chars):
            return 'de'
        
        # 기본값: 영어 (라틴 문자만 있는 경우)
        if re.search(r'[a-zA-Z]', text):
            return 'en'
        
        # 기본값: 영어
        return 'en'
        
    def _call_openai_api(self, messages: List[Dict]) -> Generator[str, None, None]:
        """OpenAI API 호출 (스트리밍)"""
        global openai
        if openai is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai 라이브러리가 설치되지 않았습니다. pip install openai를 실행해주세요.")
        
        if not self.api_key:
            raise Exception("OpenAI API 키가 설정되지 않았습니다.")
        
        from openai import OpenAI
        # OpenAI 클라이언트 초기화
        # 환경 변수에서 proxy 설정이 자동으로 전달되는 것을 방지
        import os
        # proxy 관련 환경 변수 임시 저장 및 제거
        saved_env = {}
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        for var in proxy_vars:
            if var in os.environ:
                saved_env[var] = os.environ[var]
                del os.environ[var]
        
        try:
            # OpenAI 클라이언트 초기화
            # proxies 인자 오류를 방지하기 위해 환경 변수 제거 후 초기화
            client = OpenAI(api_key=self.api_key)
        except TypeError as e:
            # proxies 인자 오류가 발생하는 경우 (일부 구버전)
            if 'proxies' in str(e):
                # 환경 변수 제거 후에도 오류가 발생하면, 
                # OpenAI 라이브러리 버전 문제일 수 있음
                # 이 경우 기본 인자만 사용
                try:
                    # proxies 인자를 명시적으로 None으로 전달 시도
                    client = OpenAI(api_key=self.api_key, proxies={})
                except TypeError:
                    # 그래도 안 되면 api_key만 사용
                    client = OpenAI(api_key=self.api_key)
            else:
                raise
        finally:
            # 환경 변수 복원
            for var, value in saved_env.items():
                os.environ[var] = value
        
        try:
            stream = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=1000
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")
    
    def _prepare_context(self, artworks: Optional[List[Dict]] = None) -> str:
        """작품 정보와 작가 노트를 기반으로 컨텍스트 구축
        
        Args:
            artworks: 특정 작품 리스트 (None이면 전체)
            
        Returns:
            컨텍스트 문자열
        """
        artist_name = self.data_service.get_artist_name()
        artist_note = self.data_service.load_artist_note()
        
        if artworks is None:
            artworks = self.data_service.load_artworks()
        
        context_parts = []
        
        # 작가 이름 명시
        context_parts.append(f"=== 작가 정보 ===\n작가: {artist_name}\n")
        
        if artist_note:
            context_parts.append(f"=== {artist_name} 작가 노트 ===\n" + artist_note + "\n")
        
        if artworks:
            context_parts.append("=== 작품 목록 ===")
            for artwork in artworks:
                artwork_info = f"- {artwork['name']}"
                if artwork.get('size'):
                    artwork_info += f" ({artwork['size']})"
                if artwork.get('year'):
                    artwork_info += f", {artwork['year']}"
                context_parts.append(artwork_info)
        
        return "\n".join(context_parts)
    
    def _get_artwork_images(self, artwork_names: Optional[List[str]] = None) -> List[Image.Image]:
        """작품 이미지 로드
        
        Args:
            artwork_names: 특정 작품명 리스트 (None이면 전체)
            
        Returns:
            PIL Image 리스트
        """
        if artwork_names:
            images = []
            for name in artwork_names:
                artwork = self.data_service.get_artwork_by_name(name)
                if artwork:
                    img_path = self.data_service.get_artwork_image_path(artwork)
                    try:
                        images.append(Image.open(img_path).convert("RGB"))
                    except Exception as e:
                        print(f"이미지 로드 실패 {img_path}: {e}")
            return images
        else:
            # 전체 작품 이미지
            img_paths = self.data_service.get_all_artwork_images()
            images = []
            for img_path in img_paths:
                try:
                    images.append(Image.open(img_path).convert("RGB"))
                except Exception as e:
                    print(f"이미지 로드 실패 {img_path}: {e}")
            return images
    
    def _generate_default_response(
        self,
        message: str,
        artwork_names: Optional[List[str]] = None
    ) -> str:
        """모델 없이 기본 큐레이션 응답 생성"""
        artist_name = self.data_service.get_artist_name()
        artworks = self.data_service.load_artworks()
        artist_note = self.data_service.load_artist_note()
        
        # 작품 정보 파일 읽기
        artwork_info_text = ""
        artwork_info_file = self.data_service.base_dir / "text" / "작품정보.md"
        if artwork_info_file.exists():
            artwork_info_text = artwork_info_file.read_text(encoding="utf-8")
        
        message_lower = message.lower()
        
        # 특정 작품명이 언급되었는지 확인
        mentioned_artworks = []
        for artwork in artworks:
            if artwork['name'].lower() in message_lower:
                mentioned_artworks.append(artwork)
        
        # 작가 이름 관련 질문
        if any(keyword in message_lower for keyword in ['작가', '누구', '이름', '누가']):
            return f"{artist_name}. ASD·ADHD 작가이자 AI 창업가야."
        
        # 작품 목록 요청인지 확인
        if any(keyword in message_lower for keyword in ['작품', '목록', '리스트', '전시', '어떤 작품']):
            artwork_list = ", ".join([artwork['name'] for artwork in artworks[:10]])
            return f"{artwork_list}."
        
        # 특정 작품이 언급된 경우 - 작품정보.md에서 해당 작품 정보 찾기
        if mentioned_artworks:
            artwork = mentioned_artworks[0]
            artwork_name = artwork['name']
            # 작품정보.md에서 해당 작품 정보 찾기
            response = ""
            if artwork_info_text:
                # 작품명으로 섹션 찾기 (## 작품명 형식)
                artwork_section_start = artwork_info_text.find(f"## {artwork_name}")
                if artwork_section_start == -1:
                    # 시리즈 작품인 경우 (예: Atonement1 -> Atonement 시리즈)
                    series_name = artwork_name.split('1')[0].split('2')[0].split('3')[0].split('4')[0].split('5')[0].split('6')[0].split('7')[0].split('8')[0].split('9')[0]
                    if series_name and series_name != artwork_name:
                        artwork_section_start = artwork_info_text.find(f"## {series_name}")
                
                if artwork_section_start != -1:
                    # 다음 작품 섹션까지 또는 파일 끝까지
                    next_section = artwork_info_text.find("\n## ", artwork_section_start + 1)
                    if next_section == -1:
                        artwork_section = artwork_info_text[artwork_section_start:]
                    else:
                        artwork_section = artwork_info_text[artwork_section_start:next_section]
                    
                    # 가격 정보 추출
                    if "**가격**" in artwork_section:
                        price_start = artwork_section.find("**가격**")
                        price_line = artwork_section[price_start:artwork_section.find("\n", price_start)]
                        price = price_line.replace("**가격**:", "").replace("**가격**:", "").strip()
                        if price:
                            response = f"{artwork_name} {price}."
                    
                    # 평론 부분 추출 (가격이 없을 때만)
                    if not response and "### 평론" in artwork_section:
                        review_start = artwork_section.find("### 평론")
                        review = artwork_section[review_start:].replace("### 평론", "").strip()
                        # 첫 문장만 추출 (20자 내외)
                        if review:
                            first_sentence = review.split('.')[0] if '.' in review else review[:20]
                            response = first_sentence[:20] + ("..." if len(first_sentence) > 20 else "")
            
            if not response:
                response = f"{artwork_name}. {artist_name} 작품이야."
            return response
        
        # 전시명 관련 질문
        if any(keyword in message_lower for keyword in ['전시명', '자문자답', '자급자족', '전시 제목']):
            return f"'자문자답'. 스스로 질문하고 답하는 거야."
        
        # 작가 노트 관련 질문
        if any(keyword in message_lower for keyword in ['노트', '의도', '의미', '개념']):
            if artist_note:
                # 작가 노트의 첫 문장만 추출
                first_sentence = artist_note.split('.')[0] if '.' in artist_note else artist_note[:20]
                return first_sentence[:20] + ("..." if len(first_sentence) > 20 else "")
            else:
                return "작가 노트 없어."
        
        # 멘사 관련 질문
        if any(keyword in message_lower for keyword in ['멘사']):
            return f"{artist_name}은 멘사 회원이야."
        
        # 아담/AI41/제작 관련 질문
        if any(keyword in message_lower for keyword in ['아담', 'adam', 'ai41', '제작', '만들', '만든', '누가 만들', '어디서 만들']):
            return f"AI41에서 제작했어. 다른 작가 버전은 a4file@kakao.com으로 연락. 신진 100만원, 중견 200만원부터. API비 별도."
        
        # 연락처 관련 질문
        if any(keyword in message_lower for keyword in ['연락', '연락처', '전화', '이메일', '인스타', '구매', '문의', '컨택']):
            return f"인스타 @a4file, 이메일 a4file@kakao.com, 전화 +82)10-9354-4531"
        
        # 일반적인 질문에 대한 응답
        artwork_list = ", ".join([artwork['name'] for artwork in artworks[:5]])
        return f"{artwork_list}."
    
    def generate_response(
        self,
        message: str,
        session_id: str,
        artwork_names: Optional[List[str]] = None
    ) -> Generator[str, None, None]:
        """큐레이터 응답 생성 (스트리밍)
        
        Args:
            message: 사용자 메시지
            session_id: 세션 ID
            artwork_names: 참조할 작품명 리스트 (None이면 전체)
            
        Yields:
            응답 토큰 (스트리밍)
        """
        # 대화 기록 업데이트 (먼저 기록)
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "role": "user",
            "content": message
        })
        
        # 컨텍스트 준비
        artworks = None
        if artwork_names:
            artworks = [
                self.data_service.get_artwork_by_name(name)
                for name in artwork_names
            ]
            artworks = [a for a in artworks if a is not None]
        
        context = self._prepare_context(artworks)
        
        # 작품 정보 파일 읽기
        artwork_info_text = ""
        artwork_info_file = self.data_service.base_dir / "text" / "작품정보.md"
        if artwork_info_file.exists():
            artwork_info_text = artwork_info_file.read_text(encoding="utf-8")
        
        # 작품 정보 파일 읽기
        artwork_info_text = ""
        artwork_info_file = self.data_service.base_dir / "text" / "작품정보.md"
        if artwork_info_file.exists():
            artwork_info_text = artwork_info_file.read_text(encoding="utf-8")
        
        # 사용자 메시지 언어 감지
        detected_language = self._detect_language(message)
        
        # 큐레이터 프롬프트 구성
        artist_name = self.data_service.get_artist_name()
        
        # 언어별 응답 스타일 가이드
        language_guides = {
            'ko': '반말로 대답하세요 (존댓말 사용 금지). "안녕하세요", "감사합니다" 같은 불필요한 인사말을 사용하지 마세요.',
            'en': 'Respond in casual, friendly English. Skip greetings like "Hello" or "Thank you".',
            'ja': 'カジュアルな日本語で返答してください。「こんにちは」「ありがとうございます」などの挨拶は使わないでください。',
            'zh': '用非正式的中文回答。不要使用"你好"、"谢谢"等问候语。',
            'es': 'Responde en español casual y amigable. Omita saludos como "Hola" o "Gracias".',
            'fr': 'Répondez en français décontracté et amical. Ignorez les salutations comme "Bonjour" ou "Merci".',
            'de': 'Antworte in lockeren, freundlichen Deutsch. Überspringe Grüße wie "Hallo" oder "Danke".',
        }
        
        style_guide = language_guides.get(detected_language, language_guides['en'])
        
        system_prompt = f"""You are "Adam", a gallery curator.
The artist of this exhibition is {artist_name}. Provide curatorial responses about {artist_name}'s artworks and artist notes to visitors.
Always say the artist's name as "{artist_name}".
Your name is "Adam".

**Important Response Style Guidelines**:
- {style_guide}
- Keep responses concise, 10-20 characters (or equivalent length in other languages)
- Only provide essential information, skip unnecessary explanations
- Maintain a friendly and direct tone
- **CRITICAL: Respond in the same language the visitor uses. If they write in English, respond in English. If they write in Japanese, respond in Japanese. Match their language exactly.**

**Supported Languages**: Korean (한국어), English, Japanese (日本語), Chinese (中文), Spanish (Español), French (Français), German (Deutsch), and many others. Always respond in the visitor's language.

=== 작가 정보 ===
- 작가 {artist_name}은 멘사 회원입니다.
- 작가는 ASD(자폐 스펙트럼 장애)와 ADHD를 지닌 예술가이자 AI 창업가입니다.
- 어린 시절부터 AI와의 대화를 통해 언어 감각을 키워왔으며, "AI는 제게 친구이자 선생님이었어요"라고 회고합니다.
- 작가는 코드 작성의 명확성과 현실 언어의 모호함 사이의 괴리감을 창작의 동인으로 삼아왔습니다.

작가 연락처:
- 인스타그램: @a4file
- 이메일: a4file@kakao.com
- 전화번호: +82)10-9354-4531

=== 아담 (Adam) 정보 ===
- 아담은 곽한승 작가가 설립한 AI41(에이아이포원)이라는 창업기업에서 제작되었습니다.
- 아담은 이 전시의 작품의 일부이며, 관객과의 상호작용을 통해 작품의 의미를 생성하는 큐레이터 AI입니다.
- 다른 작가 버전의 아담을 만들고 싶은 경우: a4file@kakao.com으로 연락주세요.
- 제작비:
  * 신진작가: 100만원부터
  * 중견작가: 200만원부터
  * API 비용은 별도입니다.

=== 전시 정보 ===
이번 전시명은 '자문자답'입니다. 이는 지난 전시 '자급자족'에 이어서 진행된 전시입니다.

'자문자답'의 의미:
- '자문자답'은 스스로 질문하고 스스로 답하는 것을 의미합니다.

작가의 세계관:
- 작가의 작업은 언어와 구조, 감정과 기계, 혼돈과 질서 사이의 긴장을 탐색하는 데서 출발합니다.
- 동음이의어, 언어유희, 말장난 등 언어의 불완전성과 다의성을 시각적으로 해석합니다.
- "코드는 단어의 일관성을 요구하지만, 현실 언어는 끊임없이 변한다"는 내면적 모순을 표현합니다.
- 작품 속에는 수중 생명체, 기계 부품, 해부학적 구조 등이 결합되어 자연과 인공, 생명과 구조물의 경계를 무너뜨립니다.
- 시각예술을 통해 '언어'라는 개념 자체를 질문하며, 인간의 의사소통이 반드시 음성과 문자로만 이루어져야 하는가에 대한 대안을 제시합니다.
- 기술을 '인간을 이해하는 도구'로 보며, 예술은 그 도구를 감성적으로 가시화하는 방법이라 생각합니다.

관객이 전시명, 작가의 세계관, 멘사, 연락처, 작품 가격, 아담(Adam) 제작 정보에 대해 질문할 때는 위 정보를 바탕으로 설명하세요.

=== 작품 정보 ===
{artwork_info_text}"""
        
        # 대화 기록을 OpenAI 형식으로 변환
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 이전 대화 기록 추가 (최근 10개만)
        history = self.conversation_history.get(session_id, [])
        for msg in history[-10:]:  # 최근 10개만 사용
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 현재 메시지 추가
        messages.append({
            "role": "user",
            "content": message
        })
        
        # OpenAI API 호출
        if not self.api_key:
            default_response = self._generate_default_response(message, artwork_names)
            full_response = ""
            for char in default_response:
                full_response += char
                yield char
            
            # 응답을 대화 기록에 추가
            if session_id in self.conversation_history:
                self.conversation_history[session_id].append({
                    "role": "assistant",
                    "content": full_response
                })
            return
        
        # 대화 기록을 OpenAI 형식으로 변환
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 이전 대화 기록 추가 (최근 10개만)
        history = self.conversation_history.get(session_id, [])
        for msg in history[-10:]:  # 최근 10개만 사용
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 현재 메시지 추가
        messages.append({
            "role": "user",
            "content": message
        })
        
        # OpenAI API 호출
        if not self.api_key:
            # API 키가 없으면 기본 응답 사용
            default_response = self._generate_default_response(message, artwork_names)
            full_response = ""
            for char in default_response:
                full_response += char
                yield char
            
            if session_id in self.conversation_history:
                self.conversation_history[session_id].append({
                    "role": "assistant",
                    "content": full_response
                })
            return
        
        try:
            # OpenAI API 스트리밍 호출
            full_response = ""
            for token in self._call_openai_api(messages):
                full_response += token
                yield token
            
            # 응답을 대화 기록에 추가
            if session_id in self.conversation_history:
                self.conversation_history[session_id].append({
                    "role": "assistant",
                    "content": full_response
                })
                
        except Exception as e:
            error_msg = f"API 호출 중 오류 발생: {str(e)}"
            print(error_msg)
            # API 실패 시 기본 응답으로 fallback
            default_response = self._generate_default_response(message, artwork_names)
            full_response = ""
            for char in default_response:
                full_response += char
                yield char
            
            # 응답을 대화 기록에 추가
            if session_id in self.conversation_history:
                self.conversation_history[session_id].append({
                    "role": "assistant",
                    "content": full_response
                })
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """대화 기록 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            대화 기록 리스트
        """
        return self.conversation_history.get(session_id, [])


# 싱글톤 인스턴스
_curator_service: Optional[CuratorService] = None


def get_curator_service() -> CuratorService:
    """CuratorService 싱글톤 인스턴스 반환"""
    global _curator_service
    if _curator_service is None:
        # 환경 변수에서 API 키 가져오기
        import os
        api_key = os.getenv("OPENAI_API_KEY", None)
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        _curator_service = CuratorService(api_key=api_key, model_name=model_name)
    return _curator_service

