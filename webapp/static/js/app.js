// Local Storage Manager
class LocalStorageManager {
    constructor() {
        this.keys = {
            APP_STATE: 'advai_app_state_v2',
            HISTORY: 'advai_history_v2',
            THEME: 'advai_theme'
        };
        this.isAvailable = this.checkAvailability();
    }

    checkAvailability() {
        try {
            const test = 'localStorage_test';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            console.log('✅ localStorage is available');
            return true;
        } catch (error) {
            console.warn('❌ localStorage is not available:', error);
            return false;
        }
    }

    save(key, data) {
        if (!this.isAvailable) {
            console.warn('Cannot save data - localStorage not available');
            return false;
        }

        try {
            const serialized = JSON.stringify({
                data: data,
                timestamp: Date.now(),
                version: '2.0'
            });
            
            localStorage.setItem(this.keys[key] || key, serialized);
            console.log(`💾 Saved ${key}:`, data);
            return true;
        } catch (error) {
            console.error(`Failed to save ${key}:`, error);
            
            if (error.name === 'QuotaExceededError') {
                this.cleanup();
                // Try again after cleanup
                try {
                    localStorage.setItem(this.keys[key] || key, serialized);
                    return true;
                } catch (retryError) {
                    console.error('Failed to save even after cleanup:', retryError);
                }
            }
            return false;
        }
    }

    load(key, defaultValue = null) {
        if (!this.isAvailable) {
            console.warn('Cannot load data - localStorage not available');
            return defaultValue;
        }

        try {
            const stored = localStorage.getItem(this.keys[key] || key);
            if (!stored) {
                console.log(`📂 No data found for ${key}`);
                return defaultValue;
            }

            const parsed = JSON.parse(stored);
            console.log(`📖 Loaded ${key}:`, parsed.data);
            return parsed.data;
        } catch (error) {
            console.error(`Failed to load ${key}:`, error);
            // Remove corrupted data
            this.remove(key);
            return defaultValue;
        }
    }

    remove(key) {
        if (!this.isAvailable) return false;
        
        try {
            localStorage.removeItem(this.keys[key] || key);
            console.log(`🗑️ Removed ${key}`);
            return true;
        } catch (error) {
            console.error(`Failed to remove ${key}:`, error);
            return false;
        }
    }

    clear() {
        if (!this.isAvailable) return false;

        try {
            Object.values(this.keys).forEach(key => {
                localStorage.removeItem(key);
            });
            console.log('🧹 Cleared all app data');
            return true;
        } catch (error) {
            console.error('Failed to clear data:', error);
            return false;
        }
    }

    cleanup() {
        console.log('🧽 Running storage cleanup...');
        
        try {
            // Remove old version keys
            const oldKeys = ['advai_app_state', 'advai_image_history'];
            oldKeys.forEach(key => {
                if (localStorage.getItem(key)) {
                    localStorage.removeItem(key);
                    console.log(`Removed old key: ${key}`);
                }
            });

            // Limit history size
            const history = this.load('HISTORY', []);
            if (history.length > 20) {
                const trimmed = history.slice(0, 20);
                this.save('HISTORY', trimmed);
                console.log(`Trimmed history from ${history.length} to ${trimmed.length} items`);
            }

            return true;
        } catch (error) {
            console.error('Cleanup failed:', error);
            return false;
        }
    }

    getStorageInfo() {
        if (!this.isAvailable) return null;

        try {
            let totalSize = 0;
            let appSize = 0;
            let itemCount = 0;

            for (let key in localStorage) {
                if (localStorage.hasOwnProperty(key)) {
                    const size = localStorage[key].length + key.length;
                    totalSize += size;
                    
                    if (key.startsWith('advai_')) {
                        appSize += size;
                        itemCount++;
                    }
                }
            }

            return {
                totalSize: totalSize,
                appSize: appSize,
                itemCount: itemCount,
                totalSizeMB: (totalSize / 1024 / 1024).toFixed(2),
                appSizeMB: (appSize / 1024 / 1024).toFixed(2)
            };
        } catch (error) {
            console.error('Failed to get storage info:', error);
            return null;
        }
    }
}

class ImageGeneratorApp {
    constructor() {
        this.currentTab = 'generate';
        this.generatedImages = [];
        this.history = [];
        this.settings = {
            size: '1024x1024',
            variants: 1,
            style: 'default',
            model: 'flux'
        };
        
        // Modal state
        this.modalImages = [];
        this.currentModalIndex = 0;

        // Storage keys
        this.storageKeys = {
            APP_STATE: 'advai_app_state',
            HISTORY: 'advai_image_history', 
            THEME: 'advai_theme'
        };

        this.init();
    }

