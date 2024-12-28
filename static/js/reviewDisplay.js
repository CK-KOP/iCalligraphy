// 检查是否为管理员并显示管理员tab
function checkAdminStatus() {
    fetch('/api/check_admin')
        .then(response => response.json())
        .then(data => {
            if (data.is_admin) {
                document.querySelectorAll('.admin-tab').forEach(el => el.style.display = '');
            }
        });
}

// 加载待审核字的函数
function loadReviewChars(search = '') {
    const reviewGrid = document.getElementById('reviewGrid');
    const loading = document.getElementById('review-loading');
    
    loading.style.display = 'block';
    
    // 构建查询参数
    const params = new URLSearchParams({
        search: search
    });
    
    fetch(`/api/get_review_chars?${params}`)
        .then(response => response.json())
        .then(data => {
            reviewGrid.innerHTML = '';
            if (data.chars.length === 0) {
                reviewGrid.innerHTML = '<div class="no-results">没有找到符合条件的字</div>';
                return;
            }
            
            data.chars.forEach(char => {
                const charElement = document.createElement('div');
                charElement.className = 'review-item';
                charElement.innerHTML = `
                    <img src="${char.image_path}" alt="${char.char}">
                    <div class="char-info">
                        <p>汉字: ${char.char}</p>
                        <p>作者: ${char.char_author}</p>
                        <p>字体: ${char.char_font}</p>
                        <p>来源: ${char.char_source}</p>
                        <p>上传者: ${char.uploader}</p>
                        <p>上传时间: ${new Date(char.upload_time).toLocaleString()}</p>
                    </div>
                    <div class="review-actions">
                        <button onclick="reviewChar(${char.id}, 'approve')" class="approve-btn">通过</button>
                        <button onclick="reviewChar(${char.id}, 'reject')" class="reject-btn">拒绝</button>
                    </div>
                `;
                reviewGrid.appendChild(charElement);
            });
        })
        .catch(error => {
            console.error('Error loading review chars:', error);
            reviewGrid.innerHTML = '<div class="error">加载失败，请刷新页面重试</div>';
        })
        .finally(() => {
            loading.style.display = 'none';
        });
}

// 处理审核决定
function reviewChar(charId, decision) {
    fetch(`/api/review_char/${charId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ decision })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadReviewChars(); // 重新加载待审核列表
            loadReviewHistory(); // 刷新审核历史
        }
    });
}

// 加载审核历史
function loadReviewHistory(page = 1, status = '', search = '') {
    const historyContainer = document.getElementById('reviewHistory');
    const loading = document.getElementById('history-loading');
    
    loading.style.display = 'block';

    const params = new URLSearchParams({
        page: page,
        per_page: 10,
        status: status,
        search: search
    });

    fetch(`/api/review_history?${params}`)
        .then(response => response.json())
        .then(data => {
            // 只更新表格和分页部分，不重置过滤器
            const tableContent = `
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>汉字</th>
                            <th>作者</th>
                            <th>字体</th>
                            <th>上传者</th>
                            <th>状态</th>
                            <th>时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.history.map(item => `
                            <tr>
                                <td>${item.char}</td>
                                <td>${item.char_author}</td>
                                <td>${item.char_font}</td>
                                <td>${item.uploader}</td>
                                <td>
                                    <span class="status-badge ${item.status}">
                                        ${item.status === 'approved' ? '已通过' : '已拒绝'}
                                    </span>
                                </td>
                                <td>${new Date(item.upload_time).toLocaleString()}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div class="pagination">
                    ${generatePagination(data.current_page, data.pages)}
                </div>
            `;
            historyContainer.innerHTML = tableContent;

            // 设置下拉选项和搜索框的值（保持用户选择）
            const statusFilter = document.getElementById('statusFilter');
            const searchInput = document.getElementById('historySearch');

            if (statusFilter) statusFilter.value = status;
            if (searchInput) searchInput.value = search;
        })
        .finally(() => {
            loading.style.display = 'none';
        });
}


// 生成分页控件
function generatePagination(currentPage, totalPages) {
    let pagination = '';
    
    if (currentPage > 1) {
        pagination += `<button onclick="loadReviewHistory(${currentPage - 1})">上一页</button>`;
    }
    
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        pagination += `
            <button class="${i === currentPage ? 'current' : ''}" 
                    onclick="loadReviewHistory(${i})">
                ${i}
            </button>
        `;
    }
    
    if (currentPage < totalPages) {
        pagination += `<button onclick="loadReviewHistory(${currentPage + 1})">下一页</button>`;
    }
    
    return pagination;
}

// 防抖函数
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

// 更新审核历史过滤器
function updateHistoryFilters() {
    const status = document.getElementById('statusFilter').value;
    const search = document.getElementById('historySearch').value;
    console.log('Updating history filters:', status, search);
    loadReviewHistory(1, status, search);
}

// 页面加载时的初始化
document.addEventListener('DOMContentLoaded', () => {
    checkAdminStatus();
    
    // 监听搜索输入
    const searchInput = document.getElementById('reviewSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => {
            loadReviewChars(searchInput.value.trim());
        }, 500));
    }
    
    // 监听tab切换
    document.getElementById('tab6').addEventListener('change', (e) => {
        if (e.target.checked) {
            // 清空搜索框并加载所有数据
            const searchInput = document.getElementById('reviewSearchInput');
            if (searchInput) {
                searchInput.value = '';
            }
            loadReviewChars();
            loadReviewHistory();
        }
    });
});