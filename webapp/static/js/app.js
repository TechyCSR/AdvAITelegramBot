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

// Multi-Platform Authentication System
class AuthSystem {
    constructor() {
        this.webApp = null;
        this.initData = null;
        this.user = null;
        this.authenticated = false;
        this.authConfig = null;
    }



    async initialize() {
        console.log('🚀 Initializing Authentication System...');
        
        // Wait for Telegram WebApp to load if present
        await new Promise(resolve => setTimeout(resolve, 150));
        
        // Simple and reliable Telegram detection
        const isTelegramEnvironment = this.detectTelegramEnvironment();
        console.log(`📱 Environment: ${isTelegramEnvironment ? 'TELEGRAM' : 'BROWSER'}`);
        
        if (isTelegramEnvironment) {
            console.log('🔄 Starting Telegram auto-login...');
            // Hide any loading overlay immediately
            this.hideAllOverlays();
            return await this.handleTelegramAuth();
        } else {
            console.log('🌐 Starting Browser auth...');
            return await this.handleBrowserAuth();
        }
    }

    detectTelegramEnvironment() {
        // Check if Telegram WebApp is available and has data
        const hasTelegramScript = typeof Telegram !== 'undefined';
        const hasWebApp = hasTelegramScript && Telegram.WebApp;
        const hasInitData = hasWebApp && Telegram.WebApp.initData && Telegram.WebApp.initData.length > 0;
        const hasTelegramUA = navigator.userAgent.includes('Telegram');
        
        console.log('🔍 Telegram Detection:', {
            hasTelegramScript,
            hasWebApp,
            hasInitData,
            initDataLength: hasInitData ? Telegram.WebApp.initData.length : 0,
            hasTelegramUA,
            userAgent: navigator.userAgent.substring(0, 100) + '...'
        });
        
        // Simple rule: If we have Telegram script AND (init data OR Telegram user agent), it's Telegram
        return hasTelegramScript && (hasInitData || hasTelegramUA);
    }

    hideAllOverlays() {
        const authOverlay = document.getElementById('authOverlay');
        if (authOverlay) {
            authOverlay.style.display = 'none';
            console.log('✅ Auth overlay hidden');
        }
    }

    async handleTelegramAuth() {
        try {
            // Load auth config
            await this.loadAuthConfig();
            
            // Setup Telegram WebApp
            this.webApp = Telegram.WebApp;
            this.initData = this.webApp.initData;
            
            // Configure WebApp
            this.webApp.ready();
            this.webApp.expand();
            this.webApp.enableClosingConfirmation();
            
            // Set Telegram theme
            if (this.webApp.colorScheme) {
                AppState.currentTheme = this.webApp.colorScheme;
                document.documentElement.setAttribute('data-theme', AppState.currentTheme);
            }
            
            // Handle back button
            this.webApp.BackButton.onClick(() => {
                this.webApp.close();
            });
            
            console.log('📋 Telegram Data:', {
                hasInitData: !!this.initData,
                dataLength: this.initData ? this.initData.length : 0,
                platform: this.webApp.platform
            });
            
            // Check existing session first
            const existingAuth = await this.checkAuthStatus();
            if (existingAuth) {
                console.log('✅ Already authenticated from session');
                return true;
            }
            
            // Authenticate with Telegram
            return await this.doTelegramAuth();
            
        } catch (error) {
            console.error('❌ Telegram auth error:', error);
            // Fallback to showing login options
            return this.showLoginOptions();
        }
    }

    async handleBrowserAuth() {
        try {
            await this.loadAuthConfig();
            
            // Check existing session first
            const existingAuth = await this.checkAuthStatus();
            if (existingAuth) {
                console.log('✅ Already authenticated from session');
                this.hideAllOverlays();
                return true;
            }
            
            // Show login options
            return this.showLoginOptions();
            
        } catch (error) {
            console.error('❌ Browser auth error:', error);
            return this.showLoginOptions();
        }
    }

    async loadAuthConfig() {
        try {
            console.log('Loading auth config...');
            const response = await fetch('/api/auth/config');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.authConfig = await response.json();
            console.log('Auth config loaded successfully:', this.authConfig);
        } catch (error) {
            console.error('Failed to load auth config:', error);
            // Default fallback config - assume both are disabled for safety
            this.authConfig = { 
                telegram_enabled: false, 
                google_enabled: false,
                google_client_id: null
            };
            console.log('Using fallback auth config:', this.authConfig);
        }
    }

    async doTelegramAuth() {
        if (!this.initData || this.initData.length === 0) {
            console.warn('⚠️ No Telegram init data - showing login options');
            return this.showLoginOptions();
        }

        try {
            console.log('🔐 Authenticating with Telegram...');
            
            const response = await fetch('/api/auth/telegram', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ initData: this.initData })
            });

            const data = await response.json();
            console.log('📡 Auth response:', { status: response.status, success: data.success });

            if (response.ok && data.success) {
                console.log('✅ Telegram auth successful!');
                
                // Set authentication state
                this.authenticated = true;
                this.user = data.user;
                AppState.user = data.user;
                AppState.authenticated = true;
                AppState.permissions = data.permissions;
                
                // Update UI
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
            console.error('❌ Telegram auth failed:', error);
            return this.showLoginOptions();
        }
    }

    showLoginOptions() {
        console.log('🔑 Showing login options...');
        
        const authOverlay = document.getElementById('authOverlay');
        if (authOverlay) {
            authOverlay.style.display = 'flex';
        }
        
        // Clear any status messages
        hideAuthStatus();
        
        // Load auth config if not loaded
        if (!this.authConfig) {
            this.loadAuthConfig().then(() => {
                this.renderAuthOptions();
            });
        } else {
            this.renderAuthOptions();
        }
        
        return false;
    }

    renderAuthOptions() {
        // This will call the existing showAuthenticationOptions method
        setTimeout(() => {
            this.showAuthenticationOptions();
        }, 100);
    }

    async authenticateGoogle() {
        try {
            if (!this.authConfig || !this.authConfig.google_enabled) {
                console.log('Google authentication not enabled in config');
                return;
            }

            console.log('Starting Google authentication setup...');
            showAuthStatus('Initializing Google login...');

            // Load Google Sign-In library
            await this.loadGoogleSignIn();
            console.log('Google Sign-In library loaded');

            // Check if google_client_id is available
            if (!this.authConfig.google_client_id) {
                throw new Error('Google Client ID not configured');
            }

            // Initialize Google Sign-In
            await google.accounts.id.initialize({
                client_id: this.authConfig.google_client_id,
                callback: this.handleGoogleCredentialResponse.bind(this)
            });
            console.log('Google Sign-In initialized');

            // Wait a moment for DOM to be ready
            setTimeout(() => {
                const googleButtonContainer = document.getElementById('googleSignInButton');
                if (googleButtonContainer) {
                    // Render the sign-in button
                    google.accounts.id.renderButton(
                        googleButtonContainer,
                        {
                            theme: AppState.currentTheme === 'dark' ? 'filled_black' : 'outline',
                            size: 'large',
                            width: 250,
                            text: 'continue_with'
                        }
                    );
                    console.log('Google Sign-In button rendered');

                    // Also show One Tap if available (but don't block if it fails)
                    try {
                        google.accounts.id.prompt();
                    } catch (promptError) {
                        console.log('One Tap prompt not available:', promptError);
                    }
                } else {
                    console.error('Google Sign-In button container not found');
                }
            }, 100);

            hideAuthStatus();
            
        } catch (error) {
            console.error('Google authentication setup error:', error);
            
            // Show a more specific error message to the user
            const googleButton = document.getElementById('googleSignInButton');
            if (googleButton) {
                googleButton.innerHTML = `
                    <div style="text-align: center; padding: 1rem; color: #dc3545; border: 1px solid #dc3545; border-radius: 8px;">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p style="margin: 0.5rem 0;">Google login temporarily unavailable</p>
                        <small style="color: #6c757d;">Please try again later or use Telegram</small>
                        <br><br>
                        <button onclick="authSystem.hideAuthOverlay()" style="background: #6c757d; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer;">
                            Continue Anyway
                        </button>
                    </div>
                `;
            }
            
            // Also show the auth overlay in case it was hidden
            const authOverlay = document.getElementById('authOverlay');
            if (authOverlay) {
                authOverlay.style.display = 'flex';
            }
        }
    }

    async loadGoogleSignIn() {
        return new Promise((resolve, reject) => {
            if (typeof google !== 'undefined' && google.accounts) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://accounts.google.com/gsi/client';
            script.async = true;
            script.defer = true;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async handleGoogleCredentialResponse(response) {
        try {
            showAuthStatus('Authenticating with Google...');

            const authResponse = await fetch('/api/auth/google/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    token: response.credential
                })
            });

            const data = await authResponse.json();

            if (authResponse.ok && data.success) {
                this.authenticated = true;
                this.user = data.user;
                AppState.user = data.user;
                AppState.authenticated = true;
                AppState.permissions = data.permissions;
                
                console.log('Google authentication successful:', this.user);
                this.hideAuthOverlay();
                this.updateUI();
                
                this.showSuccess(`Welcome, ${this.user.display_name}! You have premium access.`);
                
                return true;
            } else {
                throw new Error(data.error || 'Google authentication failed');
            }
        } catch (error) {
            console.error('Google authentication error:', error);
            this.showAuthError(error.message);
        }
    }

    showAuthenticationOptions() {
        console.log('Showing authentication options...', this.authConfig);
        
        const authOverlay = document.getElementById('authOverlay');
        if (!authOverlay) {
            console.error('Auth overlay not found');
            return;
        }

        // Ensure the overlay is visible
        authOverlay.style.display = 'flex';

        // Hide the auth status while showing options
        hideAuthStatus();
        
        // Hide auth actions
        const authActions = document.getElementById('authActions');
        if (authActions) {
            authActions.style.display = 'none';
        }

        // Create the authentication options HTML
        let optionsHtml = `
            <div class="auth-header">
                <div class="auth-logo">
                    <i class="fas fa-robot"></i>
                </div>
                <h1>Welcome to AI Image Generator</h1>
                <p class="auth-subtitle">Choose your preferred login method to get started</p>
            </div>
            <div class="auth-options-container">
        `;
        
        if (this.authConfig && this.authConfig.google_enabled) {
            optionsHtml += `
                <div class="auth-option google-option">
                    <div class="auth-option-header">
                        <div class="auth-option-icon google-icon">
                            <i class="fab fa-google"></i>
                        </div>
                        <div class="auth-option-content">
                            <h3>Continue with Google</h3>
                            <p>Get instant access with premium features</p>
                        </div>
                    </div>
                    <div class="premium-badge">
                        <i class="fas fa-crown"></i>
                        <span>Premium Features • 4 Images per Generation</span>
                    </div>
                    <div id="googleSignInButton" class="google-signin-container"></div>
                </div>
            `;
        }

        if (this.authConfig && this.authConfig.telegram_enabled) {
            optionsHtml += `
                <div class="auth-option telegram-option">
                    <div class="auth-option-header">
                        <div class="auth-option-icon telegram-icon">
                            <i class="fab fa-telegram"></i>
                        </div>
                        <div class="auth-option-content">
                            <h3>Continue with Telegram</h3>
                            <p>Access through our powerful Telegram bot</p>
                        </div>
                    </div>
                    <a href="https://t.me/AdvAIImageBot" target="_blank" class="auth-button telegram-button">
                        <i class="fab fa-telegram"></i>
                        <span>Open Telegram Bot</span>
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </div>
            `;
        }

        if (!this.authConfig || (!this.authConfig.google_enabled && !this.authConfig.telegram_enabled)) {
            optionsHtml += `
                <div class="auth-option">
                    <div class="auth-option-header">
                        <div class="auth-option-icon">
                            <i class="fas fa-unlock"></i>
                        </div>
                        <div class="auth-option-content">
                            <h3>Authentication Disabled</h3>
                            <p>You can use the app freely without login</p>
                        </div>
                    </div>
                    <button class="auth-button" onclick="authSystem.hideAuthOverlay()">
                        <i class="fas fa-arrow-right"></i>
                        <span>Continue to App</span>
                    </button>
                </div>
            `;
        }

        optionsHtml += '</div>';

        const authContent = document.querySelector('.auth-content');
        if (authContent) {
            console.log('Updating auth content with options HTML...');
            authContent.innerHTML = optionsHtml;
            console.log('Auth content updated successfully with options');
        } else {
            console.error('Auth content container not found');
        }

        // Ensure overlay is visible
        authOverlay.style.display = 'flex';
        console.log('Auth overlay made visible');

        // Initialize Google Sign-In if enabled
        if (this.authConfig && this.authConfig.google_enabled) {
            console.log('Initializing Google Sign-In...');
            setTimeout(() => this.authenticateGoogle(), 500); // Small delay to ensure DOM is updated
        }
    }

    async checkAuthStatus() {
        try {
            console.log('Checking authentication status...');
            const response = await fetch('/api/auth/status', {
                credentials: 'include'
            });
            const data = await response.json();
            
            console.log('Auth status response:', data);
            
            if (data.authenticated) {
                this.authenticated = true;
                this.user = data.user;
                AppState.user = data.user;
                AppState.authenticated = true;
                AppState.permissions = data.permissions;
                this.hideAuthOverlay();
                this.updateUI();
                console.log('User is already authenticated:', this.user);
                return true;
            }
            console.log('User is not authenticated');
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

    showSuccess(message) {
        const app = window.app;
        if (app && app.showSuccess) {
            app.showSuccess(message);
        } else {
            console.log('Success:', message);
        }
    }

    showAuthError(message) {
        console.error('❌ Auth error:', message);
        
        // Show authentication options as fallback
        console.log('🔄 Showing auth options as fallback...');
        return this.showLoginOptions();
    }

    hideAuthOverlay() {
        this.hideAllOverlays();
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

// Authentication UI helpers (moved below hideAuthStatus function)

function showAuthActions() {
    const authActions = document.getElementById('authActions');
    if (authActions) {
        authActions.style.display = 'block';
    }
}

function hideAuthStatus() {
    const authStatus = document.getElementById('authStatus');
    if (authStatus) {
        authStatus.style.display = 'none';
        console.log('Auth status hidden');
    }
}

function showAuthStatus(message, isError = false) {
    const authStatus = document.getElementById('authStatus');
    if (authStatus) {
        authStatus.innerHTML = isError ? 
            `<i class="fas fa-exclamation-triangle"></i><span>${message}</span>` :
            `<div class="loading-spinner"></div><span>${message}</span>`;
        authStatus.className = `auth-status ${isError ? 'error' : ''}`;
        authStatus.style.display = 'flex';
        console.log('Auth status shown:', message);
    }
}

// Main application class
class AdvAIApp {
    constructor() {
        this.authSystem = new AuthSystem();
        this.currentImages = [];
        this.selectedVariants = 1;
    }

    async initialize() {
        console.log('Initializing AdvAI App...');
        
        try {
            // Initialize authentication system first
            console.log('Starting authentication system initialization...');
            await this.authSystem.initialize();
            
            // Initialize UI components regardless of auth status
            console.log('Initializing UI components...');
            this.initializeTheme();
            this.initializeEventListeners();
            this.loadHistory();
            
            console.log('App initialized successfully');
        } catch (error) {
            console.error('App initialization failed:', error);
            // Still try to initialize basic UI even if auth fails
            this.initializeTheme();
            this.initializeEventListeners();
        }
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
            logoutBtn.addEventListener('click', () => this.authSystem.logout());
        }

        // Retry authentication
        const retryAuth = document.getElementById('retryAuth');
        if (retryAuth) {
            retryAuth.addEventListener('click', () => {
                console.log('🔄 Retry authentication clicked');
                // Simply reinitialize the auth system
                this.authSystem.initialize();
            });
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
                    <img src="${imageUrl}" alt="Generated image ${index + 1}" loading="lazy" onclick="app.openImageViewer('${imageUrl}', '${data.prompt.replace(/'/g, "\\'")}', '${data.style} • ${data.size}')">
                    <div class="image-overlay">
                        <div class="image-actions">
                            <button class="action-btn" onclick="app.downloadImage('${imageUrl}', ${index})" title="Download image">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="action-btn" onclick="app.shareImage('${imageUrl}')" title="Share image">
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
                <img class="history-image" src="${item.images[0]}" alt="Generated image" loading="lazy" onclick="app.openImageViewer('${item.images[0]}', '${item.prompt.replace(/'/g, "\\'")}', '${item.style} • ${item.model} • ${item.size}')">
                <div class="history-info">
                    <div class="history-prompt">${item.prompt.substring(0, 60)}${item.prompt.length > 60 ? '...' : ''}</div>
                    <div class="history-details">${item.style} • ${item.model} • ${item.size}</div>
                    <div class="history-date">${new Date(item.timestamp).toLocaleDateString()}</div>
                </div>
                <div class="history-actions">
                    <button class="action-btn" onclick="app.reloadFromHistory(${item.id})" title="Reload settings">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="action-btn" onclick="app.deleteFromHistory(${item.id})" title="Delete from history">
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
        if (navigator.share && this.authSystem.webApp) {
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

    // Image Viewer functionality
    openImageViewer(imageUrl, prompt, details) {
        const modal = document.getElementById('imageModal');
        if (!modal) {
            this.createImageModal();
        }
        
        const modalImage = document.getElementById('modalImage');
        const modalPrompt = document.getElementById('modalPrompt');
        const modalDetails = document.getElementById('modalDetails');
        
        if (modalImage) modalImage.src = imageUrl;
        if (modalPrompt) modalPrompt.textContent = prompt;
        if (modalDetails) modalDetails.textContent = details;
        
        const imageModal = document.getElementById('imageModal');
        if (imageModal) {
            imageModal.classList.add('active');
        }
    }

    createImageModal() {
        const modal = document.createElement('div');
        modal.id = 'imageModal';
        modal.className = 'image-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <img id="modalImage" class="modal-image" src="" alt="Preview image">
                <button class="modal-close" onclick="app.closeImageViewer()">
                    <i class="fas fa-times"></i>
                </button>
                <div class="modal-info">
                    <div class="modal-prompt" id="modalPrompt"></div>
                    <div class="modal-details" id="modalDetails"></div>
                    <div class="modal-actions">
                        <button class="modal-action-btn download" onclick="app.downloadCurrentImage()">
                            <i class="fas fa-download"></i>
                            Download
                        </button>
                        <button class="modal-action-btn share" onclick="app.shareCurrentImage()">
                            <i class="fas fa-share"></i>
                            Share
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeImageViewer();
            }
        });
        
        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                this.closeImageViewer();
            }
        });
        
        document.body.appendChild(modal);
    }

    closeImageViewer() {
        const modal = document.getElementById('imageModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    downloadCurrentImage() {
        const modalImage = document.getElementById('modalImage');
        if (modalImage && modalImage.src) {
            this.downloadImage(modalImage.src, 0);
        }
    }

    shareCurrentImage() {
        const modalImage = document.getElementById('modalImage');
        if (modalImage && modalImage.src) {
            this.shareImage(modalImage.src);
        }
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
        if (this.authSystem.webApp) {
            this.authSystem.webApp.showAlert(message);
        } else {
            console.log('Success:', message);
        }
    }

    showError(message) {
        if (this.authSystem.webApp) {
            this.authSystem.webApp.showAlert(`Error: ${message}`);
        } else {
            console.error('Error:', message);
            alert(`Error: ${message}`);
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM Content Loaded, initializing app...');
    
    // Create global app instance
    window.app = new AdvAIApp();
    
    // Make auth system globally accessible for debugging and fallbacks
    window.authSystem = window.app.authSystem;
    
    try {
        await window.app.initialize();
        
        // Add a fallback: if after 3 seconds the auth overlay is still showing
        // and user is not authenticated, force show auth options
        setTimeout(() => {
            if (!window.authSystem.authenticated) {
                const authOverlay = document.getElementById('authOverlay');
                const authStatus = document.getElementById('authStatus');
                
                if (authOverlay && authOverlay.style.display !== 'none' && 
                    authStatus && authStatus.style.display !== 'none') {
                    console.log('🔄 Fallback: Forcing authentication options display');
                    window.authSystem.showLoginOptions();
                }
            }
        }, 3000);
        
    } catch (error) {
        console.error('Failed to initialize app:', error);
    }
});

// Make app and authSystem globally available for onclick handlers
window.app = app;
window.authSystem = authSystem;