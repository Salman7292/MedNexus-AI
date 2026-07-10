// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

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
const handsFreeToggle = document.getElementById('hands-free-toggle');
const voiceSelectContainer = document.getElementById('voice-options-container');
const voiceDropdownBtn = document.getElementById('voice-dropdown-btn');
const voiceDropdownMenu = document.getElementById('voice-dropdown-menu');
const currentVoiceNameDisplay = document.getElementById('current-voice-name');
const suggestionChipsContainer = document.getElementById('suggestion-chips-container');

// Mobile Settings Elements
const mobileAutoSendToggle = document.getElementById('mobile-auto-send-toggle');
const mobileAutoSpeakToggle = document.getElementById('mobile-auto-speak-toggle');
const mobileHandsFreeToggle = document.getElementById('mobile-hands-free-toggle');
const mobileVoiceDropdownBtn = document.getElementById('mobile-voice-dropdown-btn');
const mobileVoiceDropdownMenu = document.getElementById('mobile-voice-dropdown-menu');
const mobileVoiceOptionsContainer = document.getElementById('mobile-voice-options-container');
const mobileCurrentVoiceDisplay = document.getElementById('mobile-current-voice-name');

const stopBtn = document.getElementById('stop-btn');

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

// State
let isSidebarCollapsed = false;
let sidebarWasCollapsedBeforeLightbox = false;
let sidebarWasCollapsedBeforeVault = false;

// Settings Popover Logic
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
            if (handsFreeToggle) {
                const savedHandsFree = localStorage.getItem('handsFreeEnabled');
                if (savedHandsFree !== null) handsFreeToggle.checked = savedHandsFree === 'true';
            }
        }
        popover.classList.toggle('hidden');
    }
}

// Close settings if clicking outside
document.addEventListener('mousedown', function (event) {
    const popover = document.getElementById('settings-popover');
    const toggleBtn = document.getElementById('settings-toggle-btn');
    if (popover && !popover.classList.contains('hidden')) {
        if (!popover.contains(event.target) && !toggleBtn.contains(event.target)) {
            popover.classList.add('hidden');
        }
    }
});

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

// Typing Animation Helper
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

// --- Voice Mode Modal Logic ---

function openVoiceMode() {
    if (!voiceModeModal) return;
    isVoiceModeActive = true;
    voiceModeModal.classList.remove('hidden');
    voiceModeModal.classList.add('active');
    document.body.style.overflow = 'hidden';

    if (sidebar) sidebar.style.display = 'none';

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

    if (sidebar) sidebar.style.display = '';

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
            voiceStatusText.classList.replace('text-brand-400', 'text-green-400');
            orbListeningBg?.classList.remove('hidden');
            voiceOrb?.classList.add('scale-105', 'shadow-[0_0_100px_rgba(34,197,94,0.4)]');
            break;
        case 'thinking':
            voiceStatusText.textContent = 'Thinking...';
            voiceStatusText.classList.replace('text-green-400', 'text-brand-400');
            orbListeningBg?.classList.add('hidden');
            modalAiFeedback?.classList.remove('opacity-0');
            voiceOrb?.classList.remove('scale-105', 'shadow-[0_0_100px_rgba(34,197,94,0.4)]');
            modalStopBtn?.classList.remove('hidden');
            modalRightSpacer?.classList.add('hidden');
            break;
        case 'speaking':
            voiceStatusText.textContent = 'Speaking...';
            voiceStatusText.classList.add('text-brand-400');
            modalAiFeedback?.classList.add('opacity-0');
            voiceOrb?.classList.add('scale-110', 'shadow-[0_0_120px_rgba(55,113,76,0.6)]');
            modalStopBtn?.classList.remove('hidden');
            modalRightSpacer?.classList.add('hidden');
            break;
        default:
            voiceStatusText.textContent = 'Ready...';
            voiceStatusText.className = 'text-brand-400 text-[10px] font-medium uppercase tracking-tighter';
            orbListeningBg?.classList.add('hidden');
            voiceOrb?.classList.remove('scale-105', 'scale-110', 'shadow-[0_0_100px_rgba(34,197,94,0.4)]', 'shadow-[0_0_120px_rgba(55,113,76,0.6)]');
            modalStopBtn?.classList.add('hidden');
            modalRightSpacer?.classList.remove('hidden');
    }

    if (text && modalTranscript) {
        modalTranscript.textContent = text;
        modalTranscript.scrollTop = modalTranscript.scrollHeight;
    }
}

// Event Listeners for Voice Mode
voiceModeTrigger?.addEventListener('click', openVoiceMode);
document.getElementById('mobile-voice-mode-trigger')?.addEventListener('click', () => {
    if (window.innerWidth < 1024 && typeof toggleSidebar === 'function') {
        toggleSidebar();
    }
    openVoiceMode();
});
closeVoiceModeBtn?.addEventListener('click', closeVoiceMode);

// Modal Triggers
if (modalUploadTrigger) {
    modalUploadTrigger.addEventListener('click', () => { imageInput.click(); });
}
if (removeModalImageBtn) {
    removeModalImageBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        clearImage();
    });
}
if (modalTypeTrigger) {
    modalTypeTrigger.addEventListener('click', () => { closeVoiceMode(); });
}
if (modalStopBtn) {
    modalStopBtn.onclick = (e) => {
        e.stopPropagation();
        stopResponse();
        updateVoiceModalUI('ready', 'Response stopped.');
    };
}

// Image input event
if (imageInput) {
    imageInput.addEventListener('change', handleImageSelect);
}

// --- Auto-expanding Textarea Logic ---
if (userInput) {
    userInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.scrollHeight > 200) {
            this.style.height = '200px';
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }

        // Show/hide send button
        const hasContent = this.value.trim().length > 0 || selectedImage;
        if (sendBtn) {
            if (hasContent) {
                sendBtn.classList.remove('scale-0', 'opacity-0');
                sendBtn.classList.add('scale-100', 'opacity-100');
                const voiceModeInputBtn = document.getElementById('voice-mode-trigger-input');
                if (voiceModeInputBtn) voiceModeInputBtn.classList.add('hidden');
            } else if (!selectedImage) {
                sendBtn.classList.remove('scale-100', 'opacity-100');
                sendBtn.classList.add('scale-0', 'opacity-0');
                const voiceModeInputBtn = document.getElementById('voice-mode-trigger-input');
                if (voiceModeInputBtn) voiceModeInputBtn.classList.remove('hidden');
            }
        }
    });

    window.resetInputHeight = function () {
        userInput.style.height = 'auto';
        userInput.style.overflowY = 'hidden';
    };

    // Handle Enter key
    userInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// --- Scrolling Navigation ---
