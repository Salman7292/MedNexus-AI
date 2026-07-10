// DOM Elements
const sidebar = document.getElementById('sidebar');
const logsPanel = document.getElementById('logs-panel');
const chatContainer = document.getElementById('chat-container');
const chatMessagesArea = document.getElementById('chat-messages-area');
const logsContainer = document.getElementById('logs-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const mobileOverlay = document.getElementById('mobile-overlay');
const newChatBtn = document.getElementById('new-chat-btn');
const scrollBottomBtn = document.getElementById('scroll-bottom-btn');

const imageInput = document.getElementById('image-input');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const imageName = document.getElementById('image-name');
const imageSize = document.getElementById('image-size');
const voiceBtn = document.getElementById('voice-btn');
const voicePulse = document.getElementById('voice-pulse');
const autoSendToggle = document.getElementById('auto-send-toggle');
const autoSpeakToggle = document.getElementById('auto-speak-toggle');
const voiceSelectContainer = document.getElementById('voice-options-container');
const voiceDropdownBtn = document.getElementById('voice-dropdown-btn');
const voiceDropdownMenu = document.getElementById('voice-dropdown-menu');
const currentVoiceNameDisplay = document.getElementById('current-voice-name');
const handsFreeToggle = document.getElementById('hands-free-toggle');
const stopBtn = document.getElementById('stop-btn');
const mobileHandsFreeToggle = document.getElementById('mobile-hands-free-toggle');

// Voice Mode Modal Elements
const voiceModeModal = document.getElementById('voice-mode-modal');
const voiceModeTrigger = document.getElementById('voice-mode-trigger');
const closeVoiceModeBtn = document.getElementById('close-voice-mode');
const voiceStatusText = document.getElementById('voice-status');
const modalTranscript = document.getElementById('modal-transcript');
const modalAiFeedback = document.getElementById('modal-ai-feedback');
const voiceOrb = document.getElementById('voice-orb');
const orbListeningBg = document.getElementById('orb-listening-bg');

// Modal Image Elements
const modalUploadTrigger = document.getElementById('modal-upload-trigger');
const modalImagePreviewContainer = document.getElementById('modal-image-preview-container');
const modalImagePreview = document.getElementById('modal-image-preview');
const removeModalImageBtn = document.getElementById('remove-modal-image');
const modalTypeTrigger = document.getElementById('modal-type-trigger');
const modalStopBtn = document.getElementById('modal-stop-btn');
const modalRightSpacer = document.getElementById('modal-right-spacer');

const SPECIALIST = 'general';

// State
let isSidebarCollapsed = false;
let sidebarWasCollapsedBeforeLightbox = false;
let sidebarWasCollapsedBeforeVault = false;

let currentThreadId = null;
let selectedImage = null;
let isRecording = false;
let recognition = null;
let silenceTimer = null;
let currentUtterance = null;
let abortController = null;
let currentMediaItems = [];
let currentMediaIndex = -1;
let isVoiceModeActive = false;

// --- Settings Popover Logic ---
function toggleSettingsMenu() {
    const popover = document.getElementById('settings-popover');
    if (popover) {
        const isHidden = popover.classList.contains('hidden');
        if (isHidden) {
            populateVoiceList();
            if (autoSendToggle) {
                const savedAutoSend = localStorage.getItem('autoSendEnabled');
                if (savedAutoSend !== null) autoSendToggle.checked = savedAutoSend === 'true';
            }
            if (autoSpeakToggle) {
                const savedAutoSpeak = localStorage.getItem('autoSpeakEnabled');
                if (savedAutoSpeak !== null) autoSpeakToggle.checked = savedAutoSpeak === 'true';
            }
        }
        popover.classList.toggle('hidden');
    }
}

document.addEventListener('mousedown', function (event) {
    const popover = document.getElementById('settings-popover');
    const toggleBtn = document.getElementById('settings-toggle-btn');
    if (popover && !popover.classList.contains('hidden')) {
        if (!popover.contains(event.target) && !toggleBtn.contains(event.target)) {
            popover.classList.add('hidden');
        }
    }
});

// --- Typing Animation Helper ---
function typeText(element, text, speed = 30, callback) {
    element.innerHTML = "";
    let i = 0;
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    cursor.textContent = '|';
    element.appendChild(cursor);

    function type() {
        if (i < text.length) {
            cursor.before(text.charAt(i));
            i++;
            setTimeout(type, speed);
        } else {
            cursor.remove();
            if (callback) callback();
        }
    }
    type();
}

// --- Scrolling Navigation ---
function scrollToBottom() {
    if (!chatContainer) return;
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
}

if (chatContainer) {
    chatContainer.addEventListener('scroll', () => {
        const threshold = 300;
        const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < threshold;
        if (isNearBottom) {
            scrollBottomBtn?.classList.add('translate-y-4', 'opacity-0', 'pointer-events-none');
        } else {
            scrollBottomBtn?.classList.remove('translate-y-4', 'opacity-0', 'pointer-events-none');
        }
    });
}

function showWelcomeMessage() {
    const welcomeHtml = `
        <div id="welcome-message" class="flex flex-col items-center justify-center mt-4 md:mt-8 text-center space-y-4">
            <img src="/static/ai_doctor_logo.gif" alt="AI Doctor Logo" class="w-32 h-32 object-contain rounded-full shadow-lg dark:shadow-none bg-white dark:bg-transparent p-1 animate-fade-in">
            <h1 id="welcome-title" class="text-2xl md:text-3xl font-medium text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-emerald-600 dark:from-brand-200 dark:to-white min-h-[2.5rem]">
            </h1>
            <p id="welcome-subtitle" class="text-gray-500 dark:text-gray-400 max-w-md text-sm md:text-base min-h-[1.5rem]">
            </p>
        </div>
    `;

    if (chatMessagesArea) chatMessagesArea.innerHTML = welcomeHtml;
    else chatContainer.innerHTML = welcomeHtml;

    // Hide Media Vault button on welcome screen
    const mediaVaultBtn = document.getElementById('media-vault-trigger');
    if (mediaVaultBtn) mediaVaultBtn.classList.add('hidden');

    const titleEl = document.getElementById('welcome-title');
    const subtitleEl = document.getElementById('welcome-subtitle');

    typeText(titleEl, "Hello, I'm Dr. Alara.", 40, () => {
        typeText(subtitleEl, "How can I help you regarding your general health today?", 20);
    });
}

// --- Voice Mode Modal Logic ---

function openVoiceMode() {
    if (!voiceModeModal) return;
    isVoiceModeActive = true;
    voiceModeModal.classList.remove('hidden');
    voiceModeModal.classList.add('active');
    document.body.style.overflow = 'hidden'; 

    if (window.innerWidth < 1024 && sidebar && !sidebar.classList.contains('-translate-x-full')) {
        toggleSidebarMobile();
    }

    const isAutoSend = (autoSendToggle && autoSendToggle.checked) || (mobileAutoSendToggle && mobileAutoSendToggle.checked);
    if (!isAutoSend) {
        if (autoSendToggle) autoSendToggle.click();
        else if (mobileAutoSendToggle) mobileAutoSendToggle.click();
    }
    const isAutoSpeak = (autoSpeakToggle && autoSpeakToggle.checked) || (mobileAutoSpeakToggle && mobileAutoSpeakToggle.checked);
    if (!isAutoSpeak) {
        if (autoSpeakToggle) autoSpeakToggle.click();
        else if (mobileAutoSpeakToggle) mobileAutoSpeakToggle.click();
    }
    const isHandsFree = (handsFreeToggle && handsFreeToggle.checked) || (mobileHandsFreeToggle && mobileHandsFreeToggle.checked);
    if (!isHandsFree) {
        if (handsFreeToggle) handsFreeToggle.click();
        else if (mobileHandsFreeToggle) mobileHandsFreeToggle.click();
    }

    if (selectedImage) {
        const reader = new FileReader();
        reader.onload = function (e) {
            if (modalImagePreview) modalImagePreview.src = e.target.result;
            if (modalImagePreviewContainer) modalImagePreviewContainer.classList.remove('hidden');
        };
        reader.readAsDataURL(selectedImage);
    } else {
        if (modalImagePreviewContainer) modalImagePreviewContainer.classList.add('hidden');
    }

    if (!isRecording) {
        toggleVoiceInput();
    }
    updateVoiceModalUI('ready');
}

function closeVoiceMode() {
    if (!voiceModeModal) return;
    isVoiceModeActive = false;
    voiceModeModal.classList.add('hidden');
    voiceModeModal.classList.remove('active');
    document.body.style.overflow = ''; 
    if (userInput) userInput.disabled = false;

    if (isRecording) {
        toggleVoiceInput();
    }

    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }

    const isAutoSend = (autoSendToggle && autoSendToggle.checked) || (mobileAutoSendToggle && mobileAutoSendToggle.checked);
    if (isAutoSend) {
        if (autoSendToggle) autoSendToggle.click();
        else if (mobileAutoSendToggle) mobileAutoSendToggle.click();
    }
    const isAutoSpeak = (autoSpeakToggle && autoSpeakToggle.checked) || (mobileAutoSpeakToggle && mobileAutoSpeakToggle.checked);
    if (isAutoSpeak) {
        if (autoSpeakToggle) autoSpeakToggle.click();
        else if (mobileAutoSpeakToggle) mobileAutoSpeakToggle.click();
    }
    const isHandsFree = (handsFreeToggle && handsFreeToggle.checked) || (mobileHandsFreeToggle && mobileHandsFreeToggle.checked);
    if (isHandsFree) {
        if (handsFreeToggle) handsFreeToggle.click();
        else if (mobileHandsFreeToggle) mobileHandsFreeToggle.click();
    }

    setTimeout(() => {
        if (userInput) {
            userInput.focus();
        }
    }, 100);
}

