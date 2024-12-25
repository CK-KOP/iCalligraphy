// 集字展示相关的新代码
const searchInput = document.getElementById('searchInput');
const collectionGrid = document.getElementById('collectionGrid');
const addCollectionBtn = document.getElementById('add-collection-btn');
const addCollectionModal = document.getElementById('add-collection-modal');
const loading = document.getElementById('loading');

let currentPage = 1;
let isLoading = false;
let isLastPage = false;

// 初始加载
loadCollectionImages();

// 搜索功能
searchInput.addEventListener('input', debounce(function() {
    resetCollection();
    loadCollectionImages();
}, 300));

// 无限滚动
document.querySelector('.collection-area').addEventListener('scroll', function(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && !isLoading && !isLastPage) {
        loadCollectionImages();
    }
});

// 加载集字图片
function loadCollectionImages() {
    if (isLoading || isLastPage) return;
    
    isLoading = true;
    loading.style.display = 'block';

    fetch(`/get_collection_images?library=personal&search=${encodeURIComponent(searchInput.value)}&page=${currentPage}&per_page=50`)
        .then(response => response.json())
        .then(data => {
            data.images.forEach(image => {
                const card = createCollectionCard(image);
                collectionGrid.appendChild(card);
            });

            currentPage = data.current_page + 1;
            isLastPage = data.current_page >= data.total_pages;
            isLoading = false;
            loading.style.display = 'none';
        })
        .catch(error => {
            console.error('加载失败:', error);
            isLoading = false;
            loading.style.display = 'none';
        });
}

// 创建集字卡片
function createCollectionCard(image) {
    const card = document.createElement('div');
    card.className = 'collection-card';
    card.dataset.id = image.id;

    let imageContent;
    if (image.is_svg) {
        imageContent = `
            <div class="svg-container">
                ${image.svg}
            </div>`;
    } else {
        imageContent = `
            <div class="img-container">
                <img src="${image.image_url}" alt="${image.description}" />
            </div>`;
    }
    
    card.innerHTML = `
        ${imageContent}
        <div class="collection-card-details">
            <p>${image.description}</p>
        </div>
        <div class="card-actions">
            <button class="delete-btn" title="删除集字">
                <i class="fas fa-trash"></i> 删除
            </button>
        </div>
    `;
    
    // 为删除按钮绑定事件
    const deleteBtn = card.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // 防止触发卡片的点击事件
        console.log('删除集字:', image.id);
        deleteCollection(image.id); // 删除操作
    });

    return card;
}

// 删除集字
async function deleteCollection(imageId) {
    if (!confirm('确定要删除这个集字吗？')) {
        return;
    }

    try {
        const response = await fetch(`/delete_collection/${imageId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // 从界面上移除该卡片
            const card = document.querySelector(`[data-id="${imageId}"]`);
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

// 重置集字展示
function resetCollection() {
    collectionGrid.innerHTML = '';
    currentPage = 1;
    isLastPage = false;
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

// 添加新集字相关功能
addCollectionBtn.addEventListener('click', () => {
    addCollectionModal.style.display = 'flex';
});

// 图片预览
document.getElementById('collection-image').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('collection-preview').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
});

// 提交新集字
document.getElementById('add-collection-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('image', document.getElementById('collection-image').files[0]);
    formData.append('character', document.getElementById('collection-character').value);

    fetch('/add_collection', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addCollectionModal.style.display = 'none';
            resetCollection();
            loadCollectionImages();
            showToast('添加成功');
        } else {
            console.error('添加失败:', data.message);
            showToast(data.message || '添加失败', 'error');
        }
    })
    .catch(error => {
        console.error('添加失败:', error);
        showToast('添加失败', 'error');
    });
});

