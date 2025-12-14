// API 클라이언트 유틸리티

const API_BASE_URL = '';

class APIClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }
    
    async chat(message, sessionId = null, artworkNames = null) {
        const response = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                artwork_names: artworkNames
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response;
    }
    
    async getSession(sessionId) {
        const response = await fetch(`${this.baseUrl}/api/session/${sessionId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }
    
    async createSession() {
        const response = await fetch(`${this.baseUrl}/api/session/new`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }
}

// 전역 API 클라이언트 인스턴스
const apiClient = new APIClient();