function updateVoiceModalUI(state, text = '') {
    if (!voiceStatusText) return;

    switch (state) {
        case 'listening':
            voiceStatusText.textContent = 'Listening...';
            voiceStatusText.classList.replace('text-brand-500', 'text-green-500');
            voiceStatusText.classList.replace('text-brand-400', 'text-green-400');
            orbListeningBg?.classList.remove('hidden');
            voiceOrb?.classList.add('scale-105', 'shadow-[0_0_100px_rgba(34,197,94,0.4)]');
            break;
        case 'thinking':
            voiceStatusText.textContent = 'Thinking...';
            voiceStatusText.classList.replace('text-green-500', 'text-brand-500');
            voiceStatusText.classList.replace('text-green-400', 'text-brand-400');
            orbListeningBg?.classList.add('hidden');
            modalAiFeedback?.classList.remove('opacity-0');
            voiceOrb?.classList.remove('scale-105', 'shadow-[0_0_100px_rgba(34,197,94,0.4)]');
            modalStopBtn?.classList.remove('hidden');
            modalRightSpacer?.classList.add('hidden');
            break;
        case 'speaking':
            voiceStatusText.textContent = 'Speaking...';
            voiceStatusText.classList.replace('text-green-500', 'text-brand-500');
            voiceStatusText.classList.replace('text-green-400', 'text-brand-400');
            orbListeningBg?.classList.add('hidden');
            modalAiFeedback?.classList.add('opacity-0');
            if (modalTranscript && text) modalTranscript.textContent = text;
            break;
        case 'ready':
        default:
            voiceStatusText.textContent = 'Ready...';
            voiceStatusText.classList.replace('text-green-500', 'text-brand-500');
            voiceStatusText.classList.replace('text-green-400', 'text-brand-400');
            orbListeningBg?.classList.add('hidden');
            modalAiFeedback?.classList.add('opacity-0');
            voiceOrb?.classList.remove('scale-105', 'shadow-[0_0_100px_rgba(34,197,94,0.4)]');
            modalStopBtn?.classList.add('hidden');
            modalRightSpacer?.classList.remove('hidden');
            if (modalTranscript && text) modalTranscript.textContent = text;
            break;
    }
}

