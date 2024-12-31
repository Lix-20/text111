// 深色模式切换
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // 初始化主题
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme) {
        document.documentElement.setAttribute('data-bs-theme', currentTheme);
        updateThemeIcon(currentTheme);
    } else if (prefersDarkScheme.matches) {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        updateThemeIcon('dark');
    }

    // 主题切换事件
    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });
});

// 更新主题图标
function updateThemeIcon(theme) {
    const icon = document.querySelector('#theme-toggle i');
    icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
}

// 回到顶部按钮
const backToTop = document.getElementById('back-to-top');
window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        backToTop.style.display = 'block';
    } else {
        backToTop.style.display = 'none';
    }
});

backToTop.addEventListener('click', () => {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});

// 阅读进度条
const progressBar = document.querySelector('.reading-progress .progress-bar');
window.addEventListener('scroll', () => {
    const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
    const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (winScroll / height) * 100;
    progressBar.style.width = scrolled + '%';
});

// 图片懒加载
document.addEventListener('DOMContentLoaded', () => {
    const lazyImages = document.querySelectorAll('img.lazy');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    });

    lazyImages.forEach(img => imageObserver.observe(img));
});

// 文章分享功能
function shareArticle(title, url) {
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url
        }).catch(console.error);
    } else {
        // 复制链接到剪贴板
        navigator.clipboard.writeText(url).then(() => {
            alert('链接已复制到剪贴板！');
        }).catch(console.error);
    }
}
