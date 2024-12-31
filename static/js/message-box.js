// 消息盒子旋转控制
function rotateBox() {
    const box = document.querySelector('.message-box');
    box.classList.toggle('rotated');
}

// 加载最新消息预览
function loadMessagePreview() {
    const previewContainer = document.getElementById('message-preview');
    if (!previewContainer) return;

    fetch('/api/messages/recent')
        .then(response => response.json())
        .then(messages => {
            if (messages.length === 0) {
                previewContainer.innerHTML = `
                    <div class="empty-message">
                        <i class="fas fa-inbox"></i>
                        <p>暂无新消息</p>
                    </div>
                `;
                return;
            }

            const messageHtml = messages.slice(0, 3).map(msg => `
                <div class="message-item ${!msg.read ? 'unread' : ''}">
                    <div class="message-sender">
                        <i class="fas fa-user"></i>
                        ${msg.sender}
                    </div>
                    <div class="message-content">
                        ${msg.content.length > 30 ? msg.content.substring(0, 30) + '...' : msg.content}
                    </div>
                    <div class="message-time">
                        ${msg.timestamp}
                    </div>
                </div>
            `).join('');

            previewContainer.innerHTML = messageHtml;
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            previewContainer.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>加载消息时出错</p>
                </div>
            `;
        });
}

// 加载完整消息列表
function loadMessageList() {
    const listContainer = document.getElementById('message-list');
    if (!listContainer) return;

    fetch('/api/messages/unread')
        .then(response => response.json())
        .then(messages => {
            if (messages.length === 0) {
                listContainer.innerHTML = `
                    <div class="empty-message">
                        <i class="fas fa-inbox"></i>
                        <p>暂无未读消息</p>
                    </div>
                `;
                return;
            }

            const messageHtml = messages.map(msg => `
                <div class="message-item unread" data-message-id="${msg.id}">
                    <div class="message-sender">
                        <i class="fas fa-user"></i>
                        ${msg.sender}
                    </div>
                    <div class="message-content">
                        ${msg.content}
                    </div>
                    <div class="message-time">
                        ${msg.timestamp}
                    </div>
                </div>
            `).join('');

            listContainer.innerHTML = messageHtml;

            // 为每个消息项添加点击事件
            document.querySelectorAll('.message-item.unread').forEach(item => {
                item.addEventListener('click', function() {
                    const messageId = this.dataset.messageId;
                    markMessageAsRead(messageId);
                    this.classList.remove('unread');
                });
            });
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            listContainer.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>加载消息时出错</p>
                </div>
            `;
        });
}

// 标记消息为已读
function markMessageAsRead(messageId) {
    fetch(`/api/messages/mark_read/${messageId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 更新消息预览
                loadMessagePreview();
            }
        })
        .catch(error => console.error('Error marking message as read:', error));
}

// 添加鼠标悬停效果
document.addEventListener('DOMContentLoaded', function() {
    const box = document.querySelector('.message-box');
    if (!box) return;

    let startX;
    let isRotating = false;

    box.addEventListener('mouseenter', function(e) {
        if (!box.classList.contains('rotated')) {
            startX = e.clientX;
            isRotating = true;
        }
    });

    box.addEventListener('mousemove', function(e) {
        if (isRotating && !box.classList.contains('rotated')) {
            const currentX = e.clientX;
            const rotation = (currentX - startX) / 5;
            box.style.transform = `rotateY(${rotation}deg)`;
        }
    });

    box.addEventListener('mouseleave', function() {
        if (!box.classList.contains('rotated')) {
            isRotating = false;
            box.style.transform = 'rotateY(0deg)';
        }
    });

    // 初始加载消息
    loadMessagePreview();
    loadMessageList();

    // 设置定时刷新
    setInterval(loadMessagePreview, 60000); // 每分钟刷新一次
});