// --- Helpers ---
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// --- Image Upload Helpers ---
function handleImageSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    selectedImage = file;
    const reader = new FileReader();
    reader.onload = function (e) {
        imagePreview.src = e.target.result;
        imageName.textContent = file.name;
        imageSize.textContent = formatBytes(file.size);
        imagePreviewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
    if (sendBtn) {
        sendBtn.classList.remove('scale-0', 'opacity-0');
        sendBtn.classList.add('scale-100', 'opacity-100');
    }
}

function clearImage() {
    selectedImage = null;
    imageInput.value = '';
    imagePreviewContainer.classList.add('hidden');
    imagePreview.src = '';
    if (sendBtn && (!userInput.value.trim().length > 0)) {
        sendBtn.classList.remove('scale-100', 'opacity-100');
        sendBtn.classList.add('scale-0', 'opacity-0');
    }
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// --- Voice Recognition ---
function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isRecording = true;
        voicePulse.classList.remove('hidden');
        voiceBtn.classList.add('text-brand-600', 'dark:text-brand-400');
    };

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        userInput.value = transcript;
        if (silenceTimer) clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (userInput.value.trim() && isRecording) {
                if (autoSendToggle && autoSendToggle.checked) sendMessage();
                else stopVoiceInput();
            }
        }, 2000);
    };

    recognition.onend = () => {
        stopVoiceInput();
        
        // Hands-Free Loop
        const isHandsFree = (handsFreeToggle && handsFreeToggle.checked) || (mobileHandsFreeToggle && mobileHandsFreeToggle.checked);
        if (isHandsFree && isVoiceModeActive && !window.speechSynthesis.speaking) {
             // If we ended recognition while in voice mode and not currently talking, restart
             setTimeout(() => {
                if (!isRecording && !window.speechSynthesis.speaking) toggleVoiceInput();
             }, 1000);
        }
    };
}

function toggleVoiceInput() {
    if (!recognition) initSpeechRecognition();
    if (!recognition) return;
    if (isRecording) { recognition.stop(); stopVoiceInput(); }
    else { userInput.value = ''; recognition.start(); }
}