function scrollToBottom() {
    if (!chatContainer) return;
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
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
        <div id="welcome-message" class="flex flex-col items-center justify-center min-h-[60vh] md:min-h-0 md:mt-10 text-center space-y-4 px-4 no-scrollbar">
            <img src="/static/images/2.png" alt="Dr. Pharma" class="mx-auto w-32 h-32 object-contain rounded-full dark:shadow-none bg-transparent p-1 animate-fade-in">
            <h1 id="welcome-title" class="text-2xl md:text-3xl font-medium text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-indigo-600 dark:from-brand-200 dark:to-white min-h-[2.5rem]">
            </h1>
            <p id="welcome-subtitle" class="text-gray-500 dark:text-gray-400 max-w-md text-sm md:text-base min-h-[1.5rem] mb-8">
            </p>
        </div>
    `;

    if (chatMessagesArea) chatMessagesArea.innerHTML = welcomeHtml;
    else chatContainer.innerHTML = welcomeHtml;

    const mediaVaultBtn = document.getElementById('media-vault-trigger');
    if (mediaVaultBtn) mediaVaultBtn.classList.add('hidden');

    const titleEl = document.getElementById('welcome-title');
    const subtitleEl = document.getElementById('welcome-subtitle');

    typeText(titleEl, "Greetings, I'm Dr. Pharma.", 40, () => {
        typeText(subtitleEl, "Please provide your medication list or upload a prescription for analysis.", 20);
    });
}

// --- Helpers ---

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

// --- Image Upload Helpers ---

function handleImageSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (files.length > 1) {
        alert('Please select only one image at a time.');
        event.target.value = '';
        return;
    }

    const file = files[0];
    const allowedExtensions = ['png', 'jpg', 'jpeg', 'gif', 'jfif', 'webp', 'bmp', 'tiff', 'tif', 'heic', 'svg', 'ico', 'avif'];
    const fileExtension = file.name.split('.').pop().toLowerCase();

    if (!allowedExtensions.includes(fileExtension)) {
        alert('Invalid file type. Please upload a valid image file (PNG, JPG, HEIC, WebP, etc.).');
        event.target.value = '';
        return;
    }

    selectedImage = file;

    const reader = new FileReader();
    reader.onload = function (e) {
        imagePreview.src = e.target.result;
        imageName.textContent = file.name;
        imageSize.textContent = formatBytes(file.size);
        imagePreviewContainer.classList.remove('hidden');

        if (modalImagePreview) modalImagePreview.src = e.target.result;
        if (modalImagePreviewContainer) modalImagePreviewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);

    if (sendBtn) {
        sendBtn.classList.remove('scale-0', 'opacity-0');
        sendBtn.classList.add('scale-100', 'opacity-100');
    }

    if (isVoiceModeActive && modalTranscript) {
        modalTranscript.textContent = "Image added. Ready for your voice input or type to send.";
    }

    showSuggestionChips();
}

function showSuggestionChips() {
    if (!suggestionChipsContainer) return;

    const chips = [
        { label: "Analyze Report", prompt: "Please analyze this medical report and extract all relevant clinical data." },
        { label: "Interaction Check", prompt: "Check for any potential drug-drug interactions in this uploaded report." },
        { label: "Dosage Safety", prompt: "Verify if the dosages mentioned in this report are safe and standardized." },
        { label: "Simple Explanation", prompt: "Explain this medical report in very simple terms for me." },
        { label: "Med Ledger", prompt: "Generate a medication ledger from this prescription." }
    ];

    suggestionChipsContainer.innerHTML = '';
    chips.forEach(chip => {
        const chipEl = document.createElement('div');
        chipEl.className = 'suggestion-chip';
        chipEl.innerHTML = chip.label;
        chipEl.onclick = () => {
            if (userInput) {
                userInput.value = chip.prompt;
                sendMessage();
                hideSuggestionChips();
            }
        };
        suggestionChipsContainer.appendChild(chipEl);
    });

    suggestionChipsContainer.classList.remove('hidden');
}

function hideSuggestionChips() {
    if (suggestionChipsContainer) {
        suggestionChipsContainer.classList.add('hidden');
        suggestionChipsContainer.innerHTML = '';
    }
}

function clearImage() {
    selectedImage = null;
    imageInput.value = '';
    imagePreviewContainer.classList.add('hidden');
    imagePreview.src = '';
    hideSuggestionChips();

    if (modalImagePreviewContainer) modalImagePreviewContainer.classList.add('hidden');
    if (modalImagePreview) modalImagePreview.src = '';

    if (sendBtn && (!userInput.value.trim().length > 0)) {
        sendBtn.classList.remove('scale-100', 'opacity-100');
        sendBtn.classList.add('scale-0', 'opacity-0');
        const voiceModeInputBtn = document.getElementById('voice-mode-trigger-input');
        if (voiceModeInputBtn) voiceModeInputBtn.classList.remove('hidden');
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

// --- Text-to-Speech Logic ---

function speakText(text, btn) {
    if (!('speechSynthesis' in window)) return;

    const resetButton = (b) => {
        if (!b) return;
        b.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.287a6 6 0 0 1 0 7.427M12 18.75V5.25A2.25 2.25 0 0 0 9.75 3H7.5a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h2.25a2.25 2.25 0 0 0 2.25-2.25Z" /></svg>';
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

    let cleanText = text.replace(/<[^>]*>/g, '')
        .replace(/[*#_~`>|-]/g, '')
        .replace(/\s+/g, ' ')
        .trim();

    if (!cleanText) return;

    currentUtterance = new SpeechSynthesisUtterance(cleanText);

    const voices = window.speechSynthesis.getVoices();
    const savedVoiceName = localStorage.getItem('selectedVoiceName');
    let selectedVoice = voices.find(v => v.name === savedVoiceName);

    if (!selectedVoice) {
        selectedVoice = voices.find(v => v.lang === 'en-US') ||
            voices.find(v => v.lang.startsWith('en')) ||
            voices[0];
    }

    if (selectedVoice) {
        currentUtterance.voice = selectedVoice;
    }

    currentUtterance.onstart = () => {
        console.log("Speech started...");
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-volume-high animate-pulse text-brand-600"></i>';
            btn.classList.add('text-brand-600');
        }
        if (isVoiceModeActive) {
            updateVoiceModalUI('speaking', text);
        }
    };

    currentUtterance.onend = () => {
        console.log("Speech finished.");
        if (btn) resetButton(btn);
        currentUtterance = null;

        const isHandsFree = (handsFreeToggle && handsFreeToggle.checked) || (mobileHandsFreeToggle && mobileHandsFreeToggle.checked);
        if (isHandsFree) {
            console.log("Hands-free mode active, restarting microphone...");
            if (isVoiceModeActive) {
                updateVoiceModalUI('ready', "Listening for your response...");
            }
            setTimeout(() => {
                if (!isRecording) {
                    toggleVoiceInput();
                }
            }, 1000);
        } else if (isVoiceModeActive) {
            updateVoiceModalUI('ready');
        }
    };

    currentUtterance.onerror = (event) => {
        console.error("Speech error:", event.error);
        if (btn) resetButton(btn);
        currentUtterance = null;
    };

    if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
    }

    window.speechSynthesis.speak(currentUtterance);
}

// --- Voice Selection Logic ---

