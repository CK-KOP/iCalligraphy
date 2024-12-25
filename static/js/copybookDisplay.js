// 字帖展示相关的代码
const copybookSearchInput = document.getElementById('copybookSearchInput');
const copybookGrid = document.getElementById('copybookGrid');
const addCopybookBtn = document.getElementById('add-copybook-btn');
const copybookLoading = document.getElementById('copybook-loading');
const imageModal = document.getElementById('image-preview-modal');

let copybookCurrentPage = 1;
let isCopybookLoading = false;
let isLastCopybookPage = false;

// 初始加载
loadCopybooks();

// 搜索功能
copybookSearchInput.addEventListener('input', debounce(function() {
    resetCopybooks();
    loadCopybooks();
}, 300));

// 无限滚动
document.querySelector('.copybook-area').addEventListener('scroll', function(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && !isCopybookLoading && !isLastCopybookPage) {
        loadCopybooks();
    }
});

// 加载字帖
function loadCopybooks() {
    if (isCopybookLoading || isLastCopybookPage) return;
    
    isCopybookLoading = true;
    copybookLoading.style.display = 'block';

    fetch(`/get_copybooks?search=${encodeURIComponent(copybookSearchInput.value)}&page=${copybookCurrentPage}&per_page=50`)
        .then(response => response.json())
        .then(data => {
            data.copybooks.forEach(copybook => {
                const card = createCopybookCard(copybook);
                copybookGrid.appendChild(card);
            });

            copybookCurrentPage = data.current_page + 1;
            isLastCopybookPage = data.current_page >= data.total_pages;
            isCopybookLoading = false;
            copybookLoading.style.display = 'none';
        })
        .catch(error => {
            console.error('加载失败:', error);
            isCopybookLoading = false;
            copybookLoading.style.display = 'none';
        });
}

// 创建字帖卡片
function createCopybookCard(copybook) {
    const card = document.createElement('div');
    card.className = 'collection-card';
    card.dataset.id = copybook.copybook_id;
    
    card.innerHTML = `
        <div class="img-container">
            <img src="${copybook.img_filepath}" alt="${copybook.title}" />
        </div>
        <div class="collection-card-details">
            <p class="copybook-title">${copybook.title}</p>
            <p class="copybook-date">${new Date(copybook.creation_date).toLocaleDateString()}</p>
            <div class="card-actions">
                <button class="delete-btn" title="删除字帖">
                    <i class="fas fa-trash"></i>删除
                </button>
            </div>
        </div>
    `;
    
    // 点击图片查看大图
    const imgContainer = card.querySelector('.img-container');
    imgContainer.addEventListener('click', () => {
        showImagePreview(copybook.img_filepath, copybook.title);
    });
    
    // 删除按钮事件
    const deleteBtn = card.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // 防止触发卡片的点击事件
        deleteCopybook(copybook.copybook_id);
    });
    
    return card;
}

// 显示大图预览
function showImagePreview(imageUrl, title) {
    imageModal.innerHTML = `
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>${title}</h2>
            <div class="preview-container">
                <img src="${imageUrl}" alt="${title}">
            </div>
        </div>
    `;
    
    imageModal.style.display = 'flex';
    
    // 关闭按钮事件
    const closeBtn = imageModal.querySelector('.close');
    closeBtn.onclick = () => {
        imageModal.style.display = 'none';
    };
    
    // 点击模态框外部关闭
    imageModal.onclick = (e) => {
        if (e.target === imageModal) {
            imageModal.style.display = 'none';
        }
    };
}

// 删除字帖
async function deleteCopybook(copybookId) {
    if (!confirm('确定要删除这个字帖吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/delete_copybook/${copybookId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // 从界面上移除该卡片
            const card = document.querySelector(`[data-id="${copybookId}"]`);
            card.remove();
            showToast('删除成功');
        } else {
            showToast('删除失败', 'error');
        }
    } catch (error) {
        console.error('删除失败:', error);
        showToast('删除失败', 'error');
    }
}

// 跳转到创建字帖页面（在父窗口的iframe中）
addCopybookBtn.addEventListener('click', () => {
    // 获取父窗口中的iframe元素
    const parentIframe = window.parent.document.querySelector('#main-content-iframe'); // 替换为实际的iframe ID
    if (parentIframe) {
        parentIframe.src = '/create_copybook';
    }
});