function stopVoiceInput() {
    isRecording = false;
    voicePulse.classList.add('hidden');
    voiceBtn.classList.remove('text-brand-600', 'dark:text-brand-400');
    if (userInput) userInput.focus();
}

// --- Hands-Free Mode Toggle Initialization ---

function initHandsFreeToggle() {
    const savedState = localStorage.getItem('handsFreeEnabled');
    const isEnabled = savedState === 'true';

    if (handsFreeToggle) {
        if (savedState !== null) handsFreeToggle.checked = isEnabled;
        handsFreeToggle.addEventListener('change', () => {
            localStorage.setItem('handsFreeEnabled', handsFreeToggle.checked);
            if (mobileHandsFreeToggle) mobileHandsFreeToggle.checked = handsFreeToggle.checked;
        });
    }

    if (mobileHandsFreeToggle) {
        if (savedState !== null) mobileHandsFreeToggle.checked = isEnabled;
        mobileHandsFreeToggle.addEventListener('change', () => {
            localStorage.setItem('handsFreeEnabled', mobileHandsFreeToggle.checked);
            if (handsFreeToggle) handsFreeToggle.checked = mobileHandsFreeToggle.checked;
        });
    }
}

function initAutoSendToggle() {
    const savedState = localStorage.getItem('autoSendEnabled');
    const isEnabled = savedState === 'true';
    if (autoSendToggle) {
        if (savedState !== null) autoSendToggle.checked = isEnabled;
        autoSendToggle.addEventListener('change', () => {
            localStorage.setItem('autoSendEnabled', autoSendToggle.checked);
        });
    }
}

function initAutoSpeakToggle() {
    const savedState = localStorage.getItem('autoSpeakEnabled');
    const isEnabled = savedState === 'true';
    if (autoSpeakToggle) {
        if (savedState !== null) autoSpeakToggle.checked = isEnabled;
        autoSpeakToggle.addEventListener('change', () => {
            localStorage.setItem('autoSpeakEnabled', autoSpeakToggle.checked);
        });
    }
}

initAutoSendToggle();
initAutoSpeakToggle();
initHandsFreeToggle();

// --- Theme & Settings ---
function initTheme() {
    const storedTheme = localStorage.getItem('color-theme');
    const theme = storedTheme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.classList[theme === 'dark' ? 'add' : 'remove']('dark');
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('color-theme', isDark ? 'dark' : 'light');
}

function populateVoiceList() {
    if (!voiceSelectContainer) return;
    const voices = window.speechSynthesis.getVoices();
    voiceSelectContainer.innerHTML = '';
    const savedVoice = localStorage.getItem('selectedVoiceName');

    voices.forEach(voice => {
        const option = document.createElement('button');
        option.className = "w-full text-left px-4 py-2 text-[10px] font-bold text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors uppercase tracking-tight";
        option.textContent = voice.name;
        if (savedVoice === voice.name) {
            option.classList.add('bg-brand-50/50', 'dark:bg-brand-900/20', 'text-brand-600', 'dark:text-brand-400');
            if (currentVoiceNameDisplay) currentVoiceNameDisplay.textContent = voice.name;
        }
        option.onclick = () => {
            localStorage.setItem('selectedVoiceName', voice.name);
            if (currentVoiceNameDisplay) currentVoiceNameDisplay.textContent = voice.name;
            toggleSettingsMenu();
        };
        voiceSelectContainer.appendChild(option);
    });
}