function populateVoiceList() {
    const voices = window.speechSynthesis.getVoices();
    const savedVoice = localStorage.getItem('selectedVoiceName');

    const updateDisplays = (name) => {
        if (currentVoiceNameDisplay) currentVoiceNameDisplay.textContent = name || 'Voice';
        if (mobileCurrentVoiceDisplay) mobileCurrentVoiceDisplay.textContent = name || 'AI Voice';
    };

    [
        { container: voiceSelectContainer, menu: voiceDropdownMenu, display: currentVoiceNameDisplay },
        { container: mobileVoiceOptionsContainer, menu: mobileVoiceDropdownMenu, display: mobileCurrentVoiceDisplay }
    ].forEach(({ container, menu, display }) => {
        if (!container) return;
        container.innerHTML = '';

        voices.forEach(voice => {
            const option = document.createElement('button');
            option.type = 'button';
            option.className = "w-full text-left px-4 py-2 text-[10px] font-bold text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/10 transition-colors uppercase tracking-tight";
            option.textContent = voice.name;

            if (savedVoice === voice.name) {
                option.classList.add('bg-blue-50/50', 'dark:bg-brand-900/20', 'text-brand-600', 'dark:text-brand-400');
                updateDisplays(voice.name);
            }

            option.onclick = () => {
                localStorage.setItem('selectedVoiceName', voice.name);
                updateDisplays(voice.name);
                if (menu) menu.classList.add('hidden');

                document.querySelectorAll('#voice-options-container button, #mobile-voice-options-container button').forEach(child => {
                    child.classList.remove('bg-blue-50/50', 'dark:bg-brand-900/20', 'text-brand-600', 'dark:text-brand-400');
                    if (child.textContent === voice.name) {
                        child.classList.add('bg-blue-50/50', 'dark:bg-brand-900/20', 'text-brand-600', 'dark:text-brand-400');
                    }
                });
            };
            container.appendChild(option);
        });
    });
}

function initVoiceSelect() {
    if (voiceDropdownBtn && voiceDropdownMenu) {
        voiceDropdownBtn.onclick = (e) => {
            e.stopPropagation();
            voiceDropdownMenu.classList.toggle('hidden');
            if (mobileVoiceDropdownMenu) mobileVoiceDropdownMenu.classList.add('hidden');
        };
    }

    if (mobileVoiceDropdownBtn && mobileVoiceDropdownMenu) {
        mobileVoiceDropdownBtn.onclick = (e) => {
            e.stopPropagation();
            mobileVoiceDropdownMenu.classList.toggle('hidden');
            if (voiceDropdownMenu) voiceDropdownMenu.classList.add('hidden');
        };
    }

    document.addEventListener('click', (e) => {
        if (voiceDropdownBtn && voiceDropdownMenu && !voiceDropdownBtn.contains(e.target) && !voiceDropdownMenu.contains(e.target)) {
            voiceDropdownMenu.classList.add('hidden');
        }
        if (mobileVoiceDropdownBtn && mobileVoiceDropdownMenu && !mobileVoiceDropdownBtn.contains(e.target) && !mobileVoiceDropdownMenu.contains(e.target)) {
            mobileVoiceDropdownMenu.classList.add('hidden');
        }
    });

    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = populateVoiceList;
    }

    populateVoiceList();
}

initVoiceSelect();

// --- Voice Input Logic ---

function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.error('Speech recognition not supported');
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isRecording = true;
        voicePulse?.classList.remove('hidden');
        voiceBtn?.classList.add('text-brand-600', 'dark:text-brand-400');
        if (isVoiceModeActive) {
            updateVoiceModalUI('listening');
        }
    };

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        userInput.value = transcript;

        if (isVoiceModeActive) {
            updateVoiceModalUI('listening', transcript);
        }

        if (silenceTimer) clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (userInput.value.trim() && isRecording) {
                if (autoSendToggle && autoSendToggle.checked) {
                    console.log("Silence detected, auto-sending...");
                    sendMessage();
                } else {
                    console.log("Silence detected, stopping recording...");
                    stopVoiceInput();
                    if (recognition) recognition.stop();
                }
            }
        }, 2000);
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        stopVoiceInput();
        if (event.error === 'not-allowed') {
            alert('Microphone permission denied. Please enable it in your browser settings.');
        }
    };

    recognition.onend = () => {
        stopVoiceInput();
    };
}

function toggleVoiceInput() {
    if (!recognition) initSpeechRecognition();
    if (!recognition) return;

    if (isRecording) {
        stopVoiceInput();
        recognition.stop();
    } else {
        userInput.value = '';
        recognition.start();
    }
}

function stopVoiceInput() {
    isRecording = false;
    voicePulse?.classList.add('hidden');
    voiceBtn?.classList.remove('text-brand-600', 'dark:text-brand-400');
    if (userInput) userInput.focus();
}

// --- Theme Logic ---

function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function initTheme() {
    const storedTheme = localStorage.getItem('color-theme');
    let themeToApply = storedTheme;

    if (!storedTheme || storedTheme === 'system') {
        themeToApply = getSystemTheme();
    }

    const html = document.documentElement;
    if (themeToApply === 'dark') {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
}

function toggleTheme() {
    const html = document.documentElement;
    let newTheme;

    if (html.classList.contains('dark')) {
        html.classList.remove('dark');
        newTheme = 'light';
    } else {
        html.classList.add('dark');
        newTheme = 'dark';
    }

    localStorage.setItem('color-theme', newTheme);
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const storedTheme = localStorage.getItem('color-theme');
    if (!storedTheme || storedTheme === 'system') {
        initTheme();
    }
});

initTheme();

// --- Auto-send Toggle Initialization ---

function initAutoSendToggle() {
    const savedState = localStorage.getItem('autoSendEnabled');
    const updateAll = (checked) => {
        if (autoSendToggle) autoSendToggle.checked = checked;
        if (mobileAutoSendToggle) mobileAutoSendToggle.checked = checked;
        localStorage.setItem('autoSendEnabled', checked);
    };

    if (savedState !== null) {
        updateAll(savedState === 'true');
    }

    autoSendToggle?.addEventListener('change', (e) => updateAll(e.target.checked));
    mobileAutoSendToggle?.addEventListener('change', (e) => updateAll(e.target.checked));
}

initAutoSendToggle();

// --- Auto-speak Toggle Initialization ---

function initAutoSpeakToggle() {
    const savedState = localStorage.getItem('autoSpeakEnabled');
    const updateAll = (checked) => {
        if (autoSpeakToggle) autoSpeakToggle.checked = checked;
        if (mobileAutoSpeakToggle) mobileAutoSpeakToggle.checked = checked;
        localStorage.setItem('autoSpeakEnabled', checked);
    };

    if (savedState !== null) {
        updateAll(savedState === 'true');
    }

    autoSpeakToggle?.addEventListener('change', (e) => updateAll(e.target.checked));
    mobileAutoSpeakToggle?.addEventListener('change', (e) => updateAll(e.target.checked));
}

initAutoSpeakToggle();

// --- Hands-Free Mode Toggle Initialization ---

