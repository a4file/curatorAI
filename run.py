#!/usr/bin/env python
"""큐레이터 AI 서버 실행 스크립트"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