// --- Thread & History ---
async function loadThreads() {
    try {
        const response = await fetch('/threads?specialist=general');
        const threads = await response.json();
        const list = document.getElementById('conversations-list');
        if (!list) return;
        list.innerHTML = threads.map(t => `
            <div class="relative group/item mb-1">
                <button onclick="loadHistory('${t.thread_id}')" class="w-full px-3 py-2.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-left transition-all conversation-item ${t.thread_id === currentThreadId ? 'active bg-brand-50/50 ring-1 ring-brand-200 dark:ring-brand-900/30' : ''}">
                    <div class="flex items-center justify-between gap-2">
                        <div class="text-sm font-semibold text-gray-700 dark:text-gray-200 truncate flex-1">${t.title}</div>
                        <div class="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
                            <button onclick="event.stopPropagation(); showConversationMenu(event, '${t.thread_id}')" 
                                class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors">
                                <i class="fa-solid fa-ellipsis-vertical text-xs"></i>
                            </button>
                        </div>
                    </div>
                </button>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

async function loadHistory(threadId) {
    currentThreadId = threadId;
    if (chatMessagesArea) chatMessagesArea.innerHTML = '';
    try {
        const response = await fetch(`/history/${threadId}?specialist=general`);
        const data = await response.json();
        if (data.messages) data.messages.forEach(msg => appendMessage(msg.role, msg.content, false, msg.index));
        else showWelcomeMessage();

        // Check for media to show/hide Media Vault button
        const hasMedia = data.messages && data.messages.some(msg => {
            const content = msg.content;
            if (typeof content === 'object' && content && content.image) return true;
            if (typeof content === 'string' && isHtmlReport(content)) return true;
            return false;
        });
        const mediaVaultBtn = document.getElementById('media-vault-trigger');
        if (mediaVaultBtn) {
            if (hasMedia) mediaVaultBtn.classList.remove('hidden');
            else mediaVaultBtn.classList.add('hidden');
        }

        loadThreads();
        scrollToBottom();
    } catch (e) { console.error(e); }
}

function startNewChat() {
    currentThreadId = generateUUID();
    showWelcomeMessage();
    loadThreads();
}

// --- Messaging ---
function appendMessage(role, content, animate = true, index = null) {
    if (role === 'ai' && !content) return;

    const isUser = role === 'user';
    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const div = document.createElement('div');
    div.className = `flex w-full ${isUser ? 'justify-end items-end gap-3' : 'justify-start'} mb-8 animate-fade-in group`;
    if (index !== null) div.setAttribute('data-index', index);

    const bubbleWrapper = document.createElement('div');
    bubbleWrapper.className = `message-bubble ${isUser ? 'max-w-[70%]' : 'w-full max-w-[85%]'}`;

    // Header label - ONLY for AI
    const headerHtml = isUser ? '' : `
        <div class="flex items-center gap-2 mb-1 pl-1">
             <span class="text-xs font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-emerald-600 dark:from-brand-400 dark:to-emerald-400 uppercase tracking-wider">Dr. Alara</span>
             <span class="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium">General Physician</span>
        </div>
    `;

    const bubble = document.createElement('div');
    bubble.className = isUser
        ? "bg-brand-600 text-white rounded-2xl px-4 py-2.5 shadow-lg text-base font-normal leading-relaxed text-justify rounded-br-sm transform translate-y-[-8px] relative"
        : "border border-gray-100 dark:border-gray-700/50 shadow-sm rounded-2xl p-4 text-gray-800 dark:text-gray-200 text-base font-normal leading-relaxed text-left rounded-tl-sm relative";

    const textContent = typeof content === 'object' ? content.text : content;
    const messageImage = typeof content === 'object' ? content.image : null;
    const renderedText = isUser ? textContent : marked.parse(textContent);

    if (isUser) {
        bubble.innerHTML = `
            <div class="message-text break-words text-justify">${renderedText}</div>
            <div class="flex justify-end items-center mt-2">
                <span class="text-[10px] text-white/70">${timeString}</span>
            </div>
        `;

        if (messageImage) {
            const imgPreviewEl = document.createElement('div');
            imgPreviewEl.className = 'flex justify-end mb-[0.7rem]';
            imgPreviewEl.innerHTML = `<img src="${messageImage}" class="w-64 max-w-full rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm" alt="Uploaded image">`;
            bubbleWrapper.appendChild(imgPreviewEl);
        }

        const avatar = document.createElement('div');
        avatar.className = "w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm ring-2 ring-blue-100 dark:ring-blue-900/30 overflow-hidden mb-1";
        avatar.innerHTML = window.currentProfilePic ? `<img src="${window.currentProfilePic}" class="w-full h-full object-cover">` : (window.currentUser || 'P')[0].toUpperCase();

        if (textContent && textContent.trim().length > 0) {
            bubbleWrapper.appendChild(bubble);
        } else if (!messageImage) {
            bubbleWrapper.appendChild(bubble);
        }

        div.appendChild(bubbleWrapper);
        div.appendChild(avatar);
    } else {
        bubble.innerHTML = `
            <div class="prose prose-invert max-w-none message-content leading-relaxed">
                ${renderedText}
            </div>
            <div class="flex justify-between items-center mt-2">
                <span class="text-[10px] text-gray-400 dark:text-gray-500">${timeString}</span>
            </div>
        `;
        bubbleWrapper.innerHTML = headerHtml;
        bubbleWrapper.appendChild(bubble);
        div.appendChild(bubbleWrapper);
    }

    (chatMessagesArea || chatContainer).appendChild(div);
    if (animate) scrollToBottom();
    return bubble;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text && !selectedImage) return;

    if (chatMessagesArea?.querySelector('#welcome-message')) chatMessagesArea.innerHTML = '';
    userInput.value = '';
    appendMessage('user', text);

    // Show Media Vault button if user sent an image
    if (selectedImage) {
        const mediaVaultBtn = document.getElementById('media-vault-trigger');
        if (mediaVaultBtn) mediaVaultBtn.classList.remove('hidden');
    }

    const formData = new FormData();
    formData.append('message', text);
    formData.append('thread_id', currentThreadId);
    formData.append('specialist', 'general');
    if (selectedImage) formData.append('image', selectedImage);
    clearImage();

    showTypingIndicator();
    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";
        let aiBubble = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const event = JSON.parse(line.replace('data: ', ''));
                        if (event.type === 'token') {
                            if (!aiBubble) { removeTypingIndicator(); aiBubble = appendMessage('ai', ''); }
                            accumulated += event.content;
                            aiBubble.innerHTML = marked.parse(accumulated);

                            // Check if this content might be a report and show media vault
                            if (isHtmlReport(accumulated)) {
                                const mb = document.getElementById('media-vault-trigger');
                                if (mb) mb.classList.remove('hidden');
                            }

                            scrollToBottom();
                        } else if (event.type.startsWith('tool')) appendLog(event.type, event);
                }
            }
        }
    } catch (e) { console.error(e); removeTypingIndicator(); }
}

function showTypingIndicator() {
    const div = document.createElement('div');
    div.id = 'typing-indicator';
    div.className = 'flex justify-start mb-8';
    div.innerHTML = '<div class="message-bubble"><div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-2xl italic text-xs">Dr. Alara is thinking...</div></div>';
    (chatMessagesArea || chatContainer).appendChild(div);
    scrollToBottom();
}

function removeTypingIndicator() {
    document.getElementById('typing-indicator')?.remove();
}

function appendLog(type, data) {
    if (!logsContainer) return;

    // Auto-open logs panel on tool start
    if (type === 'tool_start') {
        openLogs();
    }

    const log = document.createElement('div');
    log.className = "text-[10px] p-2 mb-2 bg-gray-50 dark:bg-gray-800 rounded border border-gray-100 dark:border-gray-700 font-mono";
    log.innerHTML = `<span class="text-brand-500 font-bold">[${type.toUpperCase()}]</span> ${JSON.stringify(data.args || data.output || data)}`;
    logsContainer.appendChild(log);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function toggleSidebar() { sidebar.classList.toggle('collapsed'); }
function toggleSidebarMobile() { sidebar.classList.toggle('-translate-x-full'); mobileOverlay.classList.toggle('hidden'); }
// --- Progress/Logs Panel Helpers ---
function openLogs() {
    if (!logsPanel) return;
    const logsToggleBtn = document.getElementById('logs-toggle-btn');

    // Remove all hidden/collapsed states
    logsPanel.classList.remove('hidden');
    // Force reflow
    logsPanel.offsetHeight;

    logsPanel.classList.remove('translate-x-full', 'opacity-0', 'md:w-0');
    logsPanel.classList.add('translate-x-0', 'opacity-100', 'md:w-80');

    // Hide header trigger
    if (logsToggleBtn) {
        logsToggleBtn.classList.add('opacity-0', 'pointer-events-none', 'scale-95');
    }
}

function closeLogs() {
    if (!logsPanel) return;
    const logsToggleBtn = document.getElementById('logs-toggle-btn');

    // Animate to closed state
    logsPanel.classList.add('translate-x-full', 'opacity-0', 'md:w-0');
    logsPanel.classList.remove('translate-x-0', 'opacity-100', 'md:w-80');

    // Show header trigger
    if (logsToggleBtn) {
        logsToggleBtn.classList.remove('opacity-0', 'pointer-events-none', 'scale-95');
    }

    // Wait for animation then add hidden
    setTimeout(() => {
        if (logsPanel.classList.contains('translate-x-full')) {
            logsPanel.classList.add('hidden');
        }
    }, 300);
}

function toggleLogs() {
    if (!logsPanel) return;
    // Check if it's currently hidden either by hidden class or by md:w-0
    const isHidden = logsPanel.classList.contains('hidden') || logsPanel.classList.contains('md:w-0');
    if (isHidden) {
        openLogs();
    } else {
        closeLogs();
    }
}


// --- Text-to-Speech Helper ---

function speakText(text, btn) {
    if (!('speechSynthesis' in window)) return;

    const resetButton = (b) => {
        if (!b) return;
        b.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 0 0 1 0 12.728M16.463 8.287a6 6 0 0 1 0 7.427M12 18.75V5.25A2.25 2.25 0 0 0 9.75 3H7.5a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h2.25a2.25 2.25 0 0 0 2.25-2.25Z" /></svg>';
        b.classList.remove('text-brand-600');
    };

    if (btn && btn.classList.contains('text-brand-600')) {
        window.speechSynthesis.cancel();
        currentUtterance = null;
        resetButton(btn);
        return;
    }

    window.speechSynthesis.cancel();
    document.querySelectorAll('.speak-btn.text-brand-600').forEach(b => resetButton(b));

    let cleanText = text.replace(/<[^>]*>/g, '').replace(/[*#_~`|-]/g, '').replace(/\s+/g, ' ').trim();
    if (!cleanText) return;

    currentUtterance = new SpeechSynthesisUtterance(cleanText);
    const voices = window.speechSynthesis.getVoices();
    const savedVoiceName = localStorage.getItem('selectedVoiceName');
    let selectedVoice = voices.find(v => v.name === savedVoiceName) || voices.find(v => v.lang === 'en-US') || voices[0];
    if (selectedVoice) currentUtterance.voice = selectedVoice;

    currentUtterance.onstart = () => {
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-volume-high animate-pulse text-brand-600"></i>';
            btn.classList.add('text-brand-600');
        }
        if (isVoiceModeActive) updateVoiceModalUI('speaking', text);
    };

    currentUtterance.onend = () => {
        if (btn) resetButton(btn);
        currentUtterance = null;

        const isHandsFree = (handsFreeToggle && handsFreeToggle.checked) || (mobileHandsFreeToggle && mobileHandsFreeToggle.checked);
        if (isHandsFree) {
            if (isVoiceModeActive) updateVoiceModalUI('ready', "Listening or your response...");
            setTimeout(() => { if (!isRecording) toggleVoiceInput(); }, 1000);
        } else if (isVoiceModeActive) {
            updateVoiceModalUI('ready');
        }
    };

    currentUtterance.onerror = (e) => {
        console.error(e);
        if (btn) resetButton(btn);
        currentUtterance = null;
    };

    window.speechSynthesis.speak(currentUtterance);
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initAutoSendToggle();
    initAutoSpeakToggle();
    initHandsFreeToggle();
    startNewChat();
    loadThreads();
    if (userInput) {
        userInput.addEventListener('input', () => {
            if (sendBtn) sendBtn.classList[userInput.value.trim() ? 'remove' : 'add']('scale-0', 'opacity-0');
            if (sendBtn) sendBtn.classList[userInput.value.trim() ? 'add' : 'remove']('scale-100', 'opacity-100');
        });
        userInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    }
});