    init() {
        console.log('🚀 Initializing AdvAI Image Generator...');
        
        // Check localStorage first
        this.checkLocalStorage();
        
        // Load saved data BEFORE binding events
        this.loadTheme();
        this.loadHistory();
        this.loadAppState();
        
        // Bind events
        this.bindEvents();
        
        // Update UI
        this.updateCharCount();
        this.loadHistoryGrid();
        this.updateActiveTab();
        this.toggleCustomSizeInputs();
        this.showLoading(false);
        
        // Save initial state
        this.saveAppState();
        
        console.log('✅ App initialized with localStorage');
        this.debugStorage();
    }

    checkLocalStorage() {
        try {
            const test = 'test';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            console.log('✅ localStorage is available');
            return true;
        } catch (error) {
            console.error('❌ localStorage not available:', error);
            alert('Warning: Local storage is not available. Your data will not be saved.');
            return false;
        }
    }

    debugStorage() {
        console.log('📊 Storage Debug Info:');
        console.log('App State:', localStorage.getItem(this.storageKeys.APP_STATE));
        console.log('History:', localStorage.getItem(this.storageKeys.HISTORY));
        console.log('Theme:', localStorage.getItem(this.storageKeys.THEME));
        console.log('Current Settings:', this.settings);
        console.log('Generated Images:', this.generatedImages.length);
        console.log('History Items:', this.history.length);
    }

    saveAppState() {
        try {
            const appState = {
                timestamp: Date.now(),
                description: document.getElementById('description')?.value || '',
                settings: { ...this.settings },
                generatedImages: this.generatedImages || [],
                customSize: {
                    width: document.getElementById('customWidth')?.value || '1024',
                    height: document.getElementById('customHeight')?.value || '1024'
                },
                currentTab: this.currentTab
            };
            
            localStorage.setItem(this.storageKeys.APP_STATE, JSON.stringify(appState));
            console.log('💾 App state saved:', appState);
            return true;
        } catch (error) {
            console.error('❌ Failed to save app state:', error);
            return false;
        }
    }

    loadAppState() {
        try {
            const saved = localStorage.getItem(this.storageKeys.APP_STATE);
            if (!saved) {
                console.log('📂 No saved app state found');
                return false;
            }

            const appState = JSON.parse(saved);
            console.log('📖 Loading app state:', appState);

            // Restore description
            const descriptionEl = document.getElementById('description');
            if (descriptionEl && appState.description) {
                descriptionEl.value = appState.description;
                console.log('✅ Restored description:', appState.description);
                // Resize textarea to fit the restored content
                setTimeout(() => {
                    this.autoResizeTextarea();
                }, 50);
            }

            // Restore settings
            if (appState.settings) {
                this.settings = { ...this.settings, ...appState.settings };
                
                // Update UI elements
                const sizeSelect = document.getElementById('sizeSelect');
                const styleSelect = document.getElementById('styleSelect');
                const modelSelect = document.getElementById('modelSelect');
                
                if (sizeSelect) {
                    sizeSelect.value = this.settings.size;
                    console.log('✅ Restored size:', this.settings.size);
                }
                if (styleSelect) {
                    styleSelect.value = this.settings.style;
                    console.log('✅ Restored style:', this.settings.style);
                }
                if (modelSelect) {
                    modelSelect.value = this.settings.model;
                    console.log('✅ Restored model:', this.settings.model);
                }
                
                this.selectVariants(this.settings.variants.toString());
                console.log('✅ Restored variants:', this.settings.variants);
            }

            // Restore custom size inputs
            if (appState.customSize) {
                const customWidth = document.getElementById('customWidth');
                const customHeight = document.getElementById('customHeight');
                
                if (customWidth) customWidth.value = appState.customSize.width;
                if (customHeight) customHeight.value = appState.customSize.height;
                console.log('✅ Restored custom size:', appState.customSize);
            }

            // Restore generated images
            if (appState.generatedImages && appState.generatedImages.length > 0) {
                this.generatedImages = appState.generatedImages;
                setTimeout(() => {
                    this.displayResults();
                    console.log('✅ Restored generated images:', this.generatedImages.length);
                }, 100);
            }

            // Restore current tab
            if (appState.currentTab) {
                this.currentTab = appState.currentTab;
                console.log('✅ Restored tab:', this.currentTab);
            }

            return true;
        } catch (error) {
            console.error('❌ Failed to load app state:', error);
            // Clear corrupted data
            localStorage.removeItem(this.storageKeys.APP_STATE);
            return false;
        }
    }

    saveHistory() {
        try {
            localStorage.setItem(this.storageKeys.HISTORY, JSON.stringify(this.history));
            console.log('💾 History saved:', this.history.length, 'items');
            return true;
        } catch (error) {
            console.error('❌ Failed to save history:', error);
            return false;
        }
    }

    loadHistory() {
        try {
            const saved = localStorage.getItem(this.storageKeys.HISTORY);
            if (saved) {
                this.history = JSON.parse(saved);
                console.log('📖 History loaded:', this.history.length, 'items');
            } else {
                this.history = [];
                console.log('📂 No history found, starting fresh');
            }
            return true;
        } catch (error) {
            console.error('❌ Failed to load history:', error);
            this.history = [];
            localStorage.removeItem(this.storageKeys.HISTORY);
            return false;
        }
    }

