/**
 * AdvAI Image Generator - Frontend Application
 * Enhanced with Telegram Mini App Authentication
 */

// Global application state
const AppState = {
    user: null,
    authenticated: false,
    permissions: {},
    currentTheme: localStorage.getItem('theme') || 'dark',
    history: JSON.parse(localStorage.getItem('imageHistory') || '[]'),
    isGenerating: false,
    telegramWebApp: null
};

// Telegram Mini App Integration
class TelegramAuth {
    constructor() {
        this.webApp = null;
        this.initData = null;
        this.user = null;
        this.authenticated = false;
    }

    async initialize() {
        console.log('Initializing Telegram Mini App...');
        
        // Check if running in Telegram
        if (typeof Telegram === 'undefined' || !Telegram.WebApp) {
            console.warn('Not running in Telegram environment');
            return this.handleNonTelegramEnvironment();
        }

        this.webApp = Telegram.WebApp;
        this.initData = this.webApp.initData;
        
        // Configure Telegram Web App
        this.webApp.ready();
        this.webApp.expand();
        this.webApp.enableClosingConfirmation();
        
        // Set theme based on Telegram theme
        if (this.webApp.colorScheme) {
            AppState.currentTheme = this.webApp.colorScheme;
            document.documentElement.setAttribute('data-theme', AppState.currentTheme);
        }

        // Handle back button
        this.webApp.BackButton.onClick(() => {
            this.webApp.close();
        });

        console.log('Telegram Web App initialized:', {
            platform: this.webApp.platform,
            version: this.webApp.version,
            colorScheme: this.webApp.colorScheme,
            themeParams: this.webApp.themeParams
        });

        return this.authenticate();
    }

    async authenticate() {
        if (!this.initData) {
            return this.showAuthError('No initialization data available');
        }

        try {
            showAuthStatus('Authenticating with Telegram...');
            
            const response = await fetch('/api/auth/telegram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    initData: this.initData
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.authenticated = true;
                this.user = data.user;
                AppState.user = data.user;
                AppState.authenticated = true;
                AppState.permissions = data.permissions;
                
                console.log('Authentication successful:', this.user);
                this.hideAuthOverlay();
                this.updateUI();
                
                // Show welcome message
                if (this.webApp) {
                    this.webApp.showAlert(`Welcome, ${this.user.display_name}!`);
                }
                
                return true;
            } else {
                throw new Error(data.error || 'Authentication failed');
            }
        } catch (error) {
            console.error('Authentication error:', error);
            return this.showAuthError(error.message);
        }
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status', {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.authenticated) {
                this.authenticated = true;
                this.user = data.user;
                AppState.user = data.user;
                AppState.authenticated = true;
                AppState.permissions = data.permissions;
                this.hideAuthOverlay();
                this.updateUI();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Auth status check failed:', error);
            return false;
        }
    }

    async logout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            this.authenticated = false;
            this.user = null;
            AppState.user = null;
            AppState.authenticated = false;
            AppState.permissions = {};
            
            location.reload(); // Restart the authentication flow
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    handleNonTelegramEnvironment() {
        console.log('Handling non-Telegram environment');
        
        // Check if authentication is required
        fetch('/api/health')
            .then(response => response.json())
            .then(data => {
                if (data.telegram_auth_required) {
                    this.showAuthError('This app can only be opened through Telegram');
                } else {
                    // Authentication disabled, proceed without auth
                    this.hideAuthOverlay();
                }
            })
            .catch(() => {
                this.showAuthError('Service unavailable');
            });
        
        return false;
    }

    showAuthError(message) {
        console.error('Auth error:', message);
        showAuthStatus(message, true);
        showAuthActions();
        return false;
    }

    hideAuthOverlay() {
        const overlay = document.getElementById('authOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    updateUI() {
        if (!this.user) return;

        // Update user info section
        const userInfo = document.getElementById('userInfo');
        const userName = document.getElementById('userName');
        const userStatus = document.getElementById('userStatus');
        const userAvatar = document.getElementById('userAvatar');

        if (userInfo && userName && userStatus) {
            userName.textContent = this.user.display_name;
            userStatus.textContent = this.user.is_premium ? '✨ Premium' : '👤 Standard';
            
            if (this.user.photo_url) {
                userAvatar.innerHTML = `<img src="${this.user.photo_url}" alt="User Avatar">`;
            }
            
            userInfo.style.display = 'flex';
        }

        // Show user menu buttons
        const userMenuBtns = document.querySelectorAll('.user-menu-btn');
        userMenuBtns.forEach(btn => btn.style.display = 'block');

        // Update detailed user info in modal
        this.updateUserModal();

        // Update UI based on permissions
        this.updatePermissionBasedUI();
    }

    updateUserModal() {
        const elements = {
            userNameDetailed: document.getElementById('userNameDetailed'),
            userIdDetailed: document.getElementById('userIdDetailed'),
            userBadge: document.getElementById('userBadge'),
            userAvatarLarge: document.getElementById('userAvatarLarge'),
            maxImagesPerRequest: document.getElementById('maxImagesPerRequest'),
            premiumFeatures: document.getElementById('premiumFeatures')
        };

        if (elements.userNameDetailed) {
            elements.userNameDetailed.textContent = this.user.display_name;
        }
        if (elements.userIdDetailed) {
            elements.userIdDetailed.textContent = `ID: ${this.user.id}`;
        }
        if (elements.userBadge) {
            elements.userBadge.textContent = this.user.is_premium ? '✨ Premium User' : '👤 Standard User';
            elements.userBadge.className = `user-badge ${this.user.is_premium ? 'premium' : 'standard'}`;
        }
        if (elements.userAvatarLarge && this.user.photo_url) {
            elements.userAvatarLarge.innerHTML = `<img src="${this.user.photo_url}" alt="User Avatar">`;
        }
        if (elements.maxImagesPerRequest) {
            elements.maxImagesPerRequest.textContent = AppState.permissions.max_images_per_request || 2;
        }
        if (elements.premiumFeatures) {
            elements.premiumFeatures.textContent = this.user.is_premium ? 'Yes' : 'No';
        }
    }

    updatePermissionBasedUI() {
        // Update variant options based on permissions
        const variantBtns = document.querySelectorAll('.variant-btn');
        const maxImages = AppState.permissions.max_images_per_request || 2;
        
        variantBtns.forEach(btn => {
            const variants = parseInt(btn.dataset.variants);
            if (variants > maxImages) {
                btn.disabled = true;
                btn.title = 'Premium feature';
                btn.classList.add('premium-required');
            }
        });

        // Update enhance button if user doesn't have permission
        const enhanceBtn = document.getElementById('enhanceBtn');
        if (enhanceBtn && !AppState.permissions.can_enhance_prompts) {
            enhanceBtn.disabled = true;
            enhanceBtn.title = 'Feature not available';
        }
    }
}

// Authentication UI helpers
function showAuthStatus(message, isError = false) {
    const authStatus = document.getElementById('authStatus');
    if (authStatus) {
        authStatus.innerHTML = isError ? 
            `<i class="fas fa-exclamation-triangle"></i><span>${message}</span>` :
            `<div class="loading-spinner"></div><span>${message}</span>`;
        authStatus.className = `auth-status ${isError ? 'error' : ''}`;
    }
}

function showAuthActions() {
    const authActions = document.getElementById('authActions');
    if (authActions) {
        authActions.style.display = 'block';
    }
}

// Main application class
class AdvAIApp {
    constructor() {
        this.telegramAuth = new TelegramAuth();
        this.currentImages = [];
        this.selectedVariants = 1;
    }

    async initialize() {
        console.log('Initializing AdvAI App...');
        
        // Initialize Telegram authentication first
        await this.telegramAuth.initialize();
        
        // Check if already authenticated
        if (!this.telegramAuth.authenticated) {
            await this.telegramAuth.checkAuthStatus();
        }
        
        // Initialize UI components
        this.initializeTheme();
        this.initializeEventListeners();
        this.loadHistory();
        
        console.log('App initialized successfully');
    }

