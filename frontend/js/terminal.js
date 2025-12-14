class Terminal {
    constructor() {
        this.terminalBody = document.getElementById('terminalBody');
        this.userInput = document.getElementById('userInput');
        this.autocompleteList = document.getElementById('autocompleteList');
        this.sessionId = null;
        this.isProcessing = false;
        this.autocompleteTimeout = null;
        this.selectedIndex = -1;
        
        this.init();
    }
    
    init() {
        // 세션 생성
        this.createSession();
        
        // 입력 이벤트 리스너
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isProcessing) {
                if (this.autocompleteList.classList.contains('show')) {
                    // 자동완성에서 선택
                    const items = this.autocompleteList.querySelectorAll('.autocomplete-item');
                    if (items[this.selectedIndex]) {
                        const name = items[this.selectedIndex].dataset.name;
                        this.userInput.value = name;
                        this.hideAutocomplete();
                        this.handleInput();
                    }
                } else {
                    this.handleInput();
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateAutocomplete(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateAutocomplete(-1);
            } else if (e.key === 'Escape') {
                this.hideAutocomplete();
            }
        });
        
        // 입력 변경 시 자동완성
        this.userInput.addEventListener('input', () => {
            this.handleAutocomplete();
        });
        
        // 포커스 유지
        this.userInput.addEventListener('blur', () => {
            // 자동완성 클릭을 위해 약간의 지연
            setTimeout(() => {
                if (!this.isProcessing) {
                    this.hideAutocomplete();
                    this.userInput.focus();
                }
            }, 200);
        });
    }
    
    async handleAutocomplete() {
        const query = this.userInput.value.trim();
        
        // 입력이 너무 짧으면 자동완성 숨김
        if (query.length < 1) {
            this.hideAutocomplete();
            return;
        }
        
        // 디바운싱
        clearTimeout(this.autocompleteTimeout);
        this.autocompleteTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}&limit=10`);
                const data = await response.json();
                
                if (data.artworks && data.artworks.length > 0) {
                    this.showAutocomplete(data.artworks);
                } else {
                    this.hideAutocomplete();
                }
            } catch (error) {
                console.error('자동완성 오류:', error);
                this.hideAutocomplete();
            }
        }, 300);
    }
    
    showAutocomplete(artworks) {
        this.autocompleteList.innerHTML = '';
        this.selectedIndex = -1;
        
        artworks.forEach((artwork, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.dataset.name = artwork.name;
            
            const nameSpan = document.createElement('div');
            nameSpan.className = 'autocomplete-item-name';
            nameSpan.textContent = artwork.name;
            
            const infoSpan = document.createElement('div');
            infoSpan.className = 'autocomplete-item-info';
            infoSpan.textContent = `${artwork.size || ''} ${artwork.year || ''}`.trim();
            
            item.appendChild(nameSpan);
            item.appendChild(infoSpan);
            
            item.addEventListener('click', () => {
                this.userInput.value = artwork.name;
                this.hideAutocomplete();
                this.userInput.focus();
            });
            
            this.autocompleteList.appendChild(item);
        });
        
        this.autocompleteList.classList.add('show');
    }
    
    hideAutocomplete() {
        this.autocompleteList.classList.remove('show');
        this.selectedIndex = -1;
    }
    
    navigateAutocomplete(direction) {
        const items = this.autocompleteList.querySelectorAll('.autocomplete-item');
        if (items.length === 0) return;
        
        // 이전 선택 제거
        if (this.selectedIndex >= 0 && this.selectedIndex < items.length) {
            items[this.selectedIndex].classList.remove('selected');
        }
        
        // 새 선택
        this.selectedIndex += direction;
        if (this.selectedIndex < 0) this.selectedIndex = items.length - 1;
        if (this.selectedIndex >= items.length) this.selectedIndex = 0;
        
        items[this.selectedIndex].classList.add('selected');
        items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
    }
    
    async createSession() {
        try {
            const response = await fetch('/api/session/new', {
                method: 'POST'
            });
            const data = await response.json();
            this.sessionId = data.session_id;
        } catch (error) {
            console.error('세션 생성 실패:', error);
        }
    }
    
    addLine(text, className = 'output', images = null) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        
        const promptSpan = document.createElement('span');
        promptSpan.className = 'prompt';
        promptSpan.textContent = className === 'output user' ? '사용자>' : '아담>';
        
        const outputSpan = document.createElement('span');
        outputSpan.className = className;
        outputSpan.textContent = text;
        
        line.appendChild(promptSpan);
        line.appendChild(outputSpan);
        
        // 이미지 추가
        if (images && images.length > 0) {
            const imageContainer = document.createElement('div');
            imageContainer.className = 'artwork-images';
            
            images.forEach(imageUrl => {
                const img = document.createElement('img');
                img.src = imageUrl;
                img.className = 'artwork-image';
                img.alt = '작품 이미지';
                img.addEventListener('click', () => {
                    // 이미지 클릭 시 새 창에서 열기
                    window.open(imageUrl, '_blank');
                });
                imageContainer.appendChild(img);
            });
            
            line.appendChild(imageContainer);
        }
        
        this.terminalBody.appendChild(line);
        this.scrollToBottom();
    }
    
    addTypingLine() {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.id = 'typing-line';
        
        const promptSpan = document.createElement('span');
        promptSpan.className = 'prompt';
        promptSpan.textContent = '아담>';
        
        const outputSpan = document.createElement('span');
        outputSpan.className = 'output';
        outputSpan.id = 'typing-output';
        
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        
        line.appendChild(promptSpan);
        line.appendChild(outputSpan);
        line.appendChild(cursor);
        
        this.terminalBody.appendChild(line);
        this.scrollToBottom();
        
        return outputSpan;
    }
    
    updateTypingLine(text) {
        const outputSpan = document.getElementById('typing-output');
        if (outputSpan) {
            outputSpan.textContent = text;
            this.scrollToBottom();
        }
    }
    
    removeTypingLine() {
        const typingLine = document.getElementById('typing-line');
        if (typingLine) {
            typingLine.remove();
        }
    }
    
    scrollToBottom() {
        this.terminalBody.scrollTop = this.terminalBody.scrollHeight;
    }
    
    async handleInput() {
        const message = this.userInput.value.trim();
        if (!message || this.isProcessing) {
            return;
        }
        
        // 사용자 입력 표시
        this.addLine(message, 'output user');
        this.userInput.value = '';
        this.isProcessing = true;
        this.userInput.disabled = true;
        
        // 타이핑 라인 추가
        const typingOutput = this.addTypingLine();
        let fullResponse = '';
        
        try {
            // API 호출 (스트리밍)
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let imageUrls = [];
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data.trim()) {
                            try {
                                const json = JSON.parse(data);
                                if (json.token) {
                                    fullResponse += json.token;
                                    this.updateTypingLine(fullResponse);
                                }
                                if (json.images) {
                                    imageUrls = json.images;
                                }
                                if (json.done) {
                                    break;
                                }
                            } catch (e) {
                                // JSON 파싱 오류 무시
                            }
                        }
                    }
                }
            }
            
            // 타이핑 라인을 최종 라인으로 변환
            this.removeTypingLine();
            this.addLine(fullResponse || '응답이 없습니다.', 'output', imageUrls.length > 0 ? imageUrls : null);
            
        } catch (error) {
            console.error('오류:', error);
            this.removeTypingLine();
            this.addLine(`오류가 발생했습니다: ${error.message}`, 'output error');
        } finally {
            this.isProcessing = false;
            this.userInput.disabled = false;
            this.userInput.focus();
        }
    }
}

// 페이지 로드 시 터미널 초기화
document.addEventListener('DOMContentLoaded', () => {
    new Terminal();
});

