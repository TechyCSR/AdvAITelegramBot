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

    getCurrentTelegramUser() {
        // Extract current user data from Telegram initData
        if (!this.initData || this.initData.length === 0) {
            return null;
        }

        try {
            // Parse the URL-encoded initData
            const urlParams = new URLSearchParams(this.initData);
            const userDataString = urlParams.get('user');
            
            if (!userDataString) {
                return null;
            }

            // Parse the user JSON data
            const userData = JSON.parse(userDataString);
            console.log('Current Telegram user data:', userData);
            return userData;
        } catch (error) {
            console.error('Error parsing current Telegram user data:', error);
            return null;
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
            
            // Check existing session but validate current user matches
            const existingAuth = await this.checkAuthStatus();
            if (existingAuth) {
                // Validate that the current Telegram user matches the stored session
                const currentTelegramUser = this.getCurrentTelegramUser();
                if (currentTelegramUser && this.user) {
                    const storedUserId = this.user.telegram_id;
                    const currentUserId = currentTelegramUser.id;
                    
                    if (storedUserId === currentUserId) {
                        console.log('✅ Already authenticated from session with matching user');
                        return true;
                    } else {
                        console.log('⚠️ Session user mismatch - clearing session and re-authenticating');
                        console.log(`Stored: ${storedUserId}, Current: ${currentUserId}`);
                        // Clear session without page reload to continue with fresh auth
                        await fetch('/api/auth/logout', {
                            method: 'POST',
                            credentials: 'include'
                        });
                        // Reset local state
                        this.authenticated = false;
                        this.user = null;
                        AppState.user = null;
                        AppState.authenticated = false;
                        AppState.permissions = {};
                        // Continue to fresh authentication below
                    }
                } else {
                    console.log('✅ Already authenticated from session (non-Telegram user)');
                    return true;
                }
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
                
                // Debug premium status
                console.log('🔍 Telegram Auth - Premium Debug:');
                console.log('User object:', this.user);
                console.log('Permissions:', AppState.permissions);
                console.log('Premium info from server:', data.premium);
                console.log('Max images per request:', AppState.permissions.max_images_per_request);
                
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
                console.log('🔍 Google Auth - Premium Debug:');
                console.log('User object:', this.user);
                console.log('Permissions:', AppState.permissions);
                console.log('Premium info from server:', data.premium);
                console.log('Max images per request:', AppState.permissions.max_images_per_request);
                
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
                    <a href="https://t.me/AdvChatGPTBot" target="_blank" class="auth-button telegram-button">
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
                
                // Debug premium status
                console.log('🔍 Premium Debug Info:');
                console.log('User object:', this.user);
                console.log('Permissions:', AppState.permissions);
                console.log('Premium info from server:', data.premium);
                console.log('Max images per request:', AppState.permissions.max_images_per_request);
                
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
        
        console.log('🎯 UI update completed for user:', this.user.display_name);
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
            elements.userBadge.className = `user-badge-modern ${this.user.is_premium ? 'premium' : 'standard'}`;
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
        
        console.log('🔧 Updating UI based on permissions:', AppState.permissions);
        console.log('👥 User premium status:', AppState.user?.is_premium);
        console.log('🖼️ Max images allowed:', maxImages);
        
        variantBtns.forEach(btn => {
            const variants = parseInt(btn.dataset.variants);
            console.log(`🎛️ Checking variant button for ${variants} images`);
            
            if (variants > maxImages) {
                btn.disabled = true;
                btn.title = AppState.user?.is_premium ? 'Contact support for higher limits' : 'Premium feature - Upgrade to generate multiple images';
                btn.classList.add('premium-required');
                console.log(`❌ Disabled ${variants}-image button (limit: ${maxImages})`);
                
                // If this button is currently active, switch to the max allowed
                if (btn.classList.contains('active')) {
                    btn.classList.remove('active');
                    // Find and activate the highest allowed button
                    const allowedBtn = Array.from(variantBtns).find(b => parseInt(b.dataset.variants) <= maxImages);
                    if (allowedBtn) {
                        allowedBtn.classList.add('active');
                        this.selectedVariants = parseInt(allowedBtn.dataset.variants);
                        console.log(`✅ Switched to ${this.selectedVariants}-image option`);
                    }
                }
            } else {
                btn.disabled = false;
                btn.title = '';
                btn.classList.remove('premium-required');
                console.log(`✅ Enabled ${variants}-image button`);
            }
        });

        // Update enhance button if user doesn't have permission
        const enhanceBtn = document.getElementById('enhanceBtn');
        if (enhanceBtn && !AppState.permissions.can_enhance_prompts) {
            enhanceBtn.disabled = true;
            enhanceBtn.title = 'Feature not available';
            console.log('❌ Disabled enhance button');
        } else if (enhanceBtn) {
            enhanceBtn.disabled = false;
            enhanceBtn.title = '';
            console.log('✅ Enabled enhance button');
        }

        // Add visual indicators for premium features
        this.updatePremiumVisualIndicators();
    }

    updatePremiumVisualIndicators() {
        // Add premium badges to restricted buttons
        const premiumRequiredBtns = document.querySelectorAll('.variant-btn.premium-required');
        premiumRequiredBtns.forEach(btn => {
            if (!btn.querySelector('.premium-indicator')) {
                const indicator = document.createElement('span');
                indicator.className = 'premium-indicator';
                indicator.innerHTML = '<i class="fas fa-crown"></i>';
                indicator.title = 'Premium Feature';
                btn.appendChild(indicator);
            }
        });

        // Remove premium indicators from enabled buttons
        const enabledBtns = document.querySelectorAll('.variant-btn:not(.premium-required)');
        enabledBtns.forEach(btn => {
            const indicator = btn.querySelector('.premium-indicator');
            if (indicator) {
                indicator.remove();
            }
        });
    }

    openHistoryImage(historyId, imageIndex) {
        const historyItem = AppState.history.find(h => h.id === historyId);
        if (!historyItem) return;

        // Set up current image data for navigation
        this.currentImages = historyItem.images;
        this.currentImageData = historyItem;
        this.currentImageIndex = imageIndex;

        // Open the image viewer
        this.openImageViewer(
            historyItem.images[imageIndex], 
            historyItem.prompt, 
            `${historyItem.style} • ${historyItem.model} • ${historyItem.size}`
        );
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
        this.currentImageIndex = 0;
        this.currentImageData = null;
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
            this.initializeUIState();
            
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

    initializeUIState() {
        // Hide save to history button initially
        const saveBtn = document.getElementById('saveToHistoryBtn');
        if (saveBtn) {
            saveBtn.style.display = 'none';
        }
        
        // Hide download all button initially
        const downloadAllBtn = document.getElementById('downloadAllBtn');
        if (downloadAllBtn) {
            downloadAllBtn.style.display = 'none';
        }
        
        // Hide results section initially
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
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

        // Save to history button (will be managed dynamically)
        const saveToHistoryBtn = document.getElementById('saveToHistoryBtn');
        if (saveToHistoryBtn) {
            saveToHistoryBtn.addEventListener('click', () => this.saveAllToHistory());
        }

        // Image modal event listeners
        this.initializeImageModal();
        
        // Floating navigation button
        this.initializeFloatingNav();
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
        // Check if button is disabled (premium required)
        if (button.disabled || button.classList.contains('premium-required')) {
            console.log('❌ Cannot select disabled variant button');
            
            // Show upgrade message
            this.showError('This feature requires a premium account. Please upgrade to generate multiple images.');
            return;
        }
        
        const variants = parseInt(button.dataset.variants);
        const maxImages = AppState.permissions.max_images_per_request || 2;
        
        // Double check permission limit
        if (variants > maxImages) {
            console.log(`❌ Variant ${variants} exceeds limit of ${maxImages}`);
            this.showError(`You can generate up to ${maxImages} images per request. ${maxImages === 1 ? 'Upgrade to Premium for more!' : ''}`);
            return;
        }
        
        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        this.selectedVariants = variants;
        
        console.log(`✅ Selected ${variants} image variant`);
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

        // Show loading overlay with progress animation
        this.showProgressOverlay();

        // Scroll to progress bar to show generation in progress
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

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
                this.currentImageData = data; // Store full generation data
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
            // Hide loading overlay
            this.hideProgressOverlay();
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
        
        // Store current generation data for batch save
        this.currentGeneration = data;

        data.images.forEach((imageUrl, index) => {
            const imageItem = document.createElement('div');
            imageItem.className = 'result-item';
            imageItem.innerHTML = `
                <img src="${imageUrl}" alt="Generated image ${index + 1}" class="result-image" loading="lazy" data-index="${index}">
                <div class="result-content">
                    <div class="result-actions">
                        <button class="result-btn download" onclick="app.downloadImage('${imageUrl}', ${index})" title="Download image">
                            <i class="fas fa-download"></i> Download
                        </button>
                        <button class="result-btn share" onclick="app.shareImage('${imageUrl}')" title="Share image">
                            <i class="fas fa-share"></i> Share
                        </button>
                    </div>
                </div>
            `;
            
            // Add click handler to image for viewer
            const img = imageItem.querySelector('.result-image');
            img.addEventListener('click', () => {
                this.openImageViewer(data.images, index, {
                    prompt: data.prompt,
                    size: data.size,
                    style: data.style,
                    model: data.model || 'DALL-E 3'
                });
            });
            
            imagesGrid.appendChild(imageItem);
        });

        // Show results section
        document.getElementById('resultsSection').style.display = 'block';
        
        // Update the Save to History button in the header
        this.updateSaveToHistoryButton(data.images.length);
    }

    saveAllToHistory() {
        if (!this.currentGeneration) {
            this.showError('No images to save');
            return;
        }

        const data = this.currentGeneration;
        const baseTimestamp = Date.now();
        
        // Save each image as a separate history item
        data.images.forEach((imageUrl, index) => {
            const historyItem = {
                id: baseTimestamp + index,
                timestamp: new Date().toISOString(),
                prompt: data.prompt,
                style: data.style,
                model: data.model || 'DALL-E 3',
                size: data.size,
                imageUrl: imageUrl,
                imageIndex: index + 1,
                totalImages: data.images.length,
                type: 'individual' // Mark as individual image
            };

            AppState.history.unshift(historyItem);
        });
        
        // Keep only last 100 individual images
        if (AppState.history.length > 100) {
            AppState.history = AppState.history.slice(0, 100);
        }

        this.saveHistory();
        this.renderHistory();
        this.showNotification(`Saved ${data.images.length} images to history!`, 'success');
        
        // Hide the save button after saving
        const saveBtn = document.getElementById('saveToHistoryBtn');
        if (saveBtn) {
            saveBtn.style.display = 'none';
        }
    }

    updateSaveToHistoryButton(imageCount) {
        const saveBtn = document.getElementById('saveToHistoryBtn');
        const downloadAllBtn = document.getElementById('downloadAllBtn');
        
        if (saveBtn) {
            saveBtn.style.display = 'inline-flex';
            saveBtn.innerHTML = `
                <i class="fas fa-save"></i>
                Save to History (${imageCount})
            `;
            saveBtn.onclick = () => this.saveAllToHistory();
        }
        
        // Show download all button only when not in Telegram
        if (downloadAllBtn) {
            if (!this.isInTelegram() && imageCount > 1) {
                downloadAllBtn.style.display = 'inline-flex';
                downloadAllBtn.innerHTML = `
                    <i class="fas fa-download"></i>
                    Download All (${imageCount})
                `;
                downloadAllBtn.onclick = () => this.downloadAllImages();
            } else {
                downloadAllBtn.style.display = 'none';
            }
        }
    }

    addToHistory(data) {
        // For backward compatibility - this method no longer auto-saves
        // Only saves when user explicitly clicks Save to History
        this.currentGeneration = data;
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
            historyGrid.className = 'history-grid empty-history';
            historyGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-images"></i>
                    <h3>No history yet</h3>
                    <p>Your generated images will appear here</p>
                </div>
            `;
            return;
        }

        historyGrid.className = 'history-grid';
        historyGrid.innerHTML = '';
        
        AppState.history.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            
            // Handle both old and new formats
            const imageUrl = item.imageUrl || (item.images && item.images[0]) || '';
            const isIndividual = item.type === 'individual' || item.imageUrl;
            
            historyItem.innerHTML = `
                <img class="history-image" src="${imageUrl}" alt="Generated image" loading="lazy" data-id="${item.id}">
                <div class="history-content">
                    <div class="history-info">
                        <div class="history-prompt">${item.prompt.substring(0, 60)}${item.prompt.length > 60 ? '...' : ''}</div>
                        <div class="history-date">${new Date(item.timestamp).toLocaleDateString()}</div>
                        ${item.totalImages > 1 ? `<div class="image-count">${item.imageIndex} of ${item.totalImages}</div>` : ''}
                    </div>
                    <div class="history-actions">
                        <button class="history-btn download" onclick="app.downloadSingleFromHistory(${item.id})" title="Download image">
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="history-btn share" onclick="app.shareImage('${imageUrl}')" title="Share image">
                            <i class="fas fa-share"></i>
                        </button>
                        <button class="history-btn delete" onclick="app.deleteFromHistory(${item.id})" title="Delete from history">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
            
            // Add click handler to image for viewer with navigation
            const img = historyItem.querySelector('.history-image');
            img.addEventListener('click', () => {
                this.openHistoryImageViewer(item.id);
            });
            
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

    downloadSingleFromHistory(id) {
        const historyItem = AppState.history.find(item => item.id === id);
        if (!historyItem) return;
        
        const imageUrl = historyItem.imageUrl || (historyItem.images && historyItem.images[0]);
        if (imageUrl) {
            this.downloadImage(imageUrl, 0);
        }
    }

    async downloadAllFromHistory(id) {
        const historyItem = AppState.history.find(item => item.id === id);
        if (!historyItem) return;
        
        const images = historyItem.images || [historyItem.imageUrl];
        
        if (this.isInTelegram()) {
            // In Telegram: Open all in new tabs
            images.forEach((imageUrl, index) => {
                setTimeout(() => {
                    window.open(imageUrl, '_blank');
                }, index * 500);
            });
            this.showNotification(`Opening ${images.length} image${images.length > 1 ? 's' : ''} in new tabs...`, 'success');
        } else {
            // In browser: Download all
            this.showNotification(`Starting download of ${images.length} image${images.length > 1 ? 's' : ''}...`, 'success');
            
            for (let i = 0; i < images.length; i++) {
                setTimeout(() => {
                    this.downloadImage(images[i], i);
                }, i * 500);
            }
        }
    }

    deleteFromHistory(id) {
        if (confirm('Are you sure you want to delete this image from history?')) {
            AppState.history = AppState.history.filter(h => h.id !== id);
            this.saveHistory();
            this.renderHistory();
            this.showNotification('Image deleted from history', 'success');
        }
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear all history?')) {
            AppState.history = [];
            this.saveHistory();
            this.renderHistory();
            this.showNotification('History cleared successfully', 'success');
        }
    }

    clearAllData() {
        if (confirm('Are you sure you want to clear all saved data? This cannot be undone.')) {
            localStorage.clear();
            AppState.history = [];
            this.renderHistory();
            this.showNotification('All data cleared successfully', 'success');
        }
    }

    isInTelegram() {
        // Check if we're in Telegram environment more thoroughly
        return !!(window.Telegram && 
                 window.Telegram.WebApp && 
                 window.Telegram.WebApp.initData &&
                 window.Telegram.WebApp.initData.length > 0);
    }

    forceDownload(url, filename) {
        // Create a temporary anchor element for download
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        // Add to DOM
        document.body.appendChild(a);
        
        // Trigger download
        a.click();
        
        // Clean up
        document.body.removeChild(a);
    }

    async downloadImage(imageUrl, index) {
        const isInTelegram = this.isInTelegram();
        console.log('Download Image - isInTelegram:', isInTelegram, 'URL:', imageUrl);
        console.log('Telegram check - window.Telegram:', !!window.Telegram);
        console.log('WebApp:', !!(window.Telegram && window.Telegram.WebApp));
        console.log('InitData:', !!(window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData));
        
        if (isInTelegram) {
            // In Telegram: Open in new tab
            window.open(imageUrl, '_blank');
            this.showNotification('Image opened in new tab!', 'success');
        } else {
            // In browser: Force direct download
            try {
                // Method 1: Try fetch and blob download
                const response = await fetch(imageUrl, {
                    mode: 'cors',
                    headers: {
                        'Accept': 'image/*'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Fetch failed');
                }
                
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                
                // Force download with better filename
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = `advai-image-${Date.now()}-${index + 1}.jpg`;
                link.style.display = 'none';
                
                // Add to DOM, click, and remove
                document.body.appendChild(link);
                
                // Force click event
                if (link.click) {
                    link.click();
                } else {
                    // Fallback for older browsers
                    const clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: false
                    });
                    link.dispatchEvent(clickEvent);
                }
                
                document.body.removeChild(link);
                
                // Clean up
                setTimeout(() => {
                    window.URL.revokeObjectURL(downloadUrl);
                }, 100);
                
                this.showNotification('Image download started!', 'success');
                
            } catch (error) {
                console.error('Blob download failed, trying fallback:', error);
                
                // Method 2: Direct link approach with download attribute
                const link = document.createElement('a');
                link.href = imageUrl;
                link.download = `advai-image-${Date.now()}-${index + 1}.jpg`;
                link.style.display = 'none';
                link.setAttribute('download', `advai-image-${Date.now()}-${index + 1}.jpg`);
                
                document.body.appendChild(link);
                
                try {
                    link.click();
                    this.showNotification('Image download started!', 'success');
                } catch (clickError) {
                    console.error('Click download failed, opening in new tab:', clickError);
                    // Method 3: Last resort - open in new tab
                    window.open(imageUrl, '_blank');
                    this.showNotification('Image opened in new tab (download failed)', 'warning');
                }
                
                document.body.removeChild(link);
            }
        }
    }

    async downloadAllImages() {
        if (!this.currentGeneration || !this.currentGeneration.images) {
            this.showError('No images to download');
            return;
        }

        const images = this.currentGeneration.images;
        
        if (this.isInTelegram()) {
            // In Telegram: Open all in new tabs with delay
            images.forEach((imageUrl, index) => {
                setTimeout(() => {
                    window.open(imageUrl, '_blank');
                }, index * 500);
            });
            this.showNotification(`Opening ${images.length} images in new tabs...`, 'success');
        } else {
            // In browser: Download all with delay
            this.showNotification(`Starting download of ${images.length} images...`, 'success');
            
            for (let i = 0; i < images.length; i++) {
                setTimeout(() => {
                    this.downloadImage(images[i], i);
                }, i * 500); // Increased delay to 500ms for better handling
            }
        }
    }

    async shareImage(imageUrl) {
        if (navigator.share && this.authSystem.webApp) {
            try {
                await navigator.share({
                    title: 'AI Generated Image',
                    text: 'Check out this AI-generated image!',
                    url: imageUrl
                });
                this.showNotification('Image shared successfully!', 'success');
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
            this.showNotification('Image link copied to clipboard!', 'success');
        }).catch(() => {
            this.showNotification('Failed to copy link', 'error');
        });
    }

    showProgressOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        const progressFill = document.getElementById('progressFill');
        
        if (overlay) {
            // Reset progress bar
            if (progressFill) {
                progressFill.style.width = '0%';
                progressFill.style.animation = 'none';
                
                // Force reflow to restart animation
                progressFill.offsetHeight;
                
                // Start progress animation
                progressFill.style.animation = 'progress 2s ease-in-out infinite';
            }
            
            // Show overlay
            overlay.style.display = 'flex';
            
            // Simulate progress updates for better UX
            this.startProgressSimulation();
        }
    }

    hideProgressOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        const progressFill = document.getElementById('progressFill');
        
        if (overlay) {
            // Complete the progress bar first
            if (progressFill) {
                progressFill.style.animation = 'none';
                progressFill.style.width = '100%';
                progressFill.style.transition = 'width 0.3s ease';
            }
            
            // Hide overlay after a short delay
            setTimeout(() => {
                if (overlay) {
                    overlay.style.display = 'none';
                }
                if (progressFill) {
                    progressFill.style.width = '0%';
                    progressFill.style.transition = '';
                }
            }, 300);
        }
    }

    startProgressSimulation() {
        const progressFill = document.getElementById('progressFill');
        if (!progressFill) return;
        
        let progress = 0;
        const maxProgress = 85; // Don't go to 100% until completion
        const increment = Math.random() * 3 + 1; // Random increment between 1-4%
        
        const progressInterval = setInterval(() => {
            if (!AppState.isGenerating) {
                clearInterval(progressInterval);
                return;
            }
            
            progress += increment * (1 - progress / 100); // Slow down as we approach max
            progress = Math.min(progress, maxProgress);
            
            if (progressFill && progressFill.style.animation === 'none') {
                progressFill.style.width = `${progress}%`;
            }
            
            if (progress >= maxProgress) {
                clearInterval(progressInterval);
            }
        }, 200 + Math.random() * 300); // Random interval between 200-500ms
    }

    getAllHistoryImages() {
        const allImages = [];
        const imageDetails = [];
        
        AppState.history.forEach(item => {
            const imageUrl = item.imageUrl || (item.images && item.images[0]);
            if (imageUrl) {
                allImages.push(imageUrl);
                imageDetails.push({
                    prompt: item.prompt,
                    size: item.size,
                    style: item.style,
                    model: item.model || 'DALL-E 3',
                    date: item.timestamp,
                    generationId: item.id
                });
            }
        });
        
        return { allImages, imageDetails };
    }

    openHistoryImageViewer(selectedItemId) {
        const { allImages, imageDetails } = this.getAllHistoryImages();
        
        if (allImages.length === 0) {
            this.showError('No images in history');
            return;
        }
        
        // Find the starting index based on the selected item
        let startIndex = 0;
        for (let i = 0; i < imageDetails.length; i++) {
            if (imageDetails[i].generationId === selectedItemId) {
                startIndex = i;
                break;
            }
        }
        
        this.openImageViewer(allImages, startIndex, imageDetails[startIndex]);
    }

    // Image Viewer functionality
    openImageViewer(images, currentIndex = 0, details = {}) {
        // Ensure images is an array
        if (!Array.isArray(images)) {
            images = [images];
        }

        // Create or get the modal
        let modal = document.getElementById('imageModal');
        if (!modal) {
            this.createImageModal();
            modal = document.getElementById('imageModal');
        }

        // Store current image data
        this.currentModalData = {
            images: images,
            currentIndex: currentIndex,
            prompt: details.prompt || '',
            size: details.size || '',
            style: details.style || '',
            model: details.model || 'DALL-E 3',
            isHistoryViewer: details.date ? true : false,
            imageDetails: details.date ? this.getAllHistoryImages().imageDetails : null
        };

        // Update modal content
        this.updateModalImage();

        // Show modal
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
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
            document.body.style.overflow = '';
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

    initializeImageModal() {
        const modal = document.getElementById('imageModal');
        const modalClose = document.getElementById('modalClose');
        const modalPrev = document.getElementById('modalPrev');
        const modalNext = document.getElementById('modalNext');
        const modalDownload = document.getElementById('modalDownload');
        const modalShare = document.getElementById('modalShare');

        if (modalClose) {
            modalClose.addEventListener('click', () => this.closeImageViewer());
        }

        if (modalPrev) {
            modalPrev.addEventListener('click', () => this.navigateImage(-1));
        }

        if (modalNext) {
            modalNext.addEventListener('click', () => this.navigateImage(1));
        }

        if (modalDownload) {
            modalDownload.addEventListener('click', () => this.downloadCurrentImage());
        }

        if (modalShare) {
            modalShare.addEventListener('click', () => this.shareCurrentImage());
        }

        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeImageViewer();
                }
            });
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (modal && modal.classList.contains('active')) {
                switch (e.key) {
                    case 'Escape':
                        this.closeImageViewer();
                        break;
                    case 'ArrowLeft':
                        this.navigateImage(-1);
                        break;
                    case 'ArrowRight':
                        this.navigateImage(1);
                        break;
                }
            }
        });
    }

    initializeFloatingNav() {
        const floatingBtn = document.getElementById('floatingNavBtn');
        if (!floatingBtn) return;

        // Show/hide floating button based on scroll position
        window.addEventListener('scroll', () => {
            const generateBtn = document.getElementById('generateBtn');
            if (generateBtn) {
                const rect = generateBtn.getBoundingClientRect();
                const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
                
                floatingBtn.classList.toggle('visible', !isVisible);
            }
        });

        // Click to scroll to generate button
        floatingBtn.addEventListener('click', () => {
            const generateBtn = document.getElementById('generateBtn');
            if (generateBtn) {
                generateBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    navigateImage(direction) {
        if (!this.currentModalData || !this.currentModalData.images || this.currentModalData.images.length <= 1) return;

        const newIndex = this.currentModalData.currentIndex + direction;
        if (newIndex >= 0 && newIndex < this.currentModalData.images.length) {
            this.currentModalData.currentIndex = newIndex;
            this.updateModalImage();
        }
    }

    updateModalImage() {
        if (!this.currentModalData || !this.currentModalData.images) return;

        const modalImage = document.getElementById('modalImage');
        const modalCounter = document.getElementById('modalCounter');
        const modalPrev = document.getElementById('modalPrev');
        const modalNext = document.getElementById('modalNext');
        const modalPrompt = document.getElementById('modalPrompt');
        const modalSize = document.getElementById('modalSize');
        const modalStyle = document.getElementById('modalStyle');
        const modalModel = document.getElementById('modalModel');

        const currentImage = this.currentModalData.images[this.currentModalData.currentIndex];

        // Get current image details (for history viewer, use specific image details)
        let currentDetails;
        if (this.currentModalData.isHistoryViewer && this.currentModalData.imageDetails) {
            currentDetails = this.currentModalData.imageDetails[this.currentModalData.currentIndex];
        } else {
            currentDetails = {
                prompt: this.currentModalData.prompt,
                size: this.currentModalData.size,
                style: this.currentModalData.style,
                model: this.currentModalData.model
            };
        }

        if (modalImage) {
            modalImage.src = currentImage;
        }

        if (modalCounter) {
            modalCounter.textContent = `${this.currentModalData.currentIndex + 1} / ${this.currentModalData.images.length}`;
        }

        if (modalPrev) {
            modalPrev.style.display = this.currentModalData.images.length > 1 ? 'flex' : 'none';
            modalPrev.disabled = this.currentModalData.currentIndex <= 0;
        }

        if (modalNext) {
            modalNext.style.display = this.currentModalData.images.length > 1 ? 'flex' : 'none';
            modalNext.disabled = this.currentModalData.currentIndex >= this.currentModalData.images.length - 1;
        }

        if (modalPrompt) {
            modalPrompt.textContent = currentDetails.prompt || '';
        }

        if (modalSize) {
            modalSize.textContent = currentDetails.size || '';
        }

        if (modalStyle) {
            modalStyle.textContent = currentDetails.style || '';
        }

        if (modalModel) {
            modalModel.textContent = currentDetails.model || '';
        }
    }

    showNotification(message, type = 'success') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(n => n.remove());

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const icon = type === 'success' ? 'fa-check-circle' : 
                     type === 'error' ? 'fa-exclamation-circle' : 
                     'fa-info-circle';
        
        notification.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;

        // Add to DOM
        document.body.appendChild(notification);

        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);

        // Auto-hide after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
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