    saveTheme(theme) {
        try {
            localStorage.setItem(this.storageKeys.THEME, theme);
            console.log('💾 Theme saved:', theme);
            return true;
        } catch (error) {
            console.error('❌ Failed to save theme:', error);
            return false;
        }
    }

    loadTheme() {
        try {
            const savedTheme = localStorage.getItem(this.storageKeys.THEME) || 'light';
            this.setTheme(savedTheme);
            console.log('📖 Theme loaded:', savedTheme);
            return true;
        } catch (error) {
            console.error('❌ Failed to load theme:', error);
            this.setTheme('light');
            return false;
        }
    }

    clearAppState() {
        try {
            // Clear all storage
            Object.values(this.storageKeys).forEach(key => {
                localStorage.removeItem(key);
            });
            
            // Reset form
            const descriptionEl = document.getElementById('description');
            const customWidth = document.getElementById('customWidth');
            const customHeight = document.getElementById('customHeight');
            
            if (descriptionEl) descriptionEl.value = '';
            if (customWidth) customWidth.value = '1024';
            if (customHeight) customHeight.value = '1024';
            
            // Reset settings
            this.settings = {
                size: '1024x1024',
                variants: 1,
                style: 'default',
                model: 'flux'
            };
            
            // Update UI
            const sizeSelect = document.getElementById('sizeSelect');
            const styleSelect = document.getElementById('styleSelect');
            const modelSelect = document.getElementById('modelSelect');
            
            if (sizeSelect) sizeSelect.value = this.settings.size;
            if (styleSelect) styleSelect.value = this.settings.style;
            if (modelSelect) modelSelect.value = this.settings.model;
            
            this.selectVariants(this.settings.variants.toString());
            
            // Clear images and history
            this.generatedImages = [];
            this.history = [];
            
            // Reset UI
            const resultsSection = document.getElementById('resultsSection');
            const resultsGrid = document.getElementById('resultsGrid');
            const historyGrid = document.getElementById('historyGrid');
            
            if (resultsSection) resultsSection.classList.remove('active');
            if (resultsGrid) resultsGrid.innerHTML = '';
            if (historyGrid) historyGrid.innerHTML = '';
            
            this.updateCharCount();
            this.resetTextareaHeight();
            this.toggleCustomSizeInputs();
            this.loadHistoryGrid();
            
            // Switch to generate tab
            this.switchTab('generate');
            
            console.log('🧹 All data cleared');
            this.showNotification('All data cleared successfully! 🧹', 'success');
            
            return true;
        } catch (error) {
            console.error('❌ Failed to clear app state:', error);
            this.showNotification('Failed to clear data', 'error');
            return false;
        }
    }

    // Auto-save method with immediate execution
    autoSave() {
        console.log('🔄 Auto-saving...');
        this.saveAppState();
        this.saveHistory();
    }

