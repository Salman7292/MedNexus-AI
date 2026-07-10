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
const sendBtnMobile = document.getElementById('send-btn-mobile');
const voiceBtnMobile = document.getElementById('voice-btn-mobile');
const voicePulseMobile = document.getElementById('voice-pulse-mobile');
const stopBtnMobile = document.getElementById('stop-btn-mobile');
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

// Mobile Specific Elements
const mobileAutoSendToggle = document.getElementById('mobile-auto-send-toggle');
const mobileAutoSpeakToggle = document.getElementById('mobile-auto-speak-toggle');
const mobileVoiceDropdownBtn = document.getElementById('mobile-voice-dropdown-btn');
const mobileVoiceDropdownMenu = document.getElementById('mobile-voice-dropdown-menu');
const mobileVoiceOptionsContainer = document.getElementById('mobile-voice-options-container');
const mobileCurrentVoiceDisplay = document.getElementById('mobile-current-voice-name');

// Auto-expand textarea
userInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if (this.value.trim() === '') {
        this.style.height = '48px'; // min-height
    }
});

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
            // Re-populate voice list on open
            populateVoiceList();

            // Re-sync switch states on open
            if (autoSendToggle) {
                const savedAutoSend = localStorage.getItem('autoSendEnabled');
                if (savedAutoSend !== null) {
                    autoSendToggle.checked = savedAutoSend === 'true';
                    if (mobileAutoSendToggle) mobileAutoSendToggle.checked = autoSendToggle.checked;
                }
            }
            if (autoSpeakToggle) {
                const savedAutoSpeak = localStorage.getItem('autoSpeakEnabled');
                if (savedAutoSpeak !== null) {
                    autoSpeakToggle.checked = savedAutoSpeak === 'true';
                    if (mobileAutoSpeakToggle) mobileAutoSpeakToggle.checked = autoSpeakToggle.checked;
                }
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
let currentUtterance = null; // Global reference to prevent garbage collection
let abortController = null;
let currentMediaItems = [];
let currentMediaIndex = -1;
let isVoiceModeActive = false;

// Typing Animation Helper
function typeText(element, text, speed = 30, callback) {
    element.innerHTML = ""; // Clear existing text
    let i = 0;

    // Create cursor element
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
            // Typing finished
            cursor.remove(); // Remove cursor at end
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
    document.body.style.overflow = 'hidden'; // Prevent scrolling

    // Close mobile sidebar if open
    if (window.innerWidth < 1024 && sidebar && !sidebar.classList.contains('-translate-x-full')) {
        toggleSidebarMobile();
    }

    // Auto-enable necessary voice settings
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

    // Modal Image Preview Sync
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

    // Start listening immediately
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
    document.body.style.overflow = ''; // Restore scrolling
    if (userInput) userInput.disabled = false; // Force re-enable input when closing modal

    // Stop recording if active
    if (isRecording) {
        toggleVoiceInput();
    }

    // Stop speech if active
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }

    // Auto-disable voice settings
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

    // Explicitly focus chat input after modal closes
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
            // Show stop button while thinking/speaking
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

// --- Scrolling Navigation ---
function scrollToBottom() {
    if (!chatContainer) return;
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

// Scroll handler to show/hide the scroll-to-bottom button
if (chatContainer) {
    chatContainer.addEventListener('scroll', () => {
        const threshold = 300; // Pixels from bottom to show button
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
            <img src="/static/images/phys.gif" alt="AI Doctor Logo" class="w-32 h-32 object-contain rounded-full shadow-lg dark:shadow-none bg-white dark:bg-transparent p-1 animate-fade-in">
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

    // Animate Title then Subtitle
    typeText(titleEl, "Hello, I'm Dr. Aria.", 40, () => {
        typeText(subtitleEl, "How can I help you regarding your mental health today?", 20);
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
        event.target.value = ''; // Reset the input
        return;
    }

    const file = files[0];
    const allowedExtensions = ['png', 'jpg', 'jpeg', 'gif', 'jfif', 'webp', 'bmp', 'tiff', 'tif', 'heic', 'svg', 'ico', 'avif'];
    const fileExtension = file.name.split('.').pop().toLowerCase();

    if (!allowedExtensions.includes(fileExtension)) {
        alert('Invalid file type. Please upload a valid image file (PNG, JPG, HEIC, WebP, etc.).');
        event.target.value = ''; // Reset
        return;
    }

    selectedImage = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
        imagePreview.src = e.target.result;
        imageName.textContent = file.name;
        imageSize.textContent = formatBytes(file.size);
        imagePreviewContainer.classList.remove('hidden');

        const spinner = document.getElementById('image-upload-spinner');
        const clearBtn = document.getElementById('clear-image-btn');

        // Prepare loading state
        imagePreview.classList.add('opacity-50');
        if (spinner) spinner.classList.remove('hidden');
        if (clearBtn) clearBtn.classList.add('hidden');

        if (sendBtn) sendBtn.disabled = true;
        if (sendBtnMobile) sendBtnMobile.disabled = true;

        // Simulate upload delay (e.g., 800ms) to show spinner
        setTimeout(() => {
            if (!selectedImage) return; // Bail if user cleared image during upload

            imagePreview.classList.remove('opacity-50');
            if (spinner) spinner.classList.add('hidden');
            if (clearBtn) clearBtn.classList.remove('hidden');

            // Enable send buttons after processing is complete
            if (sendBtn) {
                sendBtn.classList.remove('scale-0', 'opacity-0');
                sendBtn.classList.add('scale-100', 'opacity-100');
                sendBtn.disabled = false;
            }
            if (sendBtnMobile) {
                sendBtnMobile.classList.remove('scale-0', 'opacity-0');
                sendBtnMobile.classList.add('scale-100', 'opacity-100');
                sendBtnMobile.disabled = false;
            }
        }, 800);
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    selectedImage = null;
    imageInput.value = '';
    imagePreviewContainer.classList.add('hidden');
    imagePreview.src = '';

    // Reset loader states for the next upload
    imagePreview.classList.add('opacity-50');
    const spinner = document.getElementById('image-upload-spinner');
    if (spinner) spinner.classList.remove('hidden');
    const clearBtn = document.getElementById('clear-image-btn');
    if (clearBtn) clearBtn.classList.add('hidden');

    // Check if send button should be hidden (no text and no image)
    if (!userInput.value.trim().length > 0) {
        if (sendBtn) {
            sendBtn.classList.remove('scale-100', 'opacity-100');
            sendBtn.classList.add('scale-0', 'opacity-0');
            sendBtn.disabled = true;
        }
        if (sendBtnMobile) {
            sendBtnMobile.classList.remove('scale-100', 'opacity-100');
            sendBtnMobile.classList.add('scale-0', 'opacity-0');
            sendBtnMobile.disabled = true;
        }
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

// Consistently use the later speakText definition

// --- Voice Input Logic ---

function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.error('Speech recognition not supported');
        voiceBtn.style.display = 'none';
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isRecording = true;
        if (voicePulse) voicePulse.classList.remove('hidden');
        if (voiceBtn) voiceBtn.classList.add('text-brand-600', 'dark:text-brand-400');
        if (voicePulseMobile) voicePulseMobile.classList.remove('hidden');
        if (voiceBtnMobile) voiceBtnMobile.classList.add('text-brand-600', 'dark:text-brand-400', 'bg-brand-50', 'dark:bg-brand-900/30');
    };

    recognition.onresult = (event) => {
        let transcript = '';
        // Start from 0 instead of event.resultIndex to accumulate everything in current session
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        userInput.value = transcript;

        // Auto-send logic (VAD)
        if (silenceTimer) clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (userInput.value.trim() && isRecording) {
                if (autoSendToggle && autoSendToggle.checked) {
                    console.log("Silence detected, auto-sending...");
                    sendMessage();
                } else {
                    console.log("Silence detected, stopping recording (auto-send disabled)");
                    stopVoiceInput();
                    if (recognition) recognition.stop();
                }
            }
        }, 2000); // 2 seconds of silence before auto-send or stop
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
    if (voicePulse) voicePulse.classList.add('hidden');
    if (voiceBtn) voiceBtn.classList.remove('text-brand-600', 'dark:text-brand-400');
    if (voicePulseMobile) voicePulseMobile.classList.add('hidden');
    if (voiceBtnMobile) voiceBtnMobile.classList.remove('text-brand-600', 'dark:text-brand-400', 'bg-brand-50', 'dark:bg-brand-900/30');
    // Auto-focus the input so Enter key works and user can type
    if (userInput && window.innerWidth >= 768) userInput.focus(); // only auto-focus on desktop
}

// --- Text-to-Speech (TTS) Logic ---

// Consolidated Speak logic located further down

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

// Watch for system preference changes if in system mode
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
    const isEnabled = savedState === 'true';

    // Synchronize both desktop and mobile toggles
    if (autoSendToggle) {
        if (savedState !== null) autoSendToggle.checked = isEnabled;
        autoSendToggle.addEventListener('change', () => {
            localStorage.setItem('autoSendEnabled', autoSendToggle.checked);
            if (mobileAutoSendToggle) mobileAutoSendToggle.checked = autoSendToggle.checked;
        });
    }

    if (mobileAutoSendToggle) {
        if (savedState !== null) mobileAutoSendToggle.checked = isEnabled;
        mobileAutoSendToggle.addEventListener('change', () => {
            localStorage.setItem('autoSendEnabled', mobileAutoSendToggle.checked);
            if (autoSendToggle) autoSendToggle.checked = mobileAutoSendToggle.checked;
        });
    }
}

initAutoSendToggle();

// --- Auto-speak Toggle Initialization ---

function initAutoSpeakToggle() {
    const savedState = localStorage.getItem('autoSpeakEnabled');
    const isEnabled = savedState === 'true';

    // Synchronize both desktop and mobile toggles
    if (autoSpeakToggle) {
        if (savedState !== null) autoSpeakToggle.checked = isEnabled;
        autoSpeakToggle.addEventListener('change', () => {
            localStorage.setItem('autoSpeakEnabled', autoSpeakToggle.checked);
            if (mobileAutoSpeakToggle) mobileAutoSpeakToggle.checked = autoSpeakToggle.checked;
        });
    }

    if (mobileAutoSpeakToggle) {
        if (savedState !== null) mobileAutoSpeakToggle.checked = isEnabled;
        mobileAutoSpeakToggle.addEventListener('change', () => {
            localStorage.setItem('autoSpeakEnabled', mobileAutoSpeakToggle.checked);
            if (autoSpeakToggle) autoSpeakToggle.checked = mobileAutoSpeakToggle.checked;
        });
    }
}

initAutoSpeakToggle();

// --- Hands-Free Mode Toggle Initialization ---

function initHandsFreeToggle() {
    const savedState = localStorage.getItem('handsFreeEnabled');
    const isEnabled = savedState === 'true';

    // Synchronize both desktop and mobile toggles
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

initHandsFreeToggle();

// --- Speech Synthesis Helper ---

function speakText(text, btn) {
    if (!('speechSynthesis' in window)) return;

    // Helper to reset button state
    const resetButton = (b) => {
        if (!b) return;
        b.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 0 0 1 0 12.728M16.463 8.287a6 0 0 1 0 7.427M12 18.75V5.25A2.25 2.25 0 0 0 9.75 3H7.5a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h2.25a2.25 2.25 0 0 0 2.25-2.25Z" /></svg>';
        b.classList.remove('text-brand-600');
    };

    // Check if THIS button is currently active/speaking (Toggle OFF)
    if (btn && btn.classList.contains('text-brand-600')) {
        window.speechSynthesis.cancel();
        currentUtterance = null;
        resetButton(btn);
        return;
    }

    // Stop any current speech and reset all buttons
    window.speechSynthesis.cancel();
    document.querySelectorAll('.speak-btn.text-brand-600').forEach(b => resetButton(b));

    // Clean text: remove HTML tags, markdown markers, and redundant whitespace
    let cleanText = text.replace(/<[^>]*>/g, '') // Remove HTML
        .replace(/[*#_~`|-]/g, '') // Remove Markdown
        .replace(/\s+/g, ' ') // Normalize whitespace
        .trim();

    if (!cleanText) return;

    // Create utterance and store in global to prevent GC
    currentUtterance = new SpeechSynthesisUtterance(cleanText);

    // Select Voice
    const voices = window.speechSynthesis.getVoices();
    const savedVoiceName = localStorage.getItem('selectedVoiceName');
    let selectedVoice = voices.find(v => v.name === savedVoiceName);

    // Fallback logic
    if (!selectedVoice) {
        selectedVoice = voices.find(v => v.lang === 'en-US') ||
            voices.find(v => v.lang.startsWith('en')) ||
            voices[0];
    }

    if (selectedVoice) {
        currentUtterance.voice = selectedVoice;
    }

    // Utterance Event Handlers
    currentUtterance.onstart = () => {
        console.log("Speech started...");
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-volume-high animate-pulse text-brand-600"></i>';
            btn.classList.add('text-brand-600');
        }
    };

    currentUtterance.onend = () => {
        console.log("Speech finished.");
        if (btn) resetButton(btn);
        currentUtterance = null;

        // Hands-Free Loop: Restart microphone if enabled
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
            }, 1000); // 1s delay to avoid feedback
        } else if (isVoiceModeActive) {
            updateVoiceModalUI('ready');
        }
    };

    currentUtterance.onerror = (event) => {
        console.error("Speech error:", event.error);
        if (btn) resetButton(btn);
        currentUtterance = null;
    };

    // Final check for paused state (can happen in some browsers)
    if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
    }

    window.speechSynthesis.speak(currentUtterance);
}

// --- Voice Selection Logic ---

function populateVoiceList() {
    const voices = window.speechSynthesis.getVoices();
    const savedVoice = localStorage.getItem('selectedVoiceName');

    const updateContainer = (container, display) => {
        if (!container) return;
        container.innerHTML = '';

        voices.forEach(voice => {
            const option = document.createElement('button');
            option.type = 'button';
            option.className = "w-full text-left px-4 py-2 text-[10px] font-bold text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors uppercase tracking-tight";
            option.textContent = voice.name;

            if (savedVoice === voice.name) {
                option.classList.add('bg-blue-50/50', 'dark:bg-brand-900/20', 'text-brand-600', 'dark:text-brand-400');
                if (display) display.textContent = voice.name;
            }

            option.onclick = () => {
                localStorage.setItem('selectedVoiceName', voice.name);

                // Update both displays
                if (currentVoiceNameDisplay) currentVoiceNameDisplay.textContent = voice.name;
                if (mobileCurrentVoiceDisplay) mobileCurrentVoiceDisplay.textContent = voice.name;

                // Close both menus
                if (voiceDropdownMenu) voiceDropdownMenu.classList.add('hidden');
                if (mobileVoiceDropdownMenu) mobileVoiceDropdownMenu.classList.add('hidden');

                // Repopulate both lists to maintain highlighted state sync
                populateVoiceList();
            };

            container.appendChild(option);
        });
    };

    updateContainer(voiceSelectContainer, currentVoiceNameDisplay);
    updateContainer(mobileVoiceOptionsContainer, mobileCurrentVoiceDisplay);
}

function initVoiceSelect() {
    // Desktop Voice Select
    if (voiceDropdownBtn && voiceDropdownMenu) {
        voiceDropdownBtn.onclick = (e) => {
            e.stopPropagation();
            voiceDropdownMenu.classList.toggle('hidden');
            if (mobileVoiceDropdownMenu) mobileVoiceDropdownMenu.classList.add('hidden');
        };
    }

    // Mobile Voice Select
    if (mobileVoiceDropdownBtn && mobileVoiceDropdownMenu) {
        mobileVoiceDropdownBtn.onclick = (e) => {
            e.stopPropagation();
            mobileVoiceDropdownMenu.classList.toggle('hidden');
            if (voiceDropdownMenu) voiceDropdownMenu.classList.add('hidden');
        };
    }

    // Close on click outside (works for both)
    document.addEventListener('click', (e) => {
        if (voiceDropdownBtn && !voiceDropdownBtn.contains(e.target) && !voiceDropdownMenu.contains(e.target)) {
            voiceDropdownMenu.classList.add('hidden');
        }
        if (mobileVoiceDropdownBtn && !mobileVoiceDropdownBtn.contains(e.target) && !mobileVoiceDropdownMenu.contains(e.target)) {
            mobileVoiceDropdownMenu.classList.add('hidden');
        }
    });

    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = populateVoiceList;
    }

    populateVoiceList();
}

initVoiceSelect();

// --- Sidebar Toggle Logic ---

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    isSidebarCollapsed = !isSidebarCollapsed;

    if (isSidebarCollapsed) {
        // Collapse
        sidebar.classList.add('collapsed');
        sidebar.classList.remove('w-64');
    } else {
        // Expand
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

    // Check if it's today by comparing date strings
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
        const response = await fetch('/threads?specialist=psych');
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

        // Group threads by time period
        const grouped = {};
        threads.forEach(thread => {
            const group = getTimeGroup(thread.date);
            if (!grouped[group]) grouped[group] = [];
            grouped[group].push(thread);
        });

        // Display in order: Today, This Week, Older
        const groupOrder = ['Today', 'This Week', 'Older'];

        groupOrder.forEach(groupName => {
            if (!grouped[groupName]) return;

            // Group header
            const header = document.createElement('div');
            header.className = 'px-2 py-2 mt-4 first:mt-0 text-xs font-semibold text-gray-500 dark:text-gray-400 group-header sidebar-text';
            header.textContent = groupName;
            conversationsContainer.appendChild(header);

            // Conversations in this group
            grouped[groupName].forEach(thread => {
                const container = document.createElement('div');
                container.className = 'relative group/item mb-1';

                const btn = document.createElement('button');
                btn.className = `w-full px-3 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-left transition-colors conversation-item ${thread.thread_id === currentThreadId ? 'active bg-gray-100 dark:bg-gray-800' : ''}`;

                // Create conversation item with text
                btn.innerHTML = `
                    <div class="flex items-center gap-3">
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate pr-6 conversation-text">
                                ${thread.title}
                            </div>
                        </div>
                    </div>
                `;

                // Three-dot menu button
                const menuBtn = document.createElement('button');
                menuBtn.className = 'absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500 opacity-0 group-hover/item:opacity-100 transition-all z-10';
                menuBtn.innerHTML = '<i class="fa-solid fa-ellipsis-vertical text-xs"></i>';
                menuBtn.onclick = (e) => {
                    e.stopPropagation();
                    showConversationMenu(e, thread.thread_id, menuBtn);
                };

                btn.onclick = () => loadHistory(thread.thread_id);
                container.appendChild(btn);
                container.appendChild(menuBtn);
                conversationsContainer.appendChild(container);
            });
        });

        // Apply collapsed styles if sidebar is collapsed
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

    // Clear Chat UI
    if (chatMessagesArea) chatMessagesArea.innerHTML = ''; else chatContainer.innerHTML = '';

    try {
        const response = await fetch(`/history/${threadId}?specialist=psych`);
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                // Filter out empty AI messages from history
                if (msg.role === 'ai' && (!msg.content || msg.content.trim() === '')) {
                    return;
                }
                appendMessage(msg.role, msg.content, false, msg.index);
            });
        } else {
            // If no messages, show welcome
            showWelcomeMessage();
        }

        // Reload threads to update active state
        loadThreads();

        // Check for media to show/hide Media Vault button
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

        // Close mobile sidebar if open
        if (window.innerWidth < 768) {
            if (!sidebar.classList.contains('-translate-x-full')) {
                toggleSidebarMobile();
            }
        }
        // Scroll to bottom after history is loaded
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
    // Close mobile sidebar
    if (window.innerWidth < 768 && !sidebar.classList.contains('-translate-x-full')) {
        toggleSidebarMobile();
    }
}