// --- MEDIA VAULT & LIGHTBOX LOGIC ---

function isHtmlReport(text) {
    if (typeof text !== 'string') return false;
    return text.includes('clip-path-header') || text.includes('medical-report') || text.includes('report-container');
}

function showConversationMenu(event, threadId, anchorEl) {
    const existingMenu = document.getElementById('conversation-context-menu');
    if (existingMenu) existingMenu.remove();

    const menu = document.createElement('div');
    menu.id = 'conversation-context-menu';
    menu.className = 'fixed bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl shadow-2xl py-1 w-48 z-[100] animate-in fade-in zoom-in duration-200';

    const targetBtn = anchorEl || event.currentTarget || event.target.closest('button');
    const rect = targetBtn.getBoundingClientRect();
    const menuWidth = 192; // 48 * 4 (w-48)
    let leftPos = rect.left - 160;

    // Clamp to viewport
    if (leftPos < 10) leftPos = 10;
    if (leftPos + menuWidth > window.innerWidth - 10) leftPos = window.innerWidth - menuWidth - 10;

    menu.style.top = `${rect.bottom + 8}px`;
    menu.style.left = `${leftPos}px`;

    menu.innerHTML = `
        <button onclick="openMediaVault('${threadId}')" class="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors first:rounded-t-xl last:rounded-b-xl">
            <i class="fa-solid fa-photo-film text-brand-500"></i>
            <span>Media Vault</span>
        </button>
    `;

    document.body.appendChild(menu);

    setTimeout(() => {
        const closeMenu = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        document.addEventListener('click', closeMenu);
    }, 10);
}