function initHandsFreeToggle() {
    const savedState = localStorage.getItem('handsFreeEnabled');
    const updateAll = (checked) => {
        if (handsFreeToggle) handsFreeToggle.checked = checked;
        if (mobileHandsFreeToggle) mobileHandsFreeToggle.checked = checked;
        localStorage.setItem('handsFreeEnabled', checked);
    };

    if (savedState !== null) {
        updateAll(savedState === 'true');
    }

    handsFreeToggle?.addEventListener('change', (e) => updateAll(e.target.checked));
    mobileHandsFreeToggle?.addEventListener('change', (e) => updateAll(e.target.checked));
}

initHandsFreeToggle();

// --- Sidebar Toggle Logic ---

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

function toggleMobileSidebarOptions() {
    const optionsContainer = document.getElementById('sidebar-mobile-options');
    const icon = document.getElementById('mobile-sidebar-options-icon');

    if (optionsContainer) {
        if (optionsContainer.classList.contains('hidden')) {
            optionsContainer.classList.remove('hidden');
            if (icon) icon.classList.add('rotate-180');
        } else {
            optionsContainer.classList.add('hidden');
            if (icon) icon.classList.remove('rotate-180');
        }
    }
}

// --- Sidebar & Thread Logic ---

function getTimeGroup(dateString) {
    const date = new Date(dateString);
    const now = new Date();

    if (date.toDateString() === now.toDateString()) {
        return 'Today';
    }

    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 7) return 'This Week';
    return 'Older';
}

async function loadThreads() {
    try {
        const response = await fetch('/threads?specialist=pharmacy');
        const threads = await response.json();

        const conversationsContainer = document.getElementById('conversations-list');
        if (!conversationsContainer) return;

        conversationsContainer.innerHTML = '';

        if (threads.length === 0) {
            conversationsContainer.innerHTML = `
                <div class="text-center text-gray-400 dark:text-gray-500 text-xs mt-8 italic">
                    No conversations yet
                </div>
            `;
            return;
        }

        const grouped = {};
        threads.forEach(thread => {
            const group = getTimeGroup(thread.date);
            if (!grouped[group]) grouped[group] = [];
            grouped[group].push(thread);
        });

        const groupOrder = ['Today', 'This Week', 'Older'];

        groupOrder.forEach(groupName => {
            if (!grouped[groupName]) return;

            const header = document.createElement('div');
            header.className = 'px-2 py-2 mt-4 first:mt-0 text-xs font-semibold text-gray-500 dark:text-gray-400 group-header sidebar-text';
            header.textContent = groupName;
            conversationsContainer.appendChild(header);

            grouped[groupName].forEach(thread => {
                const container = document.createElement('div');
                container.className = 'relative group/item mb-1';

                const btn = document.createElement('button');
                btn.className = `w-full px-3 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-left transition-colors conversation-item ${thread.thread_id === currentThreadId ? 'active bg-gray-100 dark:bg-gray-800' : ''}`;

                btn.innerHTML = `
                    <div class="flex items-center gap-3">
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate pr-6 conversation-text">
                                ${escapeHtml(thread.title)}
                            </div>
                        </div>
                    </div>
                `;

                btn.onclick = () => loadHistory(thread.thread_id);
                container.appendChild(btn);
                conversationsContainer.appendChild(container);
            });
        });

        if (isSidebarCollapsed) {
            document.querySelectorAll('.conversation-text, .group-header, .sidebar-text').forEach(el => {
                el.style.display = 'none';
            });
        }

    } catch (e) {
        console.error("Failed to load threads", e);
        const conversationsContainer = document.getElementById('conversations-list');
        if (conversationsContainer) {
            conversationsContainer.innerHTML = `
                <div class="text-center text-red-400 dark:text-red-500 text-xs mt-8">
                    Failed to load conversations
                </div>
            `;
        }
    }
}

async function loadHistory(threadId) {
    currentThreadId = threadId;

    if (chatMessagesArea) chatMessagesArea.innerHTML = ''; else chatContainer.innerHTML = '';

    try {
        const response = await fetch(`/history/${threadId}?specialist=pharmacy`);
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                if (msg.role === 'ai' && (!msg.content || msg.content.trim() === '')) {
                    return;
                }
                appendMessage(msg.role, msg.content, false, msg.index);
            });
        } else {
            showWelcomeMessage();
        }

        loadThreads();

        const hasMedia = data.messages && data.messages.some(msg => {
            if (typeof msg.content === 'object' && msg.content && msg.content.image) return true;
            if (typeof msg.content === 'string' && isHtmlReport(msg.content)) return true;
            return false;
        });
        const mediaVaultBtn = document.getElementById('media-vault-trigger');
        if (mediaVaultBtn) {
            if (hasMedia) mediaVaultBtn.classList.remove('hidden');
            else mediaVaultBtn.classList.add('hidden');
        }

        if (window.innerWidth < 768) {
            if (!sidebar.classList.contains('-translate-x-full')) {
                toggleSidebarMobile();
            }
        }
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'instant' });
    } catch (e) {
        console.error("Failed to load history", e);
        const errorHtml = '<div class="text-center text-gray-400 mt-10">Failed to load conversation history.</div>';
        if (chatMessagesArea) chatMessagesArea.innerHTML = errorHtml; else chatContainer.innerHTML = errorHtml;
    }
}

function startNewChat() {
    currentThreadId = generateUUID();
    showWelcomeMessage();
    loadThreads();
    if (window.innerWidth < 768 && !sidebar.classList.contains('-translate-x-full')) {
        toggleSidebarMobile();
    }
}

if (newChatBtn) newChatBtn.onclick = startNewChat;

async function initApp() {
    await loadThreads();
    startNewChat();
}

initApp();

// --- Logs Toggle ---

function openLogs() {
    if (!logsPanel) return;
    const logsToggleBtn = document.getElementById('logs-toggle-btn');

    logsPanel.classList.remove('hidden');
    logsPanel.offsetHeight;

    logsPanel.classList.remove('translate-x-full', 'opacity-0', 'md:w-0');
    logsPanel.classList.add('translate-x-0', 'opacity-100', 'md:w-80');

    if (logsToggleBtn) {
        logsToggleBtn.classList.add('opacity-0', 'pointer-events-none', 'scale-95');
    }
}

function closeLogs() {
    if (!logsPanel) return;
    const logsToggleBtn = document.getElementById('logs-toggle-btn');

    logsPanel.classList.add('translate-x-full', 'opacity-0', 'md:w-0');
    logsPanel.classList.remove('translate-x-0', 'opacity-100', 'md:w-80');

    if (logsToggleBtn) {
        logsToggleBtn.classList.remove('opacity-0', 'pointer-events-none', 'scale-95');
    }

    setTimeout(() => {
        if (logsPanel.classList.contains('translate-x-full')) {
            logsPanel.classList.add('hidden');
        }
    }, 300);
}

function toggleLogs() {
    if (!logsPanel) return;
    const isHidden = logsPanel.classList.contains('hidden') || logsPanel.classList.contains('md:w-0');
    if (isHidden) {
        openLogs();
    } else {
        closeLogs();
    }
}

// --- Chat Functions ---

function showTypingIndicator() {
    const div = document.createElement('div');
    div.id = 'typing-indicator';
    div.className = 'flex w-full justify-start mb-8';

    const bubbleWrapper = document.createElement('div');
    bubbleWrapper.className = 'message-bubble';

    let headerHtml = `
        <div class="flex items-center gap-2 mb-1 pl-1">
             <span class="text-xs font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-indigo-600 dark:from-brand-400 dark:to-purple-400 uppercase tracking-wider">Dr. Pharma</span>
             <span class="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium">Pharmacist</span>
        </div>
    `;

    const bubble = document.createElement('div');
    bubble.className = "border border-gray-100 dark:border-gray-700/50 shadow-sm rounded-2xl rounded-tl-sm p-4 text-gray-800 dark:text-gray-200";
    bubble.innerHTML = `
        <div class="flex gap-4 w-full">
           <div class="shrink-0 flex flex-col items-center">
                <img src="/static/images/1.png" alt="Dr. Pharma" class="w-10 h-10 rounded-full object-cover ring-2 ring-white dark:ring-gray-900 shadow-md">
            </div>
            <div class="flex-1 space-y-3 pt-2">
                <div class="skeleton-loader skeleton-line w-[80%]"></div>
                <div class="skeleton-loader skeleton-line w-[60%]"></div>
                <div class="skeleton-loader skeleton-line w-[40%]"></div>
            </div>
        </div>
    `;

    bubbleWrapper.innerHTML = headerHtml;
    bubbleWrapper.appendChild(bubble);
    div.appendChild(bubbleWrapper);

    if (chatMessagesArea) {
        chatMessagesArea.appendChild(div);
    } else {
        chatContainer.appendChild(div);
    }

    scrollToBottom();

    const typingSound = document.getElementById('typing-sound');
    if (typingSound) {
        typingSound.volume = 0.15;
        typingSound.currentTime = 0;
        const playPromise = typingSound.play();
        if (playPromise !== undefined) {
            playPromise.catch(e => {
                console.log('Typing sound not available:', e.message);
            });
        }
    }

    return div;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }

    const typingSound = document.getElementById('typing-sound');
    if (typingSound) {
        typingSound.pause();
        typingSound.currentTime = 0;
    }
}

async function downloadReport(reportId) {
    const reportElement = document.getElementById(reportId);
    if (!reportElement) {
        console.error("Report element not found:", reportId);
        return;
    }

    // Create temporary wrapper for cloning
    const wrapper = document.createElement('div');
    wrapper.style.position = 'absolute';
    wrapper.style.left = '-9999px';
    wrapper.style.top = '0';
    document.body.appendChild(wrapper);

    // Clone node
    const clone = reportElement.cloneNode(true);
    // Ensure the clone is visible and has neutral transform
    clone.style.transform = 'none';

    wrapper.appendChild(clone);

    const btn = document.querySelector(`button[onclick="downloadReport('${reportId}')"]`);
    const originalContent = btn ? btn.innerHTML : '';
    if (btn) {
        btn.innerHTML = '<i class="fa-light fa-spinner-third animate-spin"></i> Generating...';
        btn.disabled = true;
    }

    try {
        if (typeof html2canvas === 'undefined') {
            // Attempt to load html2canvas dynamically if missing
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }

        // Layout Settlement Delay: Give the browser time to render the off-screen clone
        await new Promise(r => setTimeout(r, 500));

        const canvas = await html2canvas(clone, {
            scale: 2,
            useCORS: true,
            allowTaint: true,
            backgroundColor: document.documentElement.classList.contains('dark') ? '#0b0f1a' : '#ffffff',
            windowWidth: 1200,
            onclone: (clonedDoc) => {
                const element = clonedDoc.getElementById(reportId);
                if (element) {
                    element.style.transform = 'none';
                    element.style.width = '1200px';
                    element.style.display = 'flex';
                }
            }
        });

        const link = document.createElement('a');
        link.download = `Pharmacy_Report_Dr_Pharma_${new Date().toISOString().split('T')[0]}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();

    } catch (error) {
        console.error("Report download failed:", error);
        alert("Failed to download report. See console for details.");
    } finally {
        document.body.removeChild(wrapper);
        if (btn) {
            btn.innerHTML = originalContent;
            btn.disabled = false;
        }
    }
}

function isHtmlReport(text) {
    if (typeof text !== 'string') return false;
    return text.includes('clip-path-header') || text.includes('medical-report') || text.includes('report-container');
}

function appendMessage(role, content, animate = true, index = null) {
    if (role === 'ai' && (content === undefined || content === null)) {
        return null;
    }
    const div = document.createElement('div');
    const isUser = role === 'user';
    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    div.className = `flex w-full ${isUser ? 'justify-end items-end gap-3' : 'justify-start'} mb-8 group`;
    if (index !== null) div.setAttribute('data-index', index);

    const bubbleWrapper = document.createElement('div');
    bubbleWrapper.className = `message-bubble ${isUser ? 'max-w-[70%]' : 'w-full'}`;

    const headerHtml = isUser ? '' : `
        <div class="flex items-center gap-2 mb-1 pl-1">
             <span class="text-xs font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 to-teal-600 dark:from-emerald-400 dark:to-teal-400 uppercase tracking-wider">Dr. Pharma</span>
             <span class="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium">Pharmacist</span>
        </div>
    `;

    const bubble = document.createElement('div');
    bubble.className = isUser
        ? "px-4 py-2.5 text-white text-base font-normal leading-relaxed tracking-gemini rounded-2xl rounded-br-sm bg-gradient-to-br from-emerald-500 to-teal-600 dark:from-emerald-600 dark:to-teal-700 shadow-md translate-y-[-10px]"
        : "p-4 text-[#3c4043] dark:text-gray-200 text-base font-normal leading-relaxed tracking-gemini";

    let renderedContent;
    let messageImage = null;
    if (isUser) {
        const messageText = typeof content === 'string' ? content : (content.text || '');
        messageImage = typeof content === 'object' ? content.image : null;
        renderedContent = `<div class="message-text w-full break-words text-justify">${messageText}</div>`;
    } else {
        if (isHtmlReport(content)) {
            renderedContent = `<div class="w-full overflow-x-auto">${content}</div>`;
        } else {
            renderedContent = marked.parse(content).replace(/\<table\>/g, '\<div class="table-wrapper"\>\<table\>').replace(/\<\/table\>/g, '\<\/table\>\<\/div\>');
        }
    }

    if (isUser) {
        const messageText = typeof content === 'string' ? content : (content.text || '');
        bubble.innerHTML = `
            ${renderedContent}
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
        avatar.className = "w-10 h-10 rounded-full bg-brand-600 flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm ring-2 ring-brand-100 dark:ring-brand-900/30 overflow-hidden mb-1";
        avatar.innerHTML = window.currentProfilePic ? `<img src="${window.currentProfilePic}" class="w-full h-full object-cover">` : (window.currentUser || 'P')[0].toUpperCase();

        if (messageText.trim().length > 0) {
            bubbleWrapper.appendChild(bubble);
        } else if (!messageImage) {
            bubbleWrapper.appendChild(bubble);
        }

        div.appendChild(bubbleWrapper);
        div.appendChild(avatar);
    } else {
        bubble.innerHTML = `
            <div class="flex items-start gap-4">
                <div class="shrink-0 flex flex-col items-center">
                    <img src="/static/images/2.png" alt="Dr. Pharma" class="w-10 h-10 rounded-full object-cover ring-2 ring-white dark:ring-gray-900 shadow-md">
                </div>
                <div class="flex-1 min-w-0">
                    <div class="prose prose-invert max-w-none message-content leading-relaxed text-base text-gray-700 dark:text-gray-300">
                        ${renderedContent} 
                    </div>
                    <div class="flex justify-between items-center mt-2">
                        <div class="flex gap-2">
                            <button class="speak-btn p-1 text-gray-400 hover:text-brand-600 transition-colors" title="Speak Text">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.287a6 6 0 0 1 0 7.427M12 18.75V5.25A2.25 2.25 0 0 0 9.75 3H7.5a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h2.25a2.25 2.25 0 0 0 2.25-2.25Z" />
                                </svg>
                            </button>
                        </div>
                        <span class="text-[10px] text-gray-400 dark:text-gray-500">${timeString}</span>
                    </div>
                </div>
            </div>
        `;
        bubbleWrapper.innerHTML = headerHtml;
        bubbleWrapper.appendChild(bubble);
        div.appendChild(bubbleWrapper);
    }

    if (chatMessagesArea) {
        chatMessagesArea.appendChild(div);
    } else {
        chatContainer.appendChild(div);
    }

    if (chatContainer && chatContainer.classList.contains('no-scrollbar')) {
        chatContainer.classList.remove('no-scrollbar');
    }
    if (animate) {
        scrollToBottom();
    }

    if (!isUser) {
        const speakBtn = bubble.querySelector('.speak-btn');
        if (speakBtn) {
            speakBtn.onclick = (e) => {
                e.stopPropagation();
                const textToSpeak = bubble.querySelector('.message-content').innerText;
                speakText(textToSpeak, speakBtn);
            };
        }
        return div.querySelector('.message-content');
    }
}