// Attach New Chat Listener
if (newChatBtn) newChatBtn.onclick = startNewChat;

// Initial Load
async function initApp() {
    await loadThreads();
    startNewChat();
}

// Initialize the app
initApp();

// --- Logs Toggle ---

// --- Progress/Logs Panel Helpers ---
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

    // Doctor Label
    const headerHtml = `
        <div class="flex items-center gap-2 mb-1 pl-1">
             <span class="text-xs font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-emerald-600 dark:from-teal-400 dark:to-emerald-400 uppercase tracking-wider">Dr. Aria</span>
             <span class="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium">Psychiatrist</span>
        </div>
    `;

    const bubble = document.createElement('div');
    bubble.className = "border border-gray-100 dark:border-gray-700/50 shadow-sm rounded-2xl rounded-tl-sm p-4 text-gray-800 dark:text-gray-200";
    bubble.innerHTML = `
        <div class="flex gap-4 w-full">
           <div class="shrink-0 flex flex-col items-center">
                <img src="/static/images/phys_doctor.jpg" alt="Dr. Aria" class="w-10 h-10 rounded-full object-cover ring-2 ring-white dark:ring-gray-900 shadow-md">
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

    // Play typing sound
    const typingSound = document.getElementById('typing-sound');
    if (typingSound) {
        typingSound.volume = 0.15; // Set volume to 15% (subtle background sound)
        typingSound.currentTime = 0; // Reset to beginning
        const playPromise = typingSound.play();

        if (playPromise !== undefined) {
            playPromise.catch(e => {
                // Browser might block autoplay or audio file might not exist
                console.log('Typing sound not available or blocked:', e.message);
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

    // Stop typing sound
    const typingSound = document.getElementById('typing-sound');
    if (typingSound) {
        typingSound.pause();
        typingSound.currentTime = 0; // Reset for next time
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

    // Find the button involved to show loading state
    const btn = document.querySelector(`button[onclick="downloadReport('${reportId}')"]`);
    const originalContent = btn ? btn.innerHTML : '';
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Generating...';
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

        const canvas = await html2canvas(clone, {
            scale: 2,
            useCORS: true,
            backgroundColor: document.documentElement.classList.contains('dark') ? '#0b0f1a' : '#ffffff',
            windowWidth: 1200
        });

        const link = document.createElement('a');
        link.download = `Medical_Report_Dr_Aria_${new Date().toISOString().split('T')[0]}.png`;
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

function isHtmlReport(content) {
    return typeof content === 'string' &&
        (content.includes('class="medical-report') ||
            (content.includes('Dr. Aria') && content.includes('Consultant Psychiatrist') && content.includes('<!-- Header -->')));
}


function appendMessage(role, content, animate = true, index = null) {
    // Prevent empty AI messages from loading
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

    // Header label - ONLY for AI
    const headerHtml = isUser ? '' : `
        <div class="flex items-center gap-2 mb-1 pl-1">
             <span class="text-xs font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-emerald-600 dark:from-brand-400 dark:to-emerald-400 uppercase tracking-wider">Dr. Aria</span>
             <span class="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium">Psychiatrist</span>
        </div>
    `;

    const bubble = document.createElement('div');
    bubble.className = isUser
        ? "bg-[#0d9488] shadow-md rounded-2xl px-4 py-2.5 text-white text-base font-normal leading-relaxed text-justify rounded-br-sm transform translate-y-[-8px] relative"
        : "p-4 text-[#3c4043] dark:text-gray-200 text-base font-normal leading-relaxed tracking-gemini relative";

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
            renderedContent = marked.parse(content).replace(/\<table\>/g, '\<div class="table-wrapper"\>\<table\>').replace(/\<\/table\>/g, '\</table\>\</div\>');
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
        avatar.className = "w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm ring-2 ring-blue-100 dark:ring-blue-900/30 overflow-hidden mb-1";
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
                    <img src="/static/images/phys_doctor.jpg" alt="Dr. Aria" class="w-10 h-10 rounded-full object-cover ring-2 ring-white dark:ring-gray-900 shadow-md">
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

        const speakBtn = bubble.querySelector('.speak-btn');
        if (speakBtn) {
            speakBtn.onclick = (e) => {
                e.stopPropagation();
                const textToSpeak = bubble.querySelector('.message-content').innerText;
                speakText(textToSpeak, speakBtn);
            };
        }
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
        return div.querySelector('.message-content');
    }
}

// --- Data Formatting Helper ---

function formatDataForDisplay(data) {
    if (!data) return '<span class="text-gray-400 italic">None</span>';

    if (typeof data === 'string') {
        // Try parsing JSON string first
        try {
            const parsed = JSON.parse(data);
            if (typeof parsed === 'object') return formatDataForDisplay(parsed);
        } catch (e) { }
        return `<div class="text-gray-700 dark:text-gray-300 break-words whitespace-pre-wrap font-sans text-xs">${data}</div>`;
    }

    if (Array.isArray(data)) {
        if (data.length === 0) return '<span class="text-gray-400 italic">Empty List</span>';
        return `
            <div class="flex flex-col gap-2">
                ${data.map((item, index) => `
                    <div class="pl-3 border-l-2 border-gray-200 dark:border-gray-700">
                        <div class="text-[10px] text-gray-400 font-bold mb-1">ITEM ${index + 1}</div>
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
            <div class="grid grid-cols-1 gap-2">
                ${keys.map(key => `
                    <div class="group">
                        <div class="text-[10px] uppercase tracking-wider font-bold text-gray-400 mb-0.5 group-hover:text-brand-500 transition-colors">${key.replace(/_/g, ' ')}</div>
                        <div class="text-xs text-gray-800 dark:text-gray-200 break-words pl-1 border-l border-transparent group-hover:border-brand-500/30 transition-colors">
                            ${formatDataForDisplay(data[key])}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    return `<span class="text-gray-800 dark:text-gray-200 font-mono text-xs">${data}</span>`;
}


// --- Syntax Highlighting Helper ---
function syntaxHighlight(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'syntax-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'syntax-key';
            } else {
                cls = 'syntax-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'syntax-boolean';
        } else if (/null/.test(match)) {
            cls = 'syntax-boolean'; // null style
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

    // Remove empty state if present
    const emptyState = logsContainer.querySelector('.italic');
    if (emptyState) emptyState.remove();

    // Auto-open logs panel on tool start
    if (type === 'tool_start') {
        openLogs();
    }

    // Sanitize function to hide path details
    const sanitizeArgs = (args) => {
        const sanitized = JSON.parse(JSON.stringify(args)); // Deep copy
        if (sanitized.image_path) {
            sanitized.image_path = "Image File: " + sanitized.image_path.split(/[\\/]/).pop();
        }
        return sanitized;
    };


    if (type === 'tool_start') {
        // Create new Execution Card
        const cardId = `tool-${data.tool_call_id || Date.now()}`; // Fallback if no ID

        const div = document.createElement('div');
        div.id = cardId;
        div.className = "execution-card glass-card mb-4 w-full rounded-xl border p-4 active";

        const safeArgs = sanitizeArgs(data.args || {});
        const formattedInput = formatDataForDisplay(safeArgs);

        div.innerHTML = `
            <!-- Header -->
            <div class="flex items-center justify-between mb-3 cursor-pointer" onclick="toggleCard('${cardId}')">
                 <div class="flex items-center gap-2 min-w-0">
                     <span class="relative flex h-3 w-3 shrink-0">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
                     </span>
                     <span class="text-sm font-bold text-gray-800 dark:text-gray-100 tracking-tight truncate">${data.tool_name}</span>
                 </div>
                 <div class="flex items-center gap-2">
                    <div class="shrink-0 px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400 uppercase tracking-wider">
                        Running
                    </div>
                    <i id="icon-${cardId}" class="fa-solid fa-chevron-down text-gray-400 text-xs transition-transform duration-200" style="transform: rotate(180deg)"></i>
                 </div>
            </div>

            <div id="content-${cardId}" style="display: block;">
                <!-- "Neural Engine" Badge -->
                <div class="flex items-center gap-1.5 mb-3 opacity-70">
                    <i class="fa-solid fa-brain-circuit text-xs text-purple-500"></i>
                    <span class="text-[10px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-widest truncate">Gemini Neural Engine</span>
                </div>

                <!-- Arguments (Input) -->
                <div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 border border-gray-100 dark:border-gray-800/50">
                     <div class="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2 pb-1 border-b border-gray-200 dark:border-gray-700/50">Input Payload</div>
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
            // Check previous state
            const oldContent = document.getElementById(`content-${cardId}`);
            const wasHidden = oldContent && oldContent.style.display === 'none';

            // Update Existing Card to Success State
            card.classList.remove('active');
            card.classList.add('success');
            card.style.borderColor = '#10b981'; // Force green border

            // Format output clearly
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
                <!-- Header -->
                <div class="flex items-center justify-between mb-3 cursor-pointer" onclick="toggleCard('${cardId}')">
                     <div class="flex items-center gap-2 min-w-0">
                         <div class="h-5 w-5 shrink-0 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                            <i class="fa-solid fa-check text-[10px] text-green-600 dark:text-green-400"></i>
                         </div>
                         <span class="text-sm font-bold text-gray-800 dark:text-gray-100 tracking-tight truncate">${data.tool_name}</span>
                     </div>
                     <div class="flex items-center gap-2">
                        <div class="shrink-0 px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 uppercase tracking-wider">
                            Complete
                        </div>
                        <i id="icon-${cardId}" class="fa-solid fa-chevron-down text-gray-400 text-xs transition-transform duration-200" style="transform: ${rotateStyle}"></i>
                     </div>
                </div>

                <div id="content-${cardId}" style="display: ${displayStyle};">
                    <!-- Verified Badge -->
                     <div class="flex items-center gap-1.5 mb-3">
                        <i class="fa-solid fa-shield-check text-xs text-green-500"></i>
                        <span class="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest truncate">Data Verified</span>
                    </div>

                    <!-- Output (Result) -->
                    <div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 border border-gray-100 dark:border-gray-800/50 animate-fade-in group">
                         <div class="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2 pb-1 border-b border-gray-200 dark:border-gray-700/50 flex justify-between items-center">
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
        // Generic Error Log
        const div = document.createElement('div');
        div.className = "mb-3 p-3 rounded-xl bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 text-xs font-mono execution-card error w-full";
        div.innerHTML = `
            <div class="flex items-center gap-2 text-red-600 dark:text-red-400 font-bold mb-1">
                <i class="fa-solid fa-circle-exclamation"></i>
                System Error
            </div>
            <div class="text-gray-600 dark:text-gray-300 break-words whitespace-pre-wrap">${data.content}</div>
        `;
        logsContainer.appendChild(div);
    }

    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// --- Chat Logic ---

function stopResponse() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
}

async function sendMessage() {
    // Stop recording and clear timers if active
    if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
    }

    if (isRecording && recognition) {
        recognition.stop();
        stopVoiceInput();
    }

    const text = userInput.value.trim();
    if (!text && !selectedImage) return;

    // Pre-warm speech synthesis on user gesture to bypass browser restrictions
    if ('speechSynthesis' in window && autoSpeakToggle && autoSpeakToggle.checked) {
        const dummyUtterance = new SpeechSynthesisUtterance('');
        dummyUtterance.volume = 0;
        window.speechSynthesis.speak(dummyUtterance);
    }

    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.remove();

    userInput.value = '';
    // userInput.style.height = 'auto'; // Removed auto-resize logic

    // Hide send button after sending
    if (sendBtn) {
        sendBtn.classList.remove('scale-100', 'opacity-100');
        sendBtn.classList.add('scale-0', 'opacity-0');
    }
    if (sendBtnMobile) {
        sendBtnMobile.classList.remove('scale-100', 'opacity-100');
        sendBtnMobile.classList.add('scale-0', 'opacity-0');
    }

    // Create preview for user message
    let userMsgContent = { text: text };
    if (selectedImage) {
        // Use local preview for immediate feedback
        userMsgContent.image = imagePreview.src;
    }

    appendMessage('user', userMsgContent);

    // Show Media Vault button if user sent an image
    if (selectedImage) {
        const mediaVaultBtn = document.getElementById('media-vault-trigger');
        if (mediaVaultBtn) mediaVaultBtn.classList.remove('hidden');
    }

    // Prepare FormData for the actual upload
    const formData = new FormData();
    formData.append('message', text);
    formData.append('thread_id', currentThreadId);
    formData.append('specialist', 'psych');
    if (selectedImage) {
        formData.append('image', selectedImage);
    }

    // Clear selected image
    clearImage();

    // Show typing indicator while waiting for response
    showTypingIndicator();

    // Prepare AbortController
    abortController = new AbortController();
    const signal = abortController.signal;

    // Show stop button, hide send button area if necessary (sendBtn is already scale-0)
    if (stopBtn) {
        stopBtn.classList.remove('hidden');
        stopBtn.classList.add('flex');
        setTimeout(() => stopBtn.classList.add('scale-100', 'opacity-100'), 10);
    }
    if (stopBtnMobile) {
        stopBtnMobile.classList.remove('hidden');
        stopBtnMobile.classList.add('flex');
        setTimeout(() => stopBtnMobile.classList.add('scale-100', 'opacity-100'), 10);
    }

    let accumulatedText = "";
    let aiContentDiv = null;
    let firstTokenReceived = false;

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData, // Use FormData instead of JSON
            signal: signal
        });

        // If new chat started, refresh sidebar after a short delay
        if (chatContainer.children.length <= 2) {
            setTimeout(loadThreads, 2000);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.replace('data: ', '');
                    if (!jsonStr.trim()) continue;

                    try {
                        const event = JSON.parse(jsonStr);

                        if (event.type === 'token') {
                            // Remove typing indicator and create AI message on first token
                            if (!firstTokenReceived) {
                                removeTypingIndicator();
                                aiContentDiv = appendMessage('ai', event.content);
                                firstTokenReceived = true;
                                accumulatedText += event.content;
                                // aiContentDiv is handled below for the first token too
                            } else {
                                accumulatedText += event.content;
                            }
                            // Check if accumulated text is HTML report, render directly; otherwise parse as markdown
                            if (isHtmlReport(accumulatedText)) {
                                aiContentDiv.innerHTML = accumulatedText;
                                // Show Media Vault button since a report is being generated
                                const mediaVaultBtn = document.getElementById('media-vault-trigger');
                                if (mediaVaultBtn) mediaVaultBtn.classList.remove('hidden');
                            } else {
                                aiContentDiv.innerHTML = marked.parse(accumulatedText).replace(/\<table\>/g, '\<div class="table-wrapper"\>\<table\>').replace(/\<\/table\>/g, '\</table\>\</div\>');
                            }
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        } else if (event.type === 'tool_start') {
                            appendLog('tool_start', event);
                        } else if (event.type === 'tool_end') {
                            appendLog('tool_end', event);
                        } else if (event.type === 'error') {
                            appendLog('error', event);
                        }
                    } catch (e) {
                        console.error('Error parsing SSE event', e);
                    }
                }
            }
        }

        // Auto-speak after streaming finishes
        if (firstTokenReceived && aiContentDiv && autoSpeakToggle && autoSpeakToggle.checked) {
            const speakBtn = aiContentDiv.closest('.message-bubble')?.querySelector('.speak-btn');
            if (speakBtn) {
                speakText(aiContentDiv.innerText, speakBtn);
            }
        }

        // Refresh history to ensure indices are loaded for editing
        if (firstTokenReceived) {
            loadHistory(currentThreadId);
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            appendLog('info', { content: "Response stopped by user." });
        } else {
            console.error("Fetch error:", err);
            appendLog('error', { content: "Failed to connect to server." });
        }
        removeTypingIndicator(); // Remove indicator on error/abort
    } finally {
        // Reset Stop Button
        abortController = null;
        if (stopBtn) {
            stopBtn.classList.remove('scale-100', 'opacity-100');
            setTimeout(() => stopBtn.classList.add('hidden'), 300);
        }
        if (stopBtnMobile) {
            stopBtnMobile.classList.remove('scale-100', 'opacity-100');
            setTimeout(() => stopBtnMobile.classList.add('hidden'), 300);
        }

        // Check if Send Button should be restored
        if (userInput.value.trim().length > 0 || selectedImage) {
            if (sendBtn) {
                sendBtn.classList.remove('scale-0', 'opacity-0');
                sendBtn.classList.add('scale-100', 'opacity-100');
            }
            if (sendBtnMobile) {
                sendBtnMobile.classList.remove('scale-0', 'opacity-0');
                sendBtnMobile.classList.add('scale-100', 'opacity-100');
            }
        }
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function () {
    // Initialize voices for speech synthesis
    if ('speechSynthesis' in window) {
        // Load voices (they may not be immediately available)
        let voices = window.speechSynthesis.getVoices();

        // Chrome loads voices asynchronously
        if (voices.length === 0) {
            window.speechSynthesis.onvoiceschanged = () => {
                voices = window.speechSynthesis.getVoices();
                console.log('Voices loaded:', voices.length);
            };
        }
    }

    // Stop Button Listener
    if (stopBtn) stopBtn.onclick = stopResponse;

    // Handle form submission
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', function (e) {
            e.preventDefault();
            sendMessage();
        });
    }

    // Handle Enter key in input
    if (userInput) {
        userInput.addEventListener('input', function () {
            // Toggle Send Button Visibility for desktop AND mobile
            if (this.value.trim().length > 0 || selectedImage) {
                if (sendBtn) {
                    sendBtn.classList.remove('scale-0', 'opacity-0');
                    sendBtn.classList.add('scale-100', 'opacity-100');
                    sendBtn.disabled = false;
                }
                if (sendBtnMobile) {
                    sendBtnMobile.classList.remove('scale-0', 'opacity-0');
                    sendBtnMobile.classList.add('scale-100', 'opacity-100');
                    sendBtnMobile.disabled = false;
                }
            } else {
                if (sendBtn) {
                    sendBtn.classList.remove('scale-100', 'opacity-100');
                    sendBtn.classList.add('scale-0', 'opacity-0');
                    sendBtn.disabled = true;
                }
                if (sendBtnMobile) {
                    sendBtnMobile.classList.remove('scale-100', 'opacity-100');
                    sendBtnMobile.classList.add('scale-0', 'opacity-0');
                    sendBtnMobile.disabled = true;
                }
            }
        });

        userInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Handle window resize
    window.addEventListener('resize', function () {
        // Auto-close mobile sidebar on resize to desktop
        if (window.innerWidth >= 768) {
            sidebar.classList.add('-translate-x-full');
            if (mobileOverlay) mobileOverlay.classList.add('hidden');
        }
    });
});


// --- MEDIA VAULT & CONTEXT MENU ---

function isHtmlReport(text) {
    if (typeof text !== 'string') return false;
    return text.includes('clip-path-header') || text.includes('medical-report') || text.includes('report-container');
}

function showConversationMenu(event, threadId, anchorEl) {
    // Remove existing menus
    const existingMenu = document.getElementById('conversation-context-menu');
    if (existingMenu) existingMenu.remove();

    const menu = document.createElement('div');
    menu.id = 'conversation-context-menu';
    menu.className = 'fixed bg-white dark:bg-[#2D2D2D] border border-gray-100 dark:border-gray-700/50 rounded-xl shadow-2xl py-1 w-48 z-[100] animate-in fade-in zoom-in duration-200';

    // Use explicitly passed anchor element, fallback to target traversal
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
            <i class="fa-light fa-photo-film text-brand-500 dark:text-brand-400"></i>
            <span>Media</span>
        </button>
    `;

    document.body.appendChild(menu);

    // Close menu on click outside
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
    const menu = document.getElementById('conversation-context-menu');
    if (menu) menu.remove();

    toggleMediaVault();

    const grid = document.getElementById('media-vault-grid');
    const emptyState = document.getElementById('media-vault-empty');
    if (!grid) return;

    grid.innerHTML = '<div class="col-span-2 py-10 flex justify-center"><i class="fa-solid fa-spinner animate-spin text-2xl text-brand-500"></i></div>';
    emptyState.classList.add('hidden');

    try {
        const response = await fetch(`/history/${threadId}?specialist=psych`);
        const data = await response.json();
        const mediaItems = [];

        if (data.messages) {
            data.messages.forEach(msg => {
                // Check for uploaded images
                if (typeof msg.content === 'object' && msg.content.image) {
                    mediaItems.push({
                        url: msg.content.image,
                        type: 'Image',
                        date: msg.timestamp || ''
                    });
                } else if (typeof msg.content === 'string') {
                    // Check for medical reports (they start with the header)
                    if (isHtmlReport(msg.content)) {
                        mediaItems.push({
                            content: msg.content,
                            type: 'Report',
                            date: ''
                        });
                    }
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
                            <span class="text-[10px] font-bold text-gray-500 uppercase tracking-widest leading-tight mt-1">Medical Report</span>
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
        console.error("Failed to load media vault", e);
        grid.innerHTML = '<div class="col-span-2 text-center text-red-500 text-xs py-10 uppercase font-bold tracking-widest">Failed to load media</div>';
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



async function downloadReportAsImage(el) {
    if (!el) return;
    const btn = event.currentTarget;
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fa-light fa-spinner-third animate-spin"></i> Processing...';
    btn.disabled = true;

    try {
        const canvas = await html2canvas(el, {
            scale: 2,
            backgroundColor: document.documentElement.classList.contains('dark') ? '#0b0f1a' : '#ffffff',
            logging: false,
            useCORS: true,
            windowWidth: 800 // Ensure consistent rendering width
        });

        const link = document.createElement('a');
        link.download = `medical-report-${new Date().getTime()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    } catch (e) {
        console.error(e);
        alert("Failed to generate report image. Please try again.");
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}