function toggleMediaVault() {
    const panel = document.getElementById('media-vault-panel');
    const sidebar = document.getElementById('sidebar');
    if (!panel) return;
    
    if (panel.classList.contains('hidden')) {
        // Opening
        panel.classList.remove('hidden');
        panel.classList.add('flex');
        
        // Hide sidebar completely
        if (sidebar) sidebar.classList.add('hidden');
    } else {
        // Closing
        panel.classList.add('hidden');
        panel.classList.remove('flex');
        
        // Restore sidebar visibility
        if (sidebar) sidebar.classList.remove('hidden');
    }
}

async function openMediaVault(threadId) {
    // Close context menu
    document.getElementById('conversation-context-menu')?.remove();
    
    toggleMediaVault();
    const grid = document.getElementById('media-vault-grid');
    const emptyState = document.getElementById('media-vault-empty');
    if (!grid) return;

    grid.innerHTML = '<div class="col-span-2 py-10 flex justify-center"><i class="fa-solid fa-spinner animate-spin text-2xl text-brand-500"></i></div>';
    emptyState.classList.add('hidden');

    try {
        const response = await fetch(`/history/${threadId}?specialist=general`);
        const data = await response.json();
        const mediaItems = [];

        if (data.messages) {
            data.messages.forEach(msg => {
                if (typeof msg.content === 'object' && msg.content.image) {
                    mediaItems.push({ url: msg.content.image, type: 'Image', date: msg.timestamp || '' });
                } else if (typeof msg.content === 'string' && isHtmlReport(msg.content)) {
                    mediaItems.push({ content: msg.content, type: 'Report', date: msg.timestamp || '' });
                }
            });
        }

        grid.innerHTML = '';
        if (mediaItems.length === 0) {
            currentMediaItems = [];
            emptyState.classList.remove('hidden');
        } else {
            currentMediaItems = mediaItems;
            mediaItems.forEach((item, idx) => {
                const card = document.createElement('div');
                card.className = 'group/card relative aspect-square rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-brand-500 transition-all cursor-pointer shadow-sm';
                
                if (item.type === 'Report') {
                    card.innerHTML = `
                        <div class="w-full h-full flex flex-col items-center justify-center p-3 text-center">
                            <i class="fa-solid fa-file-invoice text-3xl text-brand-500 mb-2"></i>
                            <span class="text-[10px] font-bold text-gray-500 uppercase tracking-widest leading-tight">Medical Report</span>
                        </div>
                    `;
                } else {
                    card.innerHTML = `<img src="${item.url}" class="w-full h-full object-cover">`;
                }
                
                card.innerHTML += `<div class="absolute inset-0 bg-black/40 opacity-0 group-hover/card:opacity-100 transition-opacity flex items-center justify-center">
                    <i class="fa-solid fa-expand text-white text-xl"></i>
                </div>`;
                
                card.onclick = () => openLightbox(idx);
                grid.appendChild(card);
            });
        }
    } catch (e) {
        console.error(e);
        grid.innerHTML = '<div class="col-span-2 py-10 text-center text-red-500 text-xs">Failed to load media</div>';
    }
}