// --- Stop Response ---

function stopResponse() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    if (stopBtn) {
        stopBtn.classList.add('hidden', 'scale-0', 'opacity-0');
        stopBtn.classList.remove('flex', 'scale-100', 'opacity-100');
    }
    removeTypingIndicator();
}

// --- Send Message ---

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message && !selectedImage) return;

    if (!currentThreadId) currentThreadId = generateUUID();

    const welcomeMsg = document.getElementById('welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    userInput.value = '';
    if (window.resetInputHeight) resetInputHeight();

    if (sendBtn) {
        sendBtn.classList.remove('scale-100', 'opacity-100');
        sendBtn.classList.add('scale-0', 'opacity-0');
        const voiceModeInputBtn = document.getElementById('voice-mode-trigger-input');
        if (voiceModeInputBtn) voiceModeInputBtn.classList.remove('hidden');
    }

    const imageFileForMessage = selectedImage;
    let imageDataUrl = null;
    if (imageFileForMessage) {
        const r = new FileReader();
        imageDataUrl = await new Promise(res => {
            r.onload = e => res(e.target.result);
            r.readAsDataURL(imageFileForMessage);
        });
    }

    const userContent = imageDataUrl ? { text: message, image: imageDataUrl } : message;
    appendMessage('user', userContent, true);

    if (selectedImage) {
        const mediaVaultBtn = document.getElementById('media-vault-trigger');
        if (mediaVaultBtn) mediaVaultBtn.classList.remove('hidden');
    }

    const formData = new FormData();
    formData.append('message', message);
    formData.append('thread_id', currentThreadId);
    formData.append('specialist', 'pharmacy');
    if (selectedImage) {
        formData.append('image', selectedImage);
        clearImage();
    }

    showTypingIndicator();

    abortController = new AbortController();

    if (stopBtn) {
        stopBtn.classList.remove('hidden', 'scale-0', 'opacity-0');
        stopBtn.classList.add('flex', 'scale-100', 'opacity-100');
    }

    if (isVoiceModeActive) {
        updateVoiceModalUI('thinking');
    }

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        const headers = {};
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;

        const response = await fetch('/chat', {
            method: 'POST',
            headers: headers,
            body: formData,
            signal: abortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiMessageContentEl = null;
        let aiContent = "";
        let buffer = "";

        removeTypingIndicator();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));

                        if (data.type === 'token') {
                            if (!aiMessageContentEl) {
                                aiMessageContentEl = appendMessage('ai', '', true);
                            }
                            aiContent += data.content;
                            if (aiMessageContentEl) {
                                if (isHtmlReport(aiContent)) {
                                    aiMessageContentEl.innerHTML = `<div class="w-full overflow-x-auto">${aiContent}</div>`;
                                } else {
                                    aiMessageContentEl.innerHTML = marked.parse(aiContent).replace(/\<table\>/g, '\<div class="table-wrapper"\>\<table\>').replace(/\<\/table\>/g, '\<\/table\>\<\/div\>');
                                }
                                scrollToBottom();
                            }
                            if (isHtmlReport(aiContent)) {
                                const mb = document.getElementById('media-vault-trigger');
                                if (mb) mb.classList.remove('hidden');
                            }
                        } else if (data.type === 'tool_start') {
                            appendLog('tool_start', data);
                        } else if (data.type === 'tool_end') {
                            appendLog('tool_end', data);
                        } else if (data.type === 'error') {
                            removeTypingIndicator();
                            appendMessage('ai', `⚠️ ${data.content || 'An error occurred. Please try again.'}`);
                        }
                    } catch (e) {
                        console.error("Error parsing SSE chunk:", e);
                    }
                }
            }
        }

        // Auto-speak
        if (aiContent) {
            const isAutoSpeak = (autoSpeakToggle && autoSpeakToggle.checked) || (mobileAutoSpeakToggle && mobileAutoSpeakToggle.checked);
            if (isAutoSpeak) {
                const speakBtns = document.querySelectorAll('.speak-btn');
                const lastSpeakBtn = speakBtns[speakBtns.length - 1];
                speakText(aiContent, lastSpeakBtn);
            }
        }

        loadThreads();

    } catch (e) {
        if (e.name === 'AbortError') {
            console.log('Fetch aborted by user.');
        } else {
            console.error("Chat error:", e);
            removeTypingIndicator();
            appendMessage('ai', "⚠️ I encountered an error. Please try again or check your connection.");
        }
    } finally {
        abortController = null;
        if (stopBtn) {
            stopBtn.classList.add('hidden', 'scale-0', 'opacity-0');
            stopBtn.classList.remove('flex', 'scale-100', 'opacity-100');
        }
        if (isVoiceModeActive && !window.speechSynthesis.speaking) {
            updateVoiceModalUI('ready');
        }
    }
}

// --- Data Formatting Helper ---

function formatDataForDisplay(data) {
    if (!data) return '<span class="text-gray-400 italic">None</span>';

    if (typeof data === 'string') {
        try {
            const parsed = JSON.parse(data);
            if (typeof parsed === 'object') return formatDataForDisplay(parsed);
        } catch (e) { }
        return `<div class="text-gray-700 dark:text-gray-300 break-words whitespace-pre-wrap font-sans text-[10px]">${data}</div>`;
    }

    if (Array.isArray(data)) {
        if (data.length === 0) return '<span class="text-gray-400 italic">Empty List</span>';
        return `
            <div class="flex flex-col gap-1.5">
                ${data.map((item, index) => `
                    <div class="pl-2 border-l border-gray-200 dark:border-gray-700">
                        <div class="text-[8px] text-gray-400 font-bold mb-0.5">ITEM ${index + 1}</div>
                        ${formatDataForDisplay(item)}
                    </div>
                `).join('')}
            </div>
        `;
    }

    if (typeof data === 'object') {
        const keys = Object.keys(data);
        if (keys.length === 0) return '<span class="text-gray-400 italic">Empty Object</span>';

        return `
            <div class="grid grid-cols-1 gap-1.5">
                ${keys.map(key => `
                    <div class="group">
                        <div class="text-[8px] uppercase tracking-wider font-bold text-gray-400 mb-0.5 group-hover:text-brand-500 transition-colors">${key.replace(/_/g, ' ')}</div>
                        <div class="text-[10px] text-gray-800 dark:text-gray-200 break-words pl-1 border-l border-transparent group-hover:border-brand-500/30 transition-colors">
                            ${formatDataForDisplay(data[key])}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    return `<span class="text-gray-800 dark:text-gray-200 font-mono text-[10px]">${data}</span>`;
}

// --- Syntax Highlighting Helper ---
function syntaxHighlight(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/(\"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*\"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'syntax-number';
        if (/^\"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'syntax-key';
            } else {
                cls = 'syntax-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'syntax-boolean';
        } else if (/null/.test(match)) {
            cls = 'syntax-boolean';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

// --- Card Toggle Helper ---
function toggleCard(cardId) {
    const content = document.getElementById(`content-${cardId}`);
    const icon = document.getElementById(`icon-${cardId}`);

    if (content && icon) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.style.transform = 'rotate(180deg)';
        } else {
            content.style.display = 'none';
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

function appendLog(type, data) {
    if (!logsContainer) return;

    const emptyState = logsContainer.querySelector('.italic');
    if (emptyState) emptyState.remove();

    if (type === 'tool_start') {
        openLogs();
    }

    const sanitizeArgs = (args) => {
        const sanitized = JSON.parse(JSON.stringify(args));
        if (sanitized.image_path) {
            sanitized.image_path = "Image File: " + sanitized.image_path.split(/[\\\/]/).pop();
        }
        return sanitized;
    };

    if (type === 'tool_start') {
        const cardId = `tool-${data.tool_call_id || Date.now()}`;
        const div = document.createElement('div');
        div.id = cardId;
        div.className = "execution-card glass-card mb-4 w-full rounded-xl border p-4 active";

        const safeArgs = sanitizeArgs(data.args || {});
        const formattedInput = formatDataForDisplay(safeArgs);

        div.innerHTML = `
            <div class="flex items-center justify-between mb-3 cursor-pointer" onclick="toggleCard('${cardId}')">
                 <div class="flex items-center gap-2 min-w-0">
                     <span class="relative flex h-2 w-2 shrink-0">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
                     </span>
                     <span class="text-xs font-bold text-gray-800 dark:text-gray-100 tracking-tight truncate">${data.tool_name}</span>
                 </div>
                 <div class="flex items-center gap-2">
                    <div class="shrink-0 px-2 py-0.5 rounded text-[9px] font-bold bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 uppercase tracking-wider">
                        Running
                    </div>
                    <i id="icon-${cardId}" class="fa-solid fa-chevron-down text-gray-400 text-[8px] transition-transform duration-200" style="transform: rotate(180deg)"></i>
                 </div>
            </div>

            <div id="content-${cardId}" style="display: block;">
                <div class="flex items-center gap-1.5 mb-2 opacity-70">
                    <i class="fa-solid fa-brain-circuit text-[10px] text-purple-500"></i>
                    <span class="text-[8px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-widest truncate">Gemini Neural Engine</span>
                </div>

                <div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2 border border-gray-100 dark:border-gray-800/50">
                     <div class="text-[8px] text-gray-400 uppercase tracking-wider font-bold mb-1.5 pb-1 border-b border-gray-200 dark:border-gray-700/50">Input Payload</div>
                     <div class="overflow-hidden">
                        ${formattedInput}
                     </div>
                </div>
            </div>
        `;

        logsContainer.appendChild(div);

    } else if (type === 'tool_end') {
        const cardId = `tool-${data.tool_call_id}`;
        const card = document.getElementById(cardId);

        if (card) {
            const oldContent = document.getElementById(`content-${cardId}`);
            const wasHidden = oldContent && oldContent.style.display === 'none';

            card.classList.remove('active');
            card.classList.add('success');
            card.style.borderColor = '#10b981';

            let outputData = data.output;
            try {
                if (typeof data.output === 'string') {
                    outputData = JSON.parse(data.output);
                }
            } catch (e) { }

            const formattedOutput = formatDataForDisplay(outputData);
            const displayStyle = wasHidden ? 'none' : 'block';
            const rotateStyle = wasHidden ? 'rotate(0deg)' : 'rotate(180deg)';

            card.innerHTML = `
                <div class="flex items-center justify-between mb-3 cursor-pointer" onclick="toggleCard('${cardId}')">
                     <div class="flex items-center gap-2 min-w-0">
                         <div class="h-4 w-4 shrink-0 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                            <i class="fa-solid fa-check text-[8px] text-green-600 dark:text-green-400"></i>
                         </div>
                         <span class="text-xs font-bold text-gray-800 dark:text-gray-100 tracking-tight truncate">${data.tool_name}</span>
                     </div>
                     <div class="flex items-center gap-2">
                        <div class="shrink-0 px-2 py-0.5 rounded text-[9px] font-bold bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 uppercase tracking-wider">
                            Complete
                        </div>
                        <i id="icon-${cardId}" class="fa-solid fa-chevron-down text-gray-400 text-[8px] transition-transform duration-200" style="transform: ${rotateStyle}"></i>
                     </div>
                </div>

                <div id="content-${cardId}" style="display: ${displayStyle};">
                    <div class="flex items-center gap-1.5 mb-2">
                        <i class="fa-solid fa-shield-check text-[10px] text-green-500"></i>
                        <span class="text-[8px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest truncate">Data Verified</span>
                    </div>

                    <div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2 border border-gray-100 dark:border-gray-800/50 animate-fade-in group">
                         <div class="text-[8px] text-gray-400 uppercase tracking-wider font-bold mb-1.5 pb-1 border-b border-gray-200 dark:border-gray-700/50 flex justify-between items-center">
                            <span>Output Payload</span>
                         </div>
                         <div class="overflow-y-auto max-h-60 custom-scrollbar pr-1">
                            ${formattedOutput}
                         </div>
                    </div>
                </div>
            `;
        }
    } else if (type === 'error') {
        const div = document.createElement('div');
        div.className = "execution-card glass-card mb-4 w-full rounded-xl border p-4 error";
        div.innerHTML = `
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-triangle-exclamation text-red-500"></i>
                <span class="text-sm font-bold text-red-600 dark:text-red-400">Error</span>
            </div>
            <p class="text-xs text-gray-600 dark:text-gray-400 mt-2">${data.message || 'An error occurred'}</p>
        `;
        logsContainer.appendChild(div);
    }
}

// --- Media Vault Logic ---

async function openMediaVault(threadId) {
    const vaultPanel = document.getElementById('media-vault-panel');
    const vaultGrid = document.getElementById('media-vault-grid');
    const vaultEmpty = document.getElementById('media-vault-empty');

    if (!vaultPanel || !threadId) return;

    if (window.innerWidth < 768 && sidebar && !sidebar.classList.contains('-translate-x-full')) {
        toggleSidebarMobile();
    }

    sidebarWasCollapsedBeforeVault = isSidebarCollapsed;
    if (!isSidebarCollapsed && window.innerWidth >= 768) {
        toggleSidebar();
    }

    vaultPanel.classList.remove('hidden');
    vaultGrid.innerHTML = '';
    currentMediaItems = [];
    currentMediaIndex = -1;

    try {
        const response = await fetch(`/history/${threadId}?specialist=pharmacy`);
        const data = await response.json();

        const mediaMessages = (data.messages || []).filter(msg => {
            if (typeof msg.content === 'object' && msg.content && msg.content.image) return true;
            if (typeof msg.content === 'string' && isHtmlReport(msg.content)) return true;
            return false;
        });

        if (mediaMessages.length === 0) {
            vaultEmpty.classList.remove('hidden');
            return;
        }

        vaultEmpty.classList.add('hidden');

        mediaMessages.forEach((msg, idx) => {
            const isImage = typeof msg.content === 'object' && msg.content.image;
            const isReport = typeof msg.content === 'string' && isHtmlReport(msg.content);

            const item = { type: isImage ? 'image' : 'report', content: isImage ? msg.content.image : msg.content, date: msg.date || 'Unknown date' };
            currentMediaItems.push(item);

            const card = document.createElement('div');
            card.className = "relative rounded-xl overflow-hidden cursor-pointer group border border-gray-100 dark:border-gray-800 hover:border-brand-300 dark:hover:border-brand-700 transition-all shadow-sm hover:shadow-md";
            card.onclick = () => openLightbox(idx);

            if (isImage) {
                card.innerHTML = `
                    <img src="${msg.content.image}" alt="Consultation image" class="w-full h-32 object-cover group-hover:scale-105 transition-transform duration-300">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                        <span class="text-white text-[9px] font-bold uppercase tracking-wider">View</span>
                    </div>
                `;
            } else {
                card.innerHTML = `
                    <div class="w-full h-32 bg-gradient-to-br from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 flex flex-col items-center justify-center gap-2">
                        <i class="fa-solid fa-file-medical text-3xl text-brand-400 dark:text-brand-500"></i>
                        <span class="text-[10px] font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wider">Report</span>
                    </div>
                `;
            }

            vaultGrid.appendChild(card);
        });

    } catch (e) {
        console.error("Failed to load media vault:", e);
        vaultGrid.innerHTML = '<p class="text-xs text-red-400 col-span-2 text-center mt-4">Failed to load media.</p>';
    }
}

function toggleMediaVault() {
    const vaultPanel = document.getElementById('media-vault-panel');
    if (vaultPanel) {
        vaultPanel.classList.add('hidden');
        if (sidebarWasCollapsedBeforeVault === false && isSidebarCollapsed) {
            toggleSidebar();
        }
    }
}

// --- Lightbox Logic ---

function openLightbox(index) {
    const lightbox = document.getElementById('media-lightbox');
    if (!lightbox || !currentMediaItems.length) return;

    currentMediaIndex = index;
    renderLightboxItem(index);
    lightbox.classList.remove('hidden');

    sidebarWasCollapsedBeforeLightbox = isSidebarCollapsed;
    const vaultPanel = document.getElementById('media-vault-panel');
    if (vaultPanel && !vaultPanel.classList.contains('hidden')) {
        toggleMediaVault();
    }

    if (sidebar) sidebar.style.display = 'none';

    document.addEventListener('keydown', handleLightboxKeydown);
}

function renderLightboxItem(index) {
    const item = currentMediaItems[index];
    if (!item) return;

    const content = document.getElementById('lightbox-content');
    const typeLabel = document.getElementById('lightbox-type');
    const dateLabel = document.getElementById('lightbox-date');
    const downloadBtn = document.getElementById('download-media-btn');

    if (typeLabel) typeLabel.textContent = item.type === 'image' ? 'IMAGE' : 'REPORT';
    if (dateLabel) dateLabel.textContent = item.date ? new Date(item.date).toLocaleString() : 'Consultation Item';

    if (content) {
        if (item.type === 'image') {
            content.innerHTML = `<img src="${item.content}" alt="Media" class="max-w-full max-h-[80vh] object-contain rounded-xl shadow-2xl">`;
            if (downloadBtn) {
                downloadBtn.onclick = () => {
                    const a = document.createElement('a');
                    a.href = item.content;
                    a.download = `pharmacy_consultation_${Date.now()}.png`;
                    a.click();
                };
            }
        } else {
            const reportId = `lightbox-report-${Date.now()}`;
            content.innerHTML = `<div id="${reportId}" class="max-w-full max-h-[80vh] overflow-y-auto rounded-xl">${item.content}</div>`;
            if (downloadBtn) {
                downloadBtn.onclick = () => downloadReport(reportId);
            }
        }
    }
}

function navigateLightbox(direction) {
    const newIndex = currentMediaIndex + direction;
    if (newIndex >= 0 && newIndex < currentMediaItems.length) {
        currentMediaIndex = newIndex;
        renderLightboxItem(currentMediaIndex);
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('media-lightbox');
    if (lightbox) {
        lightbox.classList.add('hidden');
    }

    if (sidebar) sidebar.style.display = '';

    document.removeEventListener('keydown', handleLightboxKeydown);
}

function handleLightboxKeydown(e) {
    if (e.key === 'ArrowLeft') navigateLightbox(-1);
    if (e.key === 'ArrowRight') navigateLightbox(1);
    if (e.key === 'Escape') closeLightbox();
}

// Close lightbox on backdrop click
document.getElementById('media-lightbox')?.addEventListener('click', function (e) {
    if (e.target === this) closeLightbox();
});
