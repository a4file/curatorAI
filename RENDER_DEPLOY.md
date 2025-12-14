# Render 배포 가이드

## 사전 준비

1. GitHub 저장소에 코드 푸시
2. Render 계정 생성 (https://render.com)
3. OpenAI API 키 준비

## 배포 단계

### 방법 1: Render Dashboard 사용 (권장)

1. **새 Web Service 생성**
   - Render 대시보드에서 "New" → "Web Service" 선택
   - GitHub 저장소 연결

2. **설정 입력**
   - **Name**: `adam-curator` (또는 원하는 이름)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

3. **환경 변수 설정**
   - `OPENAI_API_KEY`: OpenAI API 키 입력
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

## 환경 변수

### 필수
- `OPENAI_API_KEY`: OpenAI API 키

### 선택사항
- `OPENAI_MODEL`: 사용할 OpenAI 모델 (기본값: `gpt-4o-mini`)

## 확인 사항

배포 후 다음 URL을 확인하세요:

- 메인 페이지: `https://your-service.onrender.com/`
- 관리 페이지 (QR 코드): `https://your-service.onrender.com/admin`
- API 문서: `https://your-service.onrender.com/docs`
- 헬스 체크: `https://your-service.onrender.com/health`

## 문제 해결

### 빌드 실패
- `requirements.txt`가 프로젝트 루트에 있는지 확인
- Python 버전이 3.11인지 확인 (`runtime.txt` 참고)

### 실행 실패
- 환경 변수 `OPENAI_API_KEY`가 설정되었는지 확인
- Start Command가 올바른지 확인
- Render 로그 확인: Dashboard → Service → Logs

### 포트 에러
- Render는 `$PORT` 환경 변수를 자동으로 제공합니다.
- Start Command에 `--port $PORT`가 포함되어 있는지 확인

### 정적 파일이 보이지 않음
- 이미지, CSS, JS 파일은 프로젝트와 함께 배포되어야 합니다.
- `.gitignore`에 정적 파일이 포함되지 않았는지 확인

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