    initializeTheme() {
        document.documentElement.setAttribute('data-theme', AppState.currentTheme);
        
        const themeToggleBtns = document.querySelectorAll('.theme-toggle');
        themeToggleBtns.forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = AppState.currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        });
    }

    initializeEventListeners() {
        // Tab navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Theme toggle
        document.querySelectorAll('.theme-toggle').forEach(btn => {
            btn.addEventListener('click', () => this.toggleTheme());
        });

        // Generate button
        const generateBtn = document.getElementById('generateBtn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateImages());
        }

        // Enhance prompt button
        const enhanceBtn = document.getElementById('enhanceBtn');
        if (enhanceBtn) {
            enhanceBtn.addEventListener('click', () => this.enhancePrompt());
        }

        // Clear prompt button
        const clearPromptBtn = document.getElementById('clearPromptBtn');
        if (clearPromptBtn) {
            clearPromptBtn.addEventListener('click', () => this.clearPrompt());
        }

        // Variant selection
        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.selectVariants(e.target));
        });

        // Custom size toggle
        const sizeSelect = document.getElementById('sizeSelect');
        if (sizeSelect) {
            sizeSelect.addEventListener('change', () => this.toggleCustomSize());
        }

        // Character counter
        const description = document.getElementById('description');
        if (description) {
            description.addEventListener('input', () => this.updateCharCounter());
        }

        // User menu
        document.querySelectorAll('.user-menu-btn').forEach(btn => {
            btn.addEventListener('click', () => this.showUserModal());
        });

        // Modal close
        const closeUserModal = document.getElementById('closeUserModal');
        if (closeUserModal) {
            closeUserModal.addEventListener('click', () => this.hideUserModal());
        }

        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.telegramAuth.logout());
        }

        // Retry authentication
        const retryAuth = document.getElementById('retryAuth');
        if (retryAuth) {
            retryAuth.addEventListener('click', () => location.reload());
        }

        // Mobile menu toggle
        const hamburgerBtn = document.getElementById('hamburgerBtn');
        const mobileDropdown = document.getElementById('mobileDropdown');
        if (hamburgerBtn && mobileDropdown) {
            hamburgerBtn.addEventListener('click', () => {
                hamburgerBtn.classList.toggle('active');
                mobileDropdown.classList.toggle('active');
            });
        }

        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (hamburgerBtn && mobileDropdown && 
                !hamburgerBtn.contains(e.target) && 
                !mobileDropdown.contains(e.target)) {
                hamburgerBtn.classList.remove('active');
                mobileDropdown.classList.remove('active');
            }
        });

        // Clear data buttons
        document.querySelectorAll('.clear-data-btn').forEach(btn => {
            btn.addEventListener('click', () => this.clearAllData());
        });

        // History actions
        const clearHistoryBtn = document.getElementById('clearHistoryBtn');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        }
    }

    switchTab(tabName) {
        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabName);
        });

        // Load history if switching to history tab
        if (tabName === 'history') {
            this.renderHistory();
        }
    }

    toggleTheme() {
        AppState.currentTheme = AppState.currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', AppState.currentTheme);
        localStorage.setItem('theme', AppState.currentTheme);

        // Update theme toggle icons
        document.querySelectorAll('.theme-toggle i').forEach(icon => {
            icon.className = AppState.currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        });
    }

    selectVariants(button) {
        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        this.selectedVariants = parseInt(button.dataset.variants);
    }

    toggleCustomSize() {
        const sizeSelect = document.getElementById('sizeSelect');
        const customInputs = document.getElementById('customSizeInputs');
        
        if (sizeSelect && customInputs) {
            customInputs.style.display = sizeSelect.value === 'custom' ? 'flex' : 'none';
        }
    }

    updateCharCounter() {
        const description = document.getElementById('description');
        const charCount = document.querySelector('.char-count');
        
        if (description && charCount) {
            const count = description.value.length;
            charCount.textContent = `${count}/1000`;
            charCount.classList.toggle('warning', count > 900);
        }
    }

    clearPrompt() {
        const description = document.getElementById('description');
        if (description) {
            description.value = '';
            this.updateCharCounter();
        }
    }

    async enhancePrompt() {
        if (!AppState.authenticated) {
            this.showError('Please authenticate first');
            return;
        }

        const description = document.getElementById('description');
        const enhanceBtn = document.getElementById('enhanceBtn');
        
        if (!description || !description.value.trim()) {
            this.showError('Please enter a prompt first');
            return;
        }

        const originalText = enhanceBtn.innerHTML;
        enhanceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Enhancing...</span>';
        enhanceBtn.disabled = true;

        try {
            const response = await fetch('/api/enhance-prompt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    prompt: description.value.trim()
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                description.value = data.enhanced_prompt;
                this.updateCharCounter();
                this.showSuccess('Prompt enhanced successfully!');
            } else {
                throw new Error(data.error || 'Enhancement failed');
            }
        } catch (error) {
            console.error('Enhancement error:', error);
            this.showError(error.message);
        } finally {
            enhanceBtn.innerHTML = originalText;
            enhanceBtn.disabled = false;
        }
    }

    async generateImages() {
        if (!AppState.authenticated) {
            this.showError('Please authenticate first');
            return;
        }

        if (AppState.isGenerating) {
            return;
        }

        const description = document.getElementById('description');
        const generateBtn = document.getElementById('generateBtn');
        
        if (!description || !description.value.trim()) {
            this.showError('Please enter a description');
            return;
        }

        // Get form values
        const prompt = description.value.trim();
        const style = document.getElementById('styleSelect').value;
        const model = document.getElementById('modelSelect').value;
        const size = this.getSelectedSize();
        const numImages = this.selectedVariants;

        AppState.isGenerating = true;
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        generateBtn.disabled = true;

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    prompt,
                    style,
                    model,
                    size,
                    num_images: numImages
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.currentImages = data.images;
                this.displayImages(data);
                this.addToHistory(data);
                this.showSuccess(`Generated ${data.images.length} image(s) successfully!`);
                
                // Switch to results
                document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
            } else {
                throw new Error(data.error || 'Generation failed');
            }
        } catch (error) {
            console.error('Generation error:', error);
            this.showError(error.message);
        } finally {
            AppState.isGenerating = false;
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;
        }
    }

    getSelectedSize() {
        const sizeSelect = document.getElementById('sizeSelect');
        if (sizeSelect.value === 'custom') {
            const width = document.getElementById('customWidth').value || 1024;
            const height = document.getElementById('customHeight').value || 1024;
            return `${width}x${height}`;
        }
        return sizeSelect.value;
    }

    displayImages(data) {
        const imagesGrid = document.getElementById('imagesGrid');
        if (!imagesGrid) return;

        imagesGrid.innerHTML = '';

        data.images.forEach((imageUrl, index) => {
            const imageItem = document.createElement('div');
            imageItem.className = 'image-item';
            imageItem.innerHTML = `
                <div class="image-container">
                    <img src="${imageUrl}" alt="Generated image ${index + 1}" loading="lazy">
                    <div class="image-overlay">
                        <div class="image-actions">
                            <button class="action-btn" onclick="app.downloadImage('${imageUrl}', ${index})">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="action-btn" onclick="app.shareImage('${imageUrl}')">
                                <i class="fas fa-share"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="image-info">
                    <span class="image-prompt">${data.prompt.substring(0, 50)}${data.prompt.length > 50 ? '...' : ''}</span>
                    <span class="image-details">${data.style} • ${data.size}</span>
                </div>
            `;
            imagesGrid.appendChild(imageItem);
        });

        // Show results section
        document.getElementById('resultsSection').style.display = 'block';
    }

    addToHistory(data) {
        const historyItem = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            prompt: data.prompt,
            style: data.style,
            model: data.model,
            size: data.size,
            images: data.images,
            count: data.count
        };

        AppState.history.unshift(historyItem);
        
        // Keep only last 50 items
        if (AppState.history.length > 50) {
            AppState.history = AppState.history.slice(0, 50);
        }

        this.saveHistory();
    }

    saveHistory() {
        localStorage.setItem('imageHistory', JSON.stringify(AppState.history));
    }

    loadHistory() {
        try {
            AppState.history = JSON.parse(localStorage.getItem('imageHistory') || '[]');
        } catch (error) {
            console.error('Error loading history:', error);
            AppState.history = [];
        }
    }

    renderHistory() {
        const historyGrid = document.getElementById('historyGrid');
        if (!historyGrid) return;

        if (AppState.history.length === 0) {
            historyGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-images"></i>
                    <h3>No history yet</h3>
                    <p>Your generated images will appear here</p>
                </div>
            `;
            return;
        }

        historyGrid.innerHTML = '';
        
        AppState.history.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.innerHTML = `
                <div class="history-preview">
                    <img src="${item.images[0]}" alt="Generated image" loading="lazy">
                    <div class="history-count">${item.count}</div>
                </div>
                <div class="history-info">
                    <div class="history-prompt">${item.prompt.substring(0, 60)}${item.prompt.length > 60 ? '...' : ''}</div>
                    <div class="history-details">${item.style} • ${item.model} • ${item.size}</div>
                    <div class="history-date">${new Date(item.timestamp).toLocaleDateString()}</div>
                </div>
                <div class="history-actions">
                    <button class="action-btn" onclick="app.reloadFromHistory(${item.id})">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="action-btn" onclick="app.deleteFromHistory(${item.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            historyGrid.appendChild(historyItem);
        });
    }

    reloadFromHistory(id) {
        const item = AppState.history.find(h => h.id === id);
        if (!item) return;

        // Switch to generate tab
        this.switchTab('generate');

        // Fill form with history data
        document.getElementById('description').value = item.prompt;
        document.getElementById('styleSelect').value = item.style;
        document.getElementById('modelSelect').value = item.model;
        
        if (item.size && item.size !== 'custom') {
            document.getElementById('sizeSelect').value = item.size;
        }

        // Update UI
        this.updateCharCounter();
        this.toggleCustomSize();
    }

    deleteFromHistory(id) {
        AppState.history = AppState.history.filter(h => h.id !== id);
        this.saveHistory();
        this.renderHistory();
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear all history?')) {
            AppState.history = [];
            this.saveHistory();
            this.renderHistory();
        }
    }

    clearAllData() {
        if (confirm('Are you sure you want to clear all saved data? This cannot be undone.')) {
            localStorage.clear();
            AppState.history = [];
            this.renderHistory();
            this.showSuccess('All data cleared successfully');
        }
    }

    downloadImage(imageUrl, index) {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = `advai-generated-${Date.now()}-${index + 1}.jpg`;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async shareImage(imageUrl) {
        if (navigator.share && this.telegramAuth.webApp) {
            try {
                await navigator.share({
                    title: 'AI Generated Image',
                    text: 'Check out this AI-generated image!',
                    url: imageUrl
                });
            } catch (error) {
                console.log('Share failed:', error);
                this.copyToClipboard(imageUrl);
            }
        } else {
            this.copyToClipboard(imageUrl);
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showSuccess('Link copied to clipboard!');
        }).catch(() => {
            this.showError('Failed to copy link');
        });
    }

    showUserModal() {
        const modal = document.getElementById('userModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    hideUserModal() {
        const modal = document.getElementById('userModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    showSuccess(message) {
        if (this.telegramAuth.webApp) {
            this.telegramAuth.webApp.showAlert(message);
        } else {
            console.log('Success:', message);
        }
    }

    showError(message) {
        if (this.telegramAuth.webApp) {
            this.telegramAuth.webApp.showAlert(`Error: ${message}`);
        } else {
            console.error('Error:', message);
            alert(`Error: ${message}`);
        }
    }
}

// Initialize app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', async () => {
    app = new AdvAIApp();
    await app.initialize();
});

// Make app globally available for onclick handlers
window.app = app;