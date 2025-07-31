// 青空セレクト 共通JavaScript

// DOM要素が読み込まれたときに実行
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeCommonFeatures();
});

// ダークモード管理
function initializeTheme() {
    // 保存されたテーマを取得
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // テーマを設定
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    setTheme(theme);
    
    // ダークモードトグルボタンを作成
    createThemeToggle();
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    // ボタンのアイコンを更新
    updateThemeToggleIcon(theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function createThemeToggle() {
    // 既存のトグルボタンをチェック
    if (document.querySelector('.theme-toggle')) return;
    
    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.setAttribute('aria-label', 'テーマを切り替え');
    toggle.onclick = toggleTheme;
    
    document.body.appendChild(toggle);
    
    // 初期アイコンを設定
    const currentTheme = document.documentElement.getAttribute('data-theme');
    updateThemeToggleIcon(currentTheme);
}

function updateThemeToggleIcon(theme) {
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
        toggle.setAttribute('title', theme === 'dark' ? 'ライトモードに切り替え' : 'ダークモードに切り替え');
    }
}

// 共通機能の初期化
function initializeCommonFeatures() {
    initializeAnimations();
    initializeTooltips();
    initializeKeyboardNavigation();
}

// アニメーションの初期化
function initializeAnimations() {
    // Intersection Observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, {
        threshold: 0.1
    });

    // .animate-on-scroll クラスの要素にアニメーションを適用
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

// ツールチップの初期化
function initializeTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const text = event.target.getAttribute('data-tooltip');
    if (!text) return;

    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: var(--bg-secondary);
        color: var(--text-color);
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        white-space: nowrap;
        z-index: 10000;
        box-shadow: var(--shadow);
        pointer-events: none;
    `;

    document.body.appendChild(tooltip);

    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';

    event.target._tooltip = tooltip;
}

function hideTooltip(event) {
    if (event.target._tooltip) {
        event.target._tooltip.remove();
        delete event.target._tooltip;
    }
}

// キーボードナビゲーション
function initializeKeyboardNavigation() {
    document.addEventListener('keydown', (e) => {
        // Escキーで各種メニューを閉じる
        if (e.key === 'Escape') {
            closeAllMenus();
        }
        
        // Alt + D でダークモード切り替え
        if (e.altKey && e.key === 'd') {
            e.preventDefault();
            toggleTheme();
        }
    });
}

function closeAllMenus() {
    // モバイルメニューを閉じる
    const mobileMenu = document.getElementById('mobileMenu');
    const hamburger = document.querySelector('.hamburger');
    
    if (mobileMenu && mobileMenu.classList.contains('active')) {
        mobileMenu.classList.remove('active');
        if (hamburger) hamburger.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    // その他のメニューやモーダルを閉じる処理を追加可能
}

// API呼び出しのユーティリティ関数
async function apiCall(url, method = 'GET', data = null, requireAuth = true) {
    const headers = {
        'Content-Type': 'application/json',
    };

    if (requireAuth) {
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
    }

    const config = {
        method,
        headers,
    };

    if (data && method !== 'GET') {
        config.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, config);
        
        // トークンが期限切れの場合、リフレッシュを試行
        if (response.status === 401 && requireAuth) {
            const refreshed = await refreshToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${localStorage.getItem('access_token')}`;
                config.headers = headers;
                return await fetch(url, config);
            }
        }
        
        return response;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// トークンリフレッシュ
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;

    try {
        const response = await fetch('/api/auth/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken }),
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }

    // リフレッシュに失敗した場合、ログアウト
    logout();
    return false;
}

// ログアウト処理
async function logout() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (refreshToken) {
        try {
            await apiCall('/api/auth/logout/', 'POST', { refresh: refreshToken });
        } catch (error) {
            console.error('Logout API call failed:', error);
        }
    }
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/accounts/register-page/';
}

// 通知表示
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: 500;
        z-index: 10000;
        max-width: 300px;
        box-shadow: var(--shadow);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;

    // タイプに応じたスタイル
    switch (type) {
        case 'success':
            notification.style.background = 'var(--success-color)';
            notification.style.color = 'white';
            break;
        case 'error':
            notification.style.background = 'var(--error-color)';
            notification.style.color = 'white';
            break;
        case 'warning':
            notification.style.background = 'var(--warning-color)';
            notification.style.color = 'black';
            break;
        default:
            notification.style.background = 'var(--info-color)';
            notification.style.color = 'white';
    }

    document.body.appendChild(notification);

    // アニメーション
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);

    // 自動削除
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, duration);

    // クリックで削除
    notification.addEventListener('click', () => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    });
}

// フォームバリデーション
function validateForm(formElement) {
    const errors = [];
    const inputs = formElement.querySelectorAll('input[required], textarea[required], select[required]');

    inputs.forEach(input => {
        const value = input.value.trim();
        const label = input.previousElementSibling?.textContent || input.name;

        if (!value) {
            errors.push(`${label}は必須項目です`);
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }

        // メールアドレスの検証
        if (input.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                errors.push('有効なメールアドレスを入力してください');
                input.classList.add('error');
            }
        }

        // パスワードの検証
        if (input.type === 'password' && value && value.length < 8) {
            errors.push('パスワードは8文字以上で入力してください');
            input.classList.add('error');
        }
    });

    return errors;
}

// ローディング状態の管理
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        element.dataset.originalText = element.textContent;
        element.innerHTML = '<span class="loading-spinner"></span> 処理中...';
    } else {
        element.disabled = false;
        element.textContent = element.dataset.originalText || element.textContent;
        delete element.dataset.originalText;
    }
}

// スムーススクロール
function smoothScrollTo(target) {
    const element = typeof target === 'string' ? document.querySelector(target) : target;
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// デバウンス関数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// スロットル関数
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// エクスポート（モジュールとして使用する場合）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        setTheme,
        toggleTheme,
        apiCall,
        refreshToken,
        logout,
        showNotification,
        validateForm,
        setLoading,
        smoothScrollTo,
        debounce,
        throttle
    };
} 