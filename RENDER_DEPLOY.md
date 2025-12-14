# Render 배포 가이드

## 사전 준비

1. GitHub 저장소에 코드 푸시
2. Render 계정 생성 (https://render.com)
3. OpenAI API 키 준비

## 프로젝트 요구사항

- **Python 버전**: 3.11.0 (자동으로 `runtime.txt`에서 감지)
- **의존성**: `requirements.txt` 참고
- **환경 변수**: `OPENAI_API_KEY` 필수

## 배포 단계

### 방법 1: Render Dashboard 사용 (권장)

1. **새 Web Service 생성**
   - Render 대시보드에서 "New" → "Web Service" 선택
   - GitHub 저장소 연결

2. **설정 입력**
   - **Name**: `adam-curator` (또는 원하는 이름)
   - **Environment**: `Python 3` (자동으로 `runtime.txt`에서 Python 3.11.0 감지)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

3. **환경 변수 설정**
   - `OPENAI_API_KEY`: OpenAI API 키 입력 (필수)
   - `OPENAI_MODEL`: `gpt-4o-mini` (선택사항, 기본값)

4. **배포**
   - "Create Web Service" 클릭
   - 배포 완료까지 대기 (약 2-5분)

### 방법 2: render.yaml 사용 (BluePrint)

1. GitHub 저장소에 `render.yaml` 파일이 이미 포함되어 있습니다.
2. Render 대시보드에서 "New" → "BluePrint" 선택
3. GitHub 저장소 연결
4. `render.yaml`이 자동으로 인식되어 서비스가 생성됩니다.
5. 환경 변수 `OPENAI_API_KEY`만 설정하면 됩니다.

**참고**: `render.yaml`을 사용할 때도 `runtime.txt`가 있으면 Python 버전이 자동으로 설정됩니다.

## 환경 변수

### 필수
- `OPENAI_API_KEY`: OpenAI API 키

### 선택사항
- `OPENAI_MODEL`: 사용할 OpenAI 모델 (기본값: `gpt-4o-mini`)

## 로컬 개발 환경 설정

로컬에서 개발할 때는 프로젝트 루트에 `.env` 파일을 생성하세요:

```bash
# .env 파일 생성
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

**중요**: `.env` 파일은 Git에 커밋되지 않습니다 (`.gitignore`에 포함됨). `env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

## 확인 사항

배포 후 다음 URL을 확인하세요:

- 메인 페이지: `https://your-service.onrender.com/`
- 관리 페이지 (QR 코드): `https://your-service.onrender.com/admin`
- API 문서: `https://your-service.onrender.com/docs`
- 헬스 체크: `https://your-service.onrender.com/health`
- Git 도구 API: `https://your-service.onrender.com/api/git/status`

## API 엔드포인트

### 대화 API
- `POST /api/chat`: AI 큐레이터와 대화
- `GET /api/session/{session_id}`: 세션 기록 조회
- `POST /api/session/new`: 새 세션 생성
- `GET /api/status`: 서비스 상태 확인
- `GET /api/autocomplete`: 작품명 자동완성

### QR 코드 API
- `GET /api/qr`: QR 코드 이미지 생성
- `GET /api/qr/info`: QR 코드 정보

### Git 도구 API
- `GET /api/git/status`: Git 저장소 상태 확인
- `GET /api/git/log`: 커밋 로그 조회
- `GET /api/git/diff`: 변경사항 diff 조회
- `GET /api/git/branch`: 브랜치 목록
- `GET /api/git/remote`: 원격 저장소 정보

## 문제 해결

### Python 버전 문제

**증상**: Python 3.13.4가 사용되거나 빌드 실패

**해결 방법**:
1. `runtime.txt` 파일이 프로젝트 루트에 있는지 확인
2. `runtime.txt` 내용이 `python-3.11.0` 형식인지 확인
3. Render 대시보드에서 수동으로 Python 버전을 3.11.0으로 설정:
   - Dashboard → Service → Settings → Environment
   - Python 버전을 3.11.0으로 선택

### 빌드 실패

**증상**: 패키지 설치 중 오류 발생

**해결 방법**:
- `requirements.txt`가 프로젝트 루트에 있는지 확인
- Python 버전이 3.11.0인지 확인 (`runtime.txt` 참고)
- 최신 의존성 버전 사용:
  - `pillow>=10.4.0` (Python 3.11/3.12/3.13 호환)
  - `pydantic>=2.6.0` (Python 3.13 호환성 개선)

### 실행 실패

**해결 방법**:
- 환경 변수 `OPENAI_API_KEY`가 설정되었는지 확인
- Start Command가 올바른지 확인: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Render 로그 확인: Dashboard → Service → Logs

### 포트 에러

**해결 방법**:
- Render는 `$PORT` 환경 변수를 자동으로 제공합니다.
- Start Command에 `--port $PORT`가 포함되어 있는지 확인

### 정적 파일이 보이지 않음

**해결 방법**:
- 이미지, CSS, JS 파일은 프로젝트와 함께 배포되어야 합니다.
- `.gitignore`에 정적 파일이 포함되지 않았는지 확인

### pydantic-core 빌드 오류

**증상**: `pydantic-core` 빌드 중 Rust/Cargo 오류

**해결 방법**:
- Python 버전을 3.11.0으로 설정 (Python 3.13과 호환성 문제)
- `pydantic>=2.6.0` 사용 (최신 버전은 Python 3.13 호환)

## 무료 티어 제한사항

Render 무료 티어:
- 15분간 요청이 없으면 서비스가 sleep 상태가 됩니다.
- 첫 요청 시 약 30초 정도 cold start 시간이 걸릴 수 있습니다.
- 월 750시간 사용 가능 (24/7 운영 불가)

### 해결 방법
- [UptimeRobot](https://uptimerobot.com) 같은 서비스로 주기적 헬스 체크
- 또는 유료 플랜 사용

## 비용 최적화

1. **이미지 최적화**: 작품 이미지 해상도를 낮춰 저장 공간 절약
2. **캐싱**: 자주 사용되는 데이터 캐싱 고려
3. **API 호출 최적화**: 불필요한 API 호출 줄이기

## 보안 권장사항

1. **CORS 설정**: 프로덕션에서는 `allow_origins=["*"]` 대신 특정 도메인으로 제한
2. **환경 변수**: API 키는 절대 코드에 하드코딩하지 않기
3. **HTTPS**: Render는 자동으로 HTTPS를 제공합니다.
4. **Git 도구 API**: 프로덕션에서는 Git 도구 API 접근을 제한하는 것을 권장합니다.

## 의존성 정보

주요 의존성:
- `fastapi==0.104.1`: 웹 프레임워크
- `uvicorn[standard]==0.24.0`: ASGI 서버
- `pillow>=10.4.0`: 이미지 처리 (Python 3.11+ 호환)
- `pydantic>=2.6.0`: 데이터 검증 (Python 3.13 호환)
- `openai==1.12.0`: OpenAI API 클라이언트
- `qrcode[pil]==7.4.2`: QR 코드 생성

전체 의존성 목록은 `requirements.txt`를 참고하세요.

## 추가 리소스

- [Render 공식 문서](https://render.com/docs)
- [Python 버전 지정 가이드](https://render.com/docs/python-version)
- [배포 문제 해결 가이드](https://render.com/docs/troubleshooting-deploys)