function openLightbox(index) {
    if (index < 0 || index >= currentMediaItems.length) return;
    currentMediaIndex = index;
    const item = currentMediaItems[index];
    const lightbox = document.getElementById('media-lightbox');
    const content = document.getElementById('lightbox-content');
    const typeLabel = document.getElementById('lightbox-type');
    
    if (!lightbox || !content) return;

    // Hide sidebar completely
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.add('hidden');

    typeLabel.textContent = item.type.toUpperCase();
    content.innerHTML = item.type === 'Report' 
        ? `<div class="bg-white dark:bg-gray-900 p-8 rounded-2xl max-w-4xl max-h-full overflow-y-auto custom-scrollbar shadow-2xl mx-auto">${item.content}</div>`
        : `<img src="${item.url}" class="max-w-full max-h-full object-contain rounded-lg shadow-2xl mx-auto">`;

    lightbox.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    document.getElementById('media-lightbox')?.classList.add('hidden');
    document.body.style.overflow = '';

    // Restore sidebar visibility only if the vault panel is also closed
    const sidebar = document.getElementById('sidebar');
    const panel = document.getElementById('media-vault-panel');
    const vaultHidden = !panel || panel.classList.contains('hidden');
    
    if (sidebar && vaultHidden) {
        sidebar.classList.remove('hidden');
    }
}

function navigateLightbox(direction) {
    const newIndex = currentMediaIndex + direction;
    if (newIndex >= 0 && newIndex < currentMediaItems.length) {
        openLightbox(newIndex);
    }
}

// Add download functionality
document.getElementById('download-media-btn')?.addEventListener('click', async () => {
    const item = currentMediaItems[currentMediaIndex];
    if (!item) return;

    if (item.type === 'Image') {
        const link = document.createElement('a');
        link.href = item.url;
        link.download = `medical-image-${Date.now()}.png`;
        link.click();
    } else {
        const reportEl = document.querySelector('#lightbox-content > div');
        if (reportEl && typeof html2canvas !== 'undefined') {
            const canvas = await html2canvas(reportEl, { scale: 2 });
            const link = document.createElement('a');
            link.href = canvas.toDataURL('image/png');
            link.download = `medical-report-${Date.now()}.png`;
            link.click();
        }
    }
});

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    isSidebarCollapsed = !isSidebarCollapsed;

    if (isSidebarCollapsed) {
        sidebar.classList.add('collapsed');
        sidebar.classList.remove('w-64');
    } else {
        sidebar.classList.remove('collapsed');
        sidebar.classList.add('w-64');
    }
}

function toggleSidebarMobile() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobile-overlay');

    sidebar.classList.toggle('-translate-x-full');
    overlay.classList.toggle('hidden');
}