    bindEvents() {
        // Theme toggle
        document.getElementById('themeToggle')?.addEventListener('click', () => {
            this.toggleTheme();
        });

        // Clear data button
        document.getElementById('clearDataBtn')?.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all saved data? This will reset the form, settings, and generated images.')) {
                this.clearAppState();
            }
        });

        // Tab navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.closest('.nav-btn').dataset.tab);
            });
        });

        // Description textarea - save on every change
        const description = document.getElementById('description');
        if (description) {
            description.addEventListener('input', () => {
                this.updateCharCount();
                this.autoResizeTextarea();
                this.autoSave();
            });
            
            // Initial resize setup
            this.setupAutoResize();
        }

        // Settings - save immediately on change
        const sizeSelect = document.getElementById('sizeSelect');
        if (sizeSelect) {
            sizeSelect.addEventListener('change', (e) => {
                this.settings.size = e.target.value;
                this.toggleCustomSizeInputs();
                this.autoSave();
                console.log('Size changed to:', e.target.value);
            });
        }

        const customWidth = document.getElementById('customWidth');
        if (customWidth) {
            customWidth.addEventListener('input', () => {
                this.autoSave();
            });
        }

        const customHeight = document.getElementById('customHeight');
        if (customHeight) {
            customHeight.addEventListener('input', () => {
                this.autoSave();
            });
        }

        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.selectVariants(btn.dataset.variants);
                this.autoSave();
                console.log('Variants changed to:', btn.dataset.variants);
            });
        });

        const styleSelect = document.getElementById('styleSelect');
        if (styleSelect) {
            styleSelect.addEventListener('change', (e) => {
                this.settings.style = e.target.value;
                this.autoSave();
                console.log('Style changed to:', e.target.value);
            });
        }

        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                this.settings.model = e.target.value;
                this.autoSave();
                console.log('Model changed to:', e.target.value);
            });
        }

        // Generate button
        document.getElementById('generateBtn')?.addEventListener('click', () => {
            this.generateImages();
        });

        // Enhance prompt button
        document.getElementById('enhanceBtn')?.addEventListener('click', () => {
            this.enhancePrompt();
        });

        // Clear prompt button
        document.getElementById('clearPromptBtn')?.addEventListener('click', () => {
            this.clearPrompt();
        });

        // Results actions
        document.getElementById('downloadAllBtn')?.addEventListener('click', () => {
            this.downloadAll();
        });

        document.getElementById('saveToHistoryBtn')?.addEventListener('click', () => {
            this.saveToHistory();
        });

        // History actions
        document.getElementById('clearHistoryBtn')?.addEventListener('click', () => {
            this.clearHistory();
        });

        document.getElementById('exportHistoryBtn')?.addEventListener('click', () => {
            this.exportHistory();
        });

        // Image modal events
        document.getElementById('modalClose')?.addEventListener('click', () => {
            this.closeImageModal();
        });

        document.getElementById('modalPrev')?.addEventListener('click', () => {
            this.showPreviousImage();
        });

        document.getElementById('modalNext')?.addEventListener('click', () => {
            this.showNextImage();
        });

        document.getElementById('modalDownload')?.addEventListener('click', () => {
            this.downloadModalImage();
        });

        document.getElementById('modalShare')?.addEventListener('click', () => {
            this.shareModalImage();
        });

        // Close modal when clicking outside
        document.getElementById('imageModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'imageModal') {
                this.closeImageModal();
            }
        });

        // Keyboard navigation for modal
        document.addEventListener('keydown', (e) => {
            const modal = document.getElementById('imageModal');
            if (modal && modal.classList.contains('active')) {
                switch(e.key) {
                    case 'Escape':
                        this.closeImageModal();
                        break;
                    case 'ArrowLeft':
                        this.showPreviousImage();
                        break;
                    case 'ArrowRight':
                        this.showNextImage();
                        break;
                }
            }
        });

        // Auto-save on page unload
        window.addEventListener('beforeunload', () => {
            this.autoSave();
        });

        // Auto-save when page becomes hidden
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                this.autoSave();
            }
        });

        // Mobile menu functionality
        this.initMobileMenu();

        // Floating navigation button
        this.initFloatingNavButton();

        console.log('✅ All events bound');
    }

    switchTab(tab) {
        this.currentTab = tab;

        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tab);
        });

        // Update URL without refresh
        history.pushState({tab}, '', `#${tab}`);
        
        // Save immediately
        this.autoSave();
        
        // Trigger custom event for floating button
        document.dispatchEvent(new CustomEvent('tabChanged'));
        
        console.log('Tab switched to:', tab);
    }

    updateActiveTab() {
        const hash = window.location.hash.slice(1);
        if (hash && ['generate', 'history'].includes(hash)) {
            this.switchTab(hash);
        } else {
            this.switchTab(this.currentTab);
        }
    }

    updateCharCount() {
        const description = document.getElementById('description');
        const charCount = document.querySelector('.textarea-overlay .char-count');
        
        if (description && charCount) {
            const count = description.value.length;
            charCount.textContent = `${count}/1000`;
            
            if (count > 900) {
                charCount.style.color = 'var(--warning-color)';
            } else if (count > 1000) {
                charCount.style.color = 'var(--danger-color)';
            } else {
                charCount.style.color = 'var(--text-muted)';
            }
        }

        // Update clear button state
        this.updateClearButtonState();
    }

    updateClearButtonState() {
        const description = document.getElementById('description');
        const clearBtn = document.getElementById('clearPromptBtn');
        
        if (description && clearBtn) {
            clearBtn.disabled = description.value.trim().length === 0;
        }
    }

    clearPrompt() {
        const description = document.getElementById('description');
        if (description) {
            description.value = '';
            this.updateCharCount();
            this.resetTextareaHeight();
            this.autoSave();
            description.focus();
            this.showNotification('Prompt cleared!', 'success');
        }
    }

    setupAutoResize() {
        const description = document.getElementById('description');
        if (description) {
            // Set initial height
            this.resetTextareaHeight();
            
            // Also resize on paste
            description.addEventListener('paste', () => {
                setTimeout(() => {
                    this.autoResizeTextarea();
                }, 10);
            });

            // Resize on window resize for responsive behavior
            window.addEventListener('resize', () => {
                this.autoResizeTextarea();
            });
        }
    }

    autoResizeTextarea() {
        const description = document.getElementById('description');
        if (!description) return;

        // Reset height to auto to get proper scrollHeight
        description.style.height = 'auto';
        
        // Calculate responsive height limits based on screen size
        let minHeight = 120; // Default desktop min-height
        let maxHeight = 300; // Default desktop max-height
        
        if (window.innerWidth <= 400) {
            // Extra small screens
            minHeight = 100;
            maxHeight = 200;
        } else if (window.innerWidth <= 768) {
            // Mobile screens
            minHeight = 120;
            maxHeight = 250;
        }
        
        const scrollHeight = description.scrollHeight;
        
        // Set new height within bounds
        let newHeight = Math.max(minHeight, Math.min(maxHeight, scrollHeight));
        
        // Apply the new height
        description.style.height = newHeight + 'px';
        
        // Show scrollbar if content exceeds max height
        if (scrollHeight > maxHeight) {
            description.style.overflowY = 'auto';
        } else {
            description.style.overflowY = 'hidden';
        }
    }

    resetTextareaHeight() {
        const description = document.getElementById('description');
        if (description) {
            // Use responsive minimum height
            let minHeight = 120;
            if (window.innerWidth <= 400) {
                minHeight = 100;
            }
            
            description.style.height = minHeight + 'px';
            description.style.overflowY = 'hidden';
        }
    }

    toggleCustomSizeInputs() {
        const customInputs = document.getElementById('customSizeInputs');
        const sizeSelect = document.getElementById('sizeSelect');
        
        if (customInputs && sizeSelect) {
            if (sizeSelect.value === 'custom') {
                customInputs.style.display = 'grid';
            } else {
                customInputs.style.display = 'none';
            }
        }
    }

    initTheme() {
        // This is now handled in loadTheme() during init
        console.log('Theme initialization handled in loadTheme()');
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.saveTheme(theme);

        // Update theme toggle icon
        const themeToggle = document.getElementById('themeToggle');
        const mobileThemeToggle = document.getElementById('mobileThemeToggle');
        
        [themeToggle, mobileThemeToggle].forEach(toggle => {
            if (toggle) {
                const icon = toggle.querySelector('i');
                if (icon) {
                    if (theme === 'dark') {
                        icon.className = 'fas fa-sun';
                        toggle.title = 'Switch to light mode';
                    } else {
                        icon.className = 'fas fa-moon';
                        toggle.title = 'Switch to dark mode';
                    }
                }
            }
        });
    }

    initMobileMenu() {
        const hamburgerBtn = document.getElementById('hamburgerBtn');
        const mobileDropdown = document.getElementById('mobileDropdown');
        
        if (!hamburgerBtn || !mobileDropdown) return;

        // Toggle mobile menu
        hamburgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = mobileDropdown.classList.contains('active');
            
            if (isActive) {
                this.closeMobileMenu();
            } else {
                this.openMobileMenu();
            }
        });

        // Mobile menu items
        document.getElementById('mobileCleanDataBtn')?.addEventListener('click', () => {
            this.closeMobileMenu();
            if (confirm('Are you sure you want to clear all saved data? This will reset the form, settings, and generated images.')) {
                this.clearAppState();
            }
        });

        document.getElementById('mobileThemeToggle')?.addEventListener('click', () => {
            this.closeMobileMenu();
            this.toggleTheme();
        });

        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.mobile-menu')) {
                this.closeMobileMenu();
            }
        });

        // Close mobile menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMobileMenu();
            }
        });
    }

    openMobileMenu() {
        const hamburgerBtn = document.getElementById('hamburgerBtn');
        const mobileDropdown = document.getElementById('mobileDropdown');
        
        hamburgerBtn?.classList.add('active');
        mobileDropdown?.classList.add('active');
    }

    closeMobileMenu() {
        const hamburgerBtn = document.getElementById('hamburgerBtn');
        const mobileDropdown = document.getElementById('mobileDropdown');
        
        hamburgerBtn?.classList.remove('active');
        mobileDropdown?.classList.remove('active');
    }

    initFloatingNavButton() {
        const floatingBtn = document.getElementById('floatingNavBtn');
        const generateBtn = document.getElementById('generateBtn');
        
        if (!floatingBtn || !generateBtn) return;

        // Handle floating button click
        floatingBtn.addEventListener('click', () => {
            generateBtn.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        });

        // Show/hide button based on scroll position and tab
        this.updateFloatingButtonVisibility();
        
        // Update visibility on scroll
        window.addEventListener('scroll', () => {
            this.updateFloatingButtonVisibility();
        });

        // Update visibility on tab change
        document.addEventListener('tabChanged', () => {
            this.updateFloatingButtonVisibility();
        });

        // Update visibility on window resize
        window.addEventListener('resize', () => {
            this.updateFloatingButtonVisibility();
        });
    }

    updateFloatingButtonVisibility() {
        const floatingBtn = document.getElementById('floatingNavBtn');
        const generateBtn = document.getElementById('generateBtn');
        
        if (!floatingBtn || !generateBtn || window.innerWidth > 768) {
            floatingBtn?.classList.remove('visible');
            return;
        }

        // Only show on generate tab
        if (this.currentTab !== 'generate') {
            floatingBtn.classList.remove('visible');
            return;
        }

        // Get generate button position relative to document
        const generateBtnRect = generateBtn.getBoundingClientRect();
        const generateBtnTop = generateBtnRect.top + window.scrollY;
        
        // Check if user has scrolled to or past the generate button area
        // Add some buffer (100px) so it disappears slightly before reaching the button
        const hasReachedGenerateBtn = window.scrollY >= (generateBtnTop - window.innerHeight + 100);
        
        // Show floating button only if:
        // 1. User has scrolled down (>200px)
        // 2. User hasn't reached the generate button area yet
        const shouldShow = window.scrollY > 200 && !hasReachedGenerateBtn;
        
        if (shouldShow) {
            floatingBtn.classList.add('visible');
        } else {
            floatingBtn.classList.remove('visible');
        }
    }

    selectVariants(variants) {
        this.settings.variants = parseInt(variants);
        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.variants === variants);
        });
    }

    async enhancePrompt() {
        const description = document.getElementById('description');
        const enhanceBtn = document.getElementById('enhanceBtn');
        
        if (!description || !enhanceBtn) return;
        
        const originalText = description.value.trim();

        if (!originalText) {
            this.showNotification('Please enter a description first', 'warning');
            return;
        }

        enhanceBtn.disabled = true;
        enhanceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enhancing...';

        try {
            const response = await fetch('/api/enhance-prompt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: originalText
                })
            });

            const data = await response.json();

            if (response.ok) {
                description.value = data.enhanced_prompt;
                this.updateCharCount();
                this.autoResizeTextarea();
                this.autoSave();
                this.showNotification('Prompt enhanced successfully!', 'success');
            } else {
                throw new Error(data.error || 'Failed to enhance prompt');
            }
        } catch (error) {
            console.error('Error enhancing prompt:', error);
            this.showNotification('Failed to enhance prompt. Please try again.', 'error');
        } finally {
            enhanceBtn.disabled = false;
            enhanceBtn.innerHTML = '<i class="fas fa-sparkles"></i> Enhance Prompt';
        }
    }

    async generateImages() {
        const description = document.getElementById('description');
        if (!description) return;
        
        const descriptionValue = description.value.trim();
        
        if (!descriptionValue) {
            this.showNotification('Please enter an image description', 'warning');
            return;
        }

        if (descriptionValue.length > 1000) {
            this.showNotification('Description is too long (max 1000 characters)', 'error');
            return;
        }

        // Get size value (handle custom sizes)
        let sizeValue = this.settings.size;
        if (this.settings.size === 'custom') {
            const width = parseInt(document.getElementById('customWidth')?.value || '1024');
            const height = parseInt(document.getElementById('customHeight')?.value || '1024');
            
            if (!width || !height || width < 256 || height < 256 || width > 2048 || height > 2048) {
                this.showNotification('Please enter valid dimensions (256-2048 pixels)', 'error');
                return;
            }
            
            sizeValue = `${width}x${height}`;
        }

        // Show loading overlay
        this.showLoading(true);

        // Prepare form data
        const formData = new FormData();
        formData.append('description', descriptionValue);
        formData.append('size', sizeValue);
        formData.append('variants', this.settings.variants.toString());
        formData.append('style', this.settings.style);
        formData.append('model', this.settings.model);

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.generatedImages = data.images.map(img => ({
                    url: img.url,
                    prompt: descriptionValue,
                    size: sizeValue,
                    style: this.settings.style,
                    model: this.settings.model
                }));
                
                this.displayResults();
                this.autoSave(); // Save after generation
                this.showNotification('Images generated successfully!', 'success');
            } else {
                throw new Error(data.error || 'Failed to generate images');
            }
        } catch (error) {
            console.error('Error generating images:', error);
            this.showNotification('Failed to generate images. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    displayResults() {
        const resultsSection = document.getElementById('resultsSection');
        const resultsGrid = document.getElementById('resultsGrid');

        if (!resultsSection || !resultsGrid) return;

        resultsGrid.innerHTML = '';

        this.generatedImages.forEach((image, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item fadeIn';
            resultItem.innerHTML = `
                <img src="${image.url}" alt="Generated image ${index + 1}" class="result-image" data-index="${index}">
                <div class="result-actions">
                    <button class="result-btn primary" data-action="download" data-index="${index}">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="result-btn" data-action="share" data-index="${index}">
                        <i class="fas fa-share"></i> Share
                    </button>
                    <button class="result-btn" data-action="variation" data-index="${index}">
                        <i class="fas fa-magic"></i> Variation
                    </button>
                </div>
            `;
            
            // Add click event to image for modal
            const imageElement = resultItem.querySelector('.result-image');
            if (imageElement) {
                imageElement.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.openImageModal(this.generatedImages, index);
                });
            }
            
            // Add click events to buttons
            const downloadBtn = resultItem.querySelector('[data-action="download"]');
            const shareBtn = resultItem.querySelector('[data-action="share"]');
            const variationBtn = resultItem.querySelector('[data-action="variation"]');
            
            if (downloadBtn) {
                downloadBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.downloadImage(image.url, index);
                });
            }
            
            if (shareBtn) {
                shareBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.shareImage(image.url);
                });
            }
            
            if (variationBtn) {
                variationBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.regenerateVariation(image.url);
                });
            }
            
            resultsGrid.appendChild(resultItem);
        });

        resultsSection.classList.add('active');
        resultsSection.scrollIntoView({ behavior: 'smooth' });
        
        // Save after displaying results
        this.autoSave();
        console.log('Results displayed and saved');
    }

    showLoading(show) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (!loadingOverlay) return;
        
        loadingOverlay.style.display = show ? 'flex' : 'none';

        if (show) {
            // Animate progress bar
            const progressFill = document.getElementById('progressFill');
            if (progressFill) {
                progressFill.style.width = '0%';
                
                let progress = 0;
                const interval = setInterval(() => {
                    progress += Math.random() * 10;
                    if (progress > 100) progress = 100;
                    progressFill.style.width = `${progress}%`;
                    
                    if (progress >= 100) {
                        clearInterval(interval);
                    }
                }, 200);
            }
        }
    }

    async downloadImage(url, index) {
        try {
            const response = await fetch(url);
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `generated-image-${index + 1}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            window.URL.revokeObjectURL(downloadUrl);
            this.showNotification('Image downloaded successfully!', 'success');
        } catch (error) {
            console.error('Error downloading image:', error);
            this.showNotification('Failed to download image', 'error');
        }
    }

    async downloadAll() {
        if (this.generatedImages.length === 0) {
            this.showNotification('No images to download', 'warning');
            return;
        }

        for (let i = 0; i < this.generatedImages.length; i++) {
            await this.downloadImage(this.generatedImages[i].url, i);
            // Add delay between downloads
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    shareImage(url) {
        if (navigator.share) {
            navigator.share({
                title: 'AI Generated Image',
                text: 'Check out this AI generated image!',
                url: url
            }).catch(err => console.log('Error sharing:', err));
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(url).then(() => {
                this.showNotification('Image URL copied to clipboard!', 'success');
            }).catch(() => {
                this.showNotification('Could not copy URL', 'error');
            });
        }
    }

    async regenerateVariation(imageUrl) {
        // Show coming soon notification with more details
        this.showNotification('🎨 Image Variation feature coming soon! This will allow you to create variations of existing images.', 'info');
    }

    saveToHistory() {
        if (this.generatedImages.length === 0) {
            this.showNotification('No images to save', 'warning');
            return;
        }

        const description = document.getElementById('description');
        if (!description) return;
        
        const descriptionValue = description.value.trim();
        const historyItem = {
            id: Date.now(),
            description: descriptionValue,
            images: this.generatedImages,
            settings: { ...this.settings },
            timestamp: new Date().toISOString(),
            date: new Date().toLocaleDateString()
        };

        this.history.unshift(historyItem);
        
        // Keep only last 50 items
        if (this.history.length > 50) {
            this.history = this.history.slice(0, 50);
        }

        this.saveHistory();
        this.loadHistoryGrid();
        this.showNotification('Images saved to history!', 'success');
        console.log('Images saved to history, total items:', this.history.length);
    }

    loadHistoryGrid() {
        const historyGrid = document.getElementById('historyGrid');
        if (!historyGrid) return;
        
        historyGrid.innerHTML = '';

        if (this.history.length === 0) {
            historyGrid.innerHTML = `
                <div class="text-center text-muted" style="grid-column: 1 / -1; padding: 2rem;">
                    <i class="fas fa-history" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.3;"></i>
                    <p>No generation history yet</p>
                    <p>Generate some images to see them here!</p>
                </div>
            `;
            console.log('History grid shows empty state');
            return;
        }

        this.history.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.innerHTML = `
                <img src="${item.images[0].url}" alt="Generated image" class="history-image">
                <div class="history-info">
                    <div class="history-prompt">${item.description}</div>
                    <div class="history-date">${item.date} • ${item.images.length} image${item.images.length > 1 ? 's' : ''}</div>
                </div>
            `;

            // Add click event to image for modal
            const imageElement = historyItem.querySelector('.history-image');
            if (imageElement) {
                imageElement.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent triggering the viewHistoryItem event
                    this.openImageModal(item.images, 0);
                });
            }

            // Click on the rest of the item loads it
            historyItem.addEventListener('click', (e) => {
                if (!e.target.classList.contains('history-image')) {
                    this.viewHistoryItem(item);
                }
            });

            historyGrid.appendChild(historyItem);
        });
        
        console.log('History grid loaded with', this.history.length, 'items');
    }

    viewHistoryItem(item) {
        // Load the history item back into the generator
        const description = document.getElementById('description');
        if (description) {
            description.value = item.description;
        }
        
        // Restore settings
        this.settings = { ...item.settings };
        
        const sizeSelect = document.getElementById('sizeSelect');
        const styleSelect = document.getElementById('styleSelect');
        const modelSelect = document.getElementById('modelSelect');
        
        if (sizeSelect) sizeSelect.value = this.settings.size;
        if (styleSelect) styleSelect.value = this.settings.style;
        if (modelSelect) modelSelect.value = this.settings.model;
        
        this.selectVariants(this.settings.variants.toString());
        
        // Set generated images
        this.generatedImages = item.images;
        this.displayResults();
        
        // Switch to generate tab
        this.switchTab('generate');
        
        // Save the loaded state
        this.autoSave();
        
        this.showNotification('History item loaded!', 'success');
        console.log('History item loaded:', item.description);
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear all history?')) {
            this.history = [];
            this.saveHistory();
            this.loadHistoryGrid();
            this.showNotification('History cleared!', 'success');
            console.log('History cleared');
        }
    }

    exportHistory() {
        if (this.history.length === 0) {
            this.showNotification('No history to export', 'warning');
            return;
        }

        const dataStr = JSON.stringify(this.history, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `advai-image-history-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        this.showNotification('History exported successfully!', 'success');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--background);
            border: 2px solid var(--border);
            border-radius: var(--radius);
            padding: 1rem 1.5rem;
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            max-width: 300px;
            animation: slideInRight 0.3s ease-out;
        `;

        // Set color based on type
        const colors = {
            success: 'var(--accent-color)',
            error: 'var(--danger-color)',
            warning: 'var(--warning-color)',
            info: 'var(--primary-color)'
        };

        notification.style.borderColor = colors[type] || colors.info;

        // Add icon
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <i class="${icons[type] || icons.info}" style="color: ${colors[type] || colors.info};"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    background: none;
                    border: none;
                    font-size: 1.2em;
                    cursor: pointer;
                    color: var(--text-muted);
                    margin-left: auto;
                ">×</button>
            </div>
        `;

        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    // Image Modal Methods
    openImageModal(images, startIndex = 0) {
        this.modalImages = images;
        this.currentModalIndex = startIndex;
        
        this.updateModalDisplay();
        
        const modal = document.getElementById('imageModal');
        if (modal) {
            modal.classList.add('active');
            
            // Prevent body scroll when modal is open
            document.body.style.overflow = 'hidden';
        }
    }

    closeImageModal() {
        const modal = document.getElementById('imageModal');
        if (modal) {
            modal.classList.remove('active');
            
            // Restore body scroll
            document.body.style.overflow = 'auto';
        }
    }

    updateModalDisplay() {
        if (this.modalImages.length === 0) return;
        
        const currentImage = this.modalImages[this.currentModalIndex];
        
        // Update image
        const modalImage = document.getElementById('modalImage');
        if (modalImage) {
            modalImage.src = currentImage.url;
            modalImage.alt = `Generated image ${this.currentModalIndex + 1}`;
        }
        
        // Update counter
        const modalCounter = document.getElementById('modalCounter');
        if (modalCounter) {
            modalCounter.textContent = `${this.currentModalIndex + 1} / ${this.modalImages.length}`;
        }
        
        // Update info
        const modalPrompt = document.getElementById('modalPrompt');
        const modalSize = document.getElementById('modalSize');
        const modalStyle = document.getElementById('modalStyle');
        const modalModel = document.getElementById('modalModel');
        
        if (modalPrompt) modalPrompt.textContent = currentImage.prompt || '';
        if (modalSize) modalSize.textContent = currentImage.size || '';
        if (modalStyle) modalStyle.textContent = this.capitalizeFirstLetter(currentImage.style || 'default');
        if (modalModel) modalModel.textContent = this.capitalizeFirstLetter(currentImage.model || 'flux');
        
        // Update navigation buttons
        const prevBtn = document.getElementById('modalPrev');
        const nextBtn = document.getElementById('modalNext');
        
        if (prevBtn) {
            prevBtn.disabled = this.modalImages.length <= 1 || this.currentModalIndex === 0;
            prevBtn.style.display = this.modalImages.length <= 1 ? 'none' : 'flex';
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.modalImages.length <= 1 || this.currentModalIndex === this.modalImages.length - 1;
            nextBtn.style.display = this.modalImages.length <= 1 ? 'none' : 'flex';
        }
        
        // Update download link
        const downloadLink = document.getElementById('modalDownload');
        if (downloadLink) {
            downloadLink.href = currentImage.url;
            downloadLink.download = `generated-image-${this.currentModalIndex + 1}.png`;
        }
    }

    showPreviousImage() {
        if (this.currentModalIndex > 0) {
            this.currentModalIndex--;
            this.updateModalDisplay();
        }
    }

    showNextImage() {
        if (this.currentModalIndex < this.modalImages.length - 1) {
            this.currentModalIndex++;
            this.updateModalDisplay();
        }
    }

    async downloadModalImage() {
        if (this.modalImages.length === 0) return;
        
        const currentImage = this.modalImages[this.currentModalIndex];
        await this.downloadImage(currentImage.url, this.currentModalIndex);
    }

    shareModalImage() {
        if (this.modalImages.length === 0) return;
        
        const currentImage = this.modalImages[this.currentModalIndex];
        this.shareImage(currentImage.url);
    }

    capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 DOM loaded, initializing app...');
    window.app = new ImageGeneratorApp();
});

// Handle browser back/forward
window.addEventListener('popstate', (e) => {
    if (e.state && e.state.tab && window.app) {
        window.app.switchTab(e.state.tab);
    }
}); 