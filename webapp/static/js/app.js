class ImageGeneratorApp {
    constructor() {
        this.currentTab = 'generate';
        this.generatedImages = [];
        this.history = this.loadHistory();
        this.settings = {
            size: '1024x1024',
            variants: 1,
            style: 'default',
            model: 'flux'
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadAppState(); // Load saved app state
        this.updateCharCount();
        this.loadHistoryGrid();
        this.updateActiveTab();
        this.toggleCustomSizeInputs(); // Initialize custom size inputs visibility
        this.initTheme(); // Initialize theme
        this.showLoading(false); // Ensure loading overlay is hidden on init
    }

    bindEvents() {
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Clear data button
        document.getElementById('clearDataBtn').addEventListener('click', () => {
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

        // Description textarea
        const description = document.getElementById('description');
        description.addEventListener('input', () => {
            this.updateCharCount();
            this.saveAppState();
        });



        // Settings
        document.getElementById('sizeSelect').addEventListener('change', (e) => {
            this.settings.size = e.target.value;
            this.toggleCustomSizeInputs();
            this.saveAppState();
        });

        // Custom size inputs
        document.getElementById('customWidth').addEventListener('input', () => {
            this.saveAppState();
        });

        document.getElementById('customHeight').addEventListener('input', () => {
            this.saveAppState();
        });

        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.selectVariants(btn.dataset.variants);
                this.saveAppState();
            });
        });

        document.getElementById('styleSelect').addEventListener('change', (e) => {
            this.settings.style = e.target.value;
            this.saveAppState();
        });

        document.getElementById('modelSelect').addEventListener('change', (e) => {
            this.settings.model = e.target.value;
            this.saveAppState();
        });

        // Generate button
        document.getElementById('generateBtn').addEventListener('click', () => {
            this.generateImages();
        });

        // Enhance prompt button
        document.getElementById('enhanceBtn').addEventListener('click', () => {
            this.enhancePrompt();
        });

        // Results actions
        document.getElementById('downloadAllBtn').addEventListener('click', () => {
            this.downloadAll();
        });

        document.getElementById('saveToHistoryBtn').addEventListener('click', () => {
            this.saveToHistory();
        });

        // History actions
        document.getElementById('clearHistoryBtn').addEventListener('click', () => {
            this.clearHistory();
        });

        document.getElementById('exportHistoryBtn').addEventListener('click', () => {
            this.exportHistory();
        });
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
        
        // Save app state
        this.saveAppState();
    }

    updateActiveTab() {
        const hash = window.location.hash.slice(1);
        if (hash && ['generate', 'history'].includes(hash)) {
            this.switchTab(hash);
        }
    }

    updateCharCount() {
        const description = document.getElementById('description');
        const charCount = document.querySelector('.textarea-overlay .char-count');
        const count = description.value.length;
        charCount.textContent = `${count}/500`;
        
        if (count > 450) {
            charCount.style.color = 'var(--warning-color)';
        } else if (count > 500) {
            charCount.style.color = 'var(--danger-color)';
        } else {
            charCount.style.color = 'var(--text-muted)';
        }
    }

    toggleCustomSizeInputs() {
        const customInputs = document.getElementById('customSizeInputs');
        const sizeSelect = document.getElementById('sizeSelect');
        
        if (sizeSelect.value === 'custom') {
            customInputs.style.display = 'grid';
        } else {
            customInputs.style.display = 'none';
        }
    }

    initTheme() {
        // Get saved theme or default to light
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Update theme toggle icon
        const themeToggle = document.getElementById('themeToggle');
        const icon = themeToggle.querySelector('i');
        
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
            themeToggle.title = 'Switch to light mode';
        } else {
            icon.className = 'fas fa-moon';
            themeToggle.title = 'Switch to dark mode';
        }
    }

    saveAppState() {
        try {
            const appState = {
                description: document.getElementById('description').value,
                settings: { ...this.settings },
                generatedImages: this.generatedImages,
                customSize: {
                    width: document.getElementById('customWidth').value,
                    height: document.getElementById('customHeight').value
                },
                currentTab: this.currentTab
            };
            localStorage.setItem('advai_app_state', JSON.stringify(appState));
        } catch (error) {
            console.error('Error saving app state:', error);
        }
    }

    loadAppState() {
        try {
            const saved = localStorage.getItem('advai_app_state');
            if (!saved) return;

            const appState = JSON.parse(saved);

            // Restore description
            if (appState.description) {
                document.getElementById('description').value = appState.description;
            }

            // Restore settings
            if (appState.settings) {
                this.settings = { ...this.settings, ...appState.settings };
                
                // Update UI elements
                document.getElementById('sizeSelect').value = this.settings.size;
                document.getElementById('styleSelect').value = this.settings.style;
                document.getElementById('modelSelect').value = this.settings.model;
                this.selectVariants(this.settings.variants);
            }

            // Restore custom size inputs
            if (appState.customSize) {
                document.getElementById('customWidth').value = appState.customSize.width || '';
                document.getElementById('customHeight').value = appState.customSize.height || '';
            }

            // Restore generated images
            if (appState.generatedImages && appState.generatedImages.length > 0) {
                this.generatedImages = appState.generatedImages;
                this.displayResults();
            }

            // Restore current tab
            if (appState.currentTab) {
                this.currentTab = appState.currentTab;
            }

        } catch (error) {
            console.error('Error loading app state:', error);
        }
    }

    clearAppState() {
        try {
            localStorage.removeItem('advai_app_state');
            
            // Reset form
            document.getElementById('description').value = '';
            document.getElementById('customWidth').value = '';
            document.getElementById('customHeight').value = '';
            
            // Reset settings
            this.settings = {
                size: '1024x1024',
                variants: 1,
                style: 'default',
                model: 'flux'
            };
            
            // Update UI
            document.getElementById('sizeSelect').value = this.settings.size;
            document.getElementById('styleSelect').value = this.settings.style;
            document.getElementById('modelSelect').value = this.settings.model;
            this.selectVariants(this.settings.variants);
            
            // Clear generated images
            this.generatedImages = [];
            document.getElementById('resultsSection').classList.remove('active');
            
            this.updateCharCount();
            this.toggleCustomSizeInputs();
            
            this.showNotification('App state cleared!', 'success');
        } catch (error) {
            console.error('Error clearing app state:', error);
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
                this.saveAppState();
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
        const description = document.getElementById('description').value.trim();
        
        if (!description) {
            this.showNotification('Please enter an image description', 'warning');
            return;
        }

        if (description.length > 500) {
            this.showNotification('Description is too long (max 500 characters)', 'error');
            return;
        }

        // Get size value (handle custom sizes)
        let sizeValue = this.settings.size;
        if (this.settings.size === 'custom') {
            const width = parseInt(document.getElementById('customWidth').value);
            const height = parseInt(document.getElementById('customHeight').value);
            
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
        formData.append('description', description);
        formData.append('size', sizeValue);
        formData.append('variants', this.settings.variants);
        formData.append('style', this.settings.style);
        formData.append('model', this.settings.model);



        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.generatedImages = data.images;
                this.displayResults();
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

        resultsGrid.innerHTML = '';

        this.generatedImages.forEach((image, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item fadeIn';
            resultItem.innerHTML = `
                <img src="${image.url}" alt="Generated image ${index + 1}" class="result-image">
                <div class="result-actions">
                    <button class="result-btn primary" onclick="app.downloadImage('${image.url}', ${index})">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="result-btn" onclick="app.shareImage('${image.url}')">
                        <i class="fas fa-share"></i> Share
                    </button>
                    <button class="result-btn" onclick="app.regenerateVariation('${image.url}')">
                        <i class="fas fa-magic"></i> Variation
                    </button>
                </div>
            `;
            resultsGrid.appendChild(resultItem);
        });

        resultsSection.classList.add('active');
        resultsSection.scrollIntoView({ behavior: 'smooth' });
        
        // Save app state after displaying results
        this.saveAppState();
    }

    showLoading(show) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        loadingOverlay.style.display = show ? 'flex' : 'none';

        if (show) {
            // Animate progress bar
            const progressFill = document.getElementById('progressFill');
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
        // This would regenerate a variation of the selected image
        this.showNotification('Variation generation coming soon!', 'info');
    }

    saveToHistory() {
        if (this.generatedImages.length === 0) {
            this.showNotification('No images to save', 'warning');
            return;
        }

        const description = document.getElementById('description').value.trim();
        const historyItem = {
            id: Date.now(),
            description: description,
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
    }

    loadHistory() {
        try {
            const saved = localStorage.getItem('advai_image_history');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Error loading history:', error);
            return [];
        }
    }

    saveHistory() {
        try {
            localStorage.setItem('advai_image_history', JSON.stringify(this.history));
        } catch (error) {
            console.error('Error saving history:', error);
        }
    }

    loadHistoryGrid() {
        const historyGrid = document.getElementById('historyGrid');
        historyGrid.innerHTML = '';

        if (this.history.length === 0) {
            historyGrid.innerHTML = `
                <div class="text-center text-muted" style="grid-column: 1 / -1; padding: 2rem;">
                    <i class="fas fa-history" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.3;"></i>
                    <p>No generation history yet</p>
                    <p>Generate some images to see them here!</p>
                </div>
            `;
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

            historyItem.addEventListener('click', () => {
                this.viewHistoryItem(item);
            });

            historyGrid.appendChild(historyItem);
        });
    }

    viewHistoryItem(item) {
        // Switch to generate tab and load the item
        this.switchTab('generate');
        
        // Load settings
        document.getElementById('description').value = item.description;
        document.getElementById('sizeSelect').value = item.settings.size;
        this.settings.size = item.settings.size;
        this.selectVariants(item.settings.variants);
        document.getElementById('styleSelect').value = item.settings.style;
        document.getElementById('modelSelect').value = item.settings.model || 'flux';
        this.settings.model = item.settings.model || 'flux';
        
        // Load images as results
        this.generatedImages = item.images;
        this.displayResults();
        
        this.updateCharCount();
        this.showNotification('History item loaded!', 'info');
    }

    clearHistory() {
        if (this.history.length === 0) {
            this.showNotification('History is already empty', 'info');
            return;
        }

        if (confirm('Are you sure you want to clear all history? This action cannot be undone.')) {
            this.history = [];
            this.saveHistory();
            this.loadHistoryGrid();
            this.showNotification('History cleared!', 'success');
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
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ImageGeneratorApp();
});

// Handle browser back/forward
window.addEventListener('popstate', (e) => {
    if (e.state && e.state.tab) {
        window.app.switchTab(e.state.tab);
    }
}); 