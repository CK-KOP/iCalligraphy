const postsGrid = document.getElementById('postsList');
const postsLoading = document.getElementById('posts-loading');

let postsCurrentPage = 1;
let isPostsLoading = false;
let isLastPostsPage = false;

// 初始加载
loadPosts();

// 无限滚动
document.querySelector('.posts-area').addEventListener('scroll', function(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && !isPostsLoading && !isLastPostsPage) {
        loadPosts();
    }
});

// 加载帖子
function loadPosts() {
    if (isPostsLoading || isLastPostsPage) return;
    
    isPostsLoading = true;
    postsLoading.style.display = 'block';

    fetch(`/posts?page=${postsCurrentPage}&size=50`)
        .then(response => response.json())
        .then(data => {
            if (data.posts && data.posts.length > 0) {
                data.posts.forEach(post => {
                    const card = createPostCard(post);
                    postsGrid.appendChild(card);
                });
                
                postsCurrentPage += 1;
                // 判断是否是最后一页
                if (data.posts.length < 10) {
                    isLastPostsPage = true;
                }
            } else {
                isLastPostsPage = true;
            }
            
            isPostsLoading = false;
            postsLoading.style.display = 'none';
        })
        .catch(error => {
            console.error('加载失败:', error);
            showToast('加载失败，请稍后重试');
            isPostsLoading = false;
            postsLoading.style.display = 'none';
        });
}

// 重置帖子列表
function resetPosts() {
    postsGrid.innerHTML = '';
    postsCurrentPage = 1;
    isLastPostsPage = false;
}


// 删除帖子
async function deletePost(postId) {
    if (!confirm('确定要删除这条帖子吗？')) {
        return;
    }
    
    try {
        console.log(`开始删除帖子，ID: ${postId}`);  // 调试信息
        const response = await fetch(`/delete_post/${postId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        console.log('服务器响应:', data);  // 调试信息
        
        if (data.code === 200) {
            const card = document.querySelector(`[data-id="${postId}"]`);
            if (card) {
                card.remove();
                showToast(data.message);
            } else {
                console.error('未找到要删除的卡片元素');  // 调试信息
            }
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        console.error('删除操作失败:', error);
        showToast('删除失败', 'error');
    }
}

// 创建帖子卡片
function createPostCard(post) {
    const card = document.createElement('div');
    card.className = 'post-card';
    card.dataset.id = post.post_id;
    
    // 处理帖子文本，将换行符转换为<br>标签
    const formattedText = post.content ? post.content.replace(/\n/g, '<br>') : '';
    const formattedDate = new Date(post.creation_date).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    card.innerHTML = `
        <div class="post-content">
            <div class="post-header">
                <div class="post-info">
                    <div class="post-author-name">${post.username}</div>
                    <div class="post-time">${formattedDate}</div>
                </div>
            </div>
            <div class="post-text">
                <div class="post-text-container">
                    <div class="post-text-content">${formattedText}</div>
                    <div class="post-text-mask"></div>
                </div>
                <div class="expand-btn">展开全文</div>
            </div>
            ${post.image_paths && post.image_paths.length > 0 ? `
                <div class="post-images">
                    ${post.image_paths.map(path => `
                        <div class="post-image">
                            <img src="${path}" alt="帖子图片" />
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            <div class="post-actions">
                <div class="action-stats">
                    <span class="like-count">
                        <i class="fas fa-heart"></i>
                        ${post.post_likes || 0}
                    </span>
                    <span class="comment-count">
                        <i class="fas fa-comment"></i>
                        ${post.post_comments || 0}
                    </span>
                </div>
                <div class="action-buttons">
                    <a href="/post_detail/${post.post_id}" class="enter-post-btn">
                        <i class="fas fa-arrow-right"></i>
                        进入帖子
                    </a>
                    <button class="delete-btn" title="删除帖子">
                        <i class="fas fa-trash"></i>
                        删除
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 获取相关元素
    const textContainer = card.querySelector('.post-text-container');
    const textContent = card.querySelector('.post-text-content');
    const expandBtn = card.querySelector('.expand-btn');
    const textMask = card.querySelector('.post-text-mask');
    
    // 给内容添加展开/收起功能
    setTimeout(() => {
        if (textContent.scrollHeight > textContainer.clientHeight) {
            expandBtn.style.display = 'block';
            textMask.style.display = 'block';
        }
    }, 0);
    
    // 展开/收起文本的点击事件
    expandBtn.addEventListener('click', () => {
        const isExpanded = textContainer.classList.contains('expanded');
        textContainer.classList.toggle('expanded');
        textMask.style.display = isExpanded ? 'block' : 'none';
        expandBtn.textContent = isExpanded ? '展开全文' : '收起';
    });
    
    // 点击图片查看大图
    const images = card.querySelectorAll('.post-image img');
    images.forEach(img => {
        img.addEventListener('click', () => {
            showImagePreview(img.src, '帖子图片');
        });
    });
    
     // 添加删除按钮事件
     const deleteBtn = card.querySelector('.delete-btn');
     deleteBtn.addEventListener('click', (e) => {
         e.stopPropagation(); // 防止触发卡片的点击事件
         deletePost(post.post_id);
     });
     
    return card;
}