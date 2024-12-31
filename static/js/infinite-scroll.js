// 无限滚动加载
let page = 1;
let loading = false;
const postsContainer = document.querySelector('.posts-container');
const loadingSpinner = document.createElement('div');
loadingSpinner.className = 'loading-spinner';
loadingSpinner.innerHTML = `
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
`;

// 骨架屏模板
const skeletonTemplate = `
    <div class="card mb-4 post-card skeleton-card">
        <div class="card-body">
            <div class="skeleton-title"></div>
            <div class="skeleton-meta"></div>
            <div class="skeleton-text"></div>
            <div class="skeleton-text"></div>
            <div class="skeleton-text"></div>
            <div class="d-flex justify-content-between align-items-center mt-3">
                <div class="skeleton-button"></div>
                <div class="skeleton-stats"></div>
            </div>
        </div>
    </div>
`;

// 添加骨架屏
function addSkeletons() {
    const skeletons = document.createElement('div');
    for (let i = 0; i < 3; i++) {
        skeletons.innerHTML += skeletonTemplate;
    }
    postsContainer.appendChild(skeletons);
}

// 移除骨架屏
function removeSkeletons() {
    const skeletons = document.querySelectorAll('.skeleton-card');
    skeletons.forEach(skeleton => skeleton.remove());
}

// 加载更多文章
async function loadMorePosts() {
    if (loading) return;
    
    loading = true;
    page++;
    
    // 添加骨架屏
    addSkeletons();
    
    try {
        const response = await fetch(`/api/posts?page=${page}`);
        const data = await response.json();
        
        // 移除骨架屏
        removeSkeletons();
        
        if (data.posts.length === 0) {
            // 没有更多文章了
            const endMessage = document.createElement('div');
            endMessage.className = 'text-center text-muted my-4';
            endMessage.innerHTML = '没有更多文章了 ~';
            postsContainer.appendChild(endMessage);
            window.removeEventListener('scroll', handleScroll);
            return;
        }
        
        // 添加新文章
        data.posts.forEach(post => {
            const postElement = createPostElement(post);
            postsContainer.appendChild(postElement);
        });
        
        // 添加淡入动画
        const newPosts = document.querySelectorAll('.post-card:not(.fade-in)');
        newPosts.forEach(post => {
            post.classList.add('fade-in');
        });
        
    } catch (error) {
        console.error('Error loading posts:', error);
        const errorMessage = document.createElement('div');
        errorMessage.className = 'alert alert-danger';
        errorMessage.innerHTML = '加载失败，请稍后重试';
        postsContainer.appendChild(errorMessage);
    } finally {
        loading = false;
    }
}

// 创建文章元素
function createPostElement(post) {
    const div = document.createElement('div');
    div.className = 'card mb-4 post-card';
    div.innerHTML = `
        <div class="card-body">
            <h2 class="card-title">
                <a href="/post/${post.id}" class="text-decoration-none">
                    ${post.title}
                </a>
            </h2>
            <div class="card-meta mb-3">
                <span class="text-muted">
                    <i class="fas fa-clock me-1"></i>
                    ${post.date_posted}
                </span>
                ${post.category ? `
                    <span class="ms-3 text-muted">
                        <i class="fas fa-folder me-1"></i>
                        <a href="/category/${post.category_id}" class="text-decoration-none text-muted">
                            ${post.category_name}
                        </a>
                    </span>
                ` : ''}
            </div>
            <p class="card-text">${post.content}</p>
            <div class="d-flex justify-content-between align-items-center mt-3">
                <a href="/post/${post.id}" class="btn btn-primary">
                    阅读更多
                </a>
                <div class="post-stats">
                    <span class="me-3">
                        <i class="far fa-eye text-muted"></i>
                        <small class="text-muted">${post.views || 0}</small>
                    </span>
                    <span>
                        <i class="far fa-comment text-muted"></i>
                        <small class="text-muted">${post.comments_count || 0}</small>
                    </span>
                </div>
            </div>
        </div>
    `;
    return div;
}

// 滚动处理
function handleScroll() {
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 800) { // 提前800px开始加载
        loadMorePosts();
    }
}

// 初始化
window.addEventListener('scroll', handleScroll);
