/* globals $, html2canvas */

// DOM 元素
const searchInput = document.getElementById('searchInput');
const collectionGrid = document.getElementById('collectionGrid');
const libraryToggle = document.getElementById('libraryToggle');
const fontTypeToggle = document.getElementById('fontTypeToggle');

const loading = document.getElementById('loading');
const previewContainer = document.getElementById('previewContainer');

// 全局状态管理
let currentPage = 1;
let isLoading = false;
let isLastPage = false;
let currentLibrary = 'system';
let scale = 1;
const selectedItems = [];
const baseSettings = {
    width: 80,
    spacing: 10
};

// 页面加载初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log("页面已加载，开始加载默认字库");
    initializeEventListeners();
    loadCollectionImages(currentLibrary);
    $('#backgroundSelect').trigger('change');
});

// 初始化所有事件监听器
function initializeEventListeners() {
    // 字库切换监听
    libraryToggle.addEventListener('change', function() {
        currentLibrary = this.value;
        resetCollection();
        loadCollectionImages(currentLibrary);
    });
    
    fontTypeToggle.addEventListener('change', function() {
        resetCollection();
        loadCollectionImages(currentLibrary);
    });

    // 搜索功能
    searchInput.addEventListener('input', debounce(function() {
        resetCollection();
        loadCollectionImages(currentLibrary);
    }, 300));

    // 滚动加载
    collectionGrid.addEventListener('scroll', function() {
        const { scrollTop, scrollHeight, clientHeight } = this;
        if (scrollHeight - scrollTop - clientHeight < 200 && !isLoading && !isLastPage) {
            loadCollectionImages(currentLibrary);
        }
    });

    // 背景配置
    const backgrounds = {
        white: {
            type: 'image',
            value: '/static/images/backgrounds/white_paper.jpg',
            fallbackColor: '#ffffff'
        },
        xuan: {
            type: 'image',
            value: '/static/images/backgrounds/rice_paper.jpg',
            fallbackColor: '#f9f3e3'
        }
    };

    // 背景设置处理函数
    $('#backgroundSelect').change(function() {
        const selectedBackground = $(this).val();
        const colorPicker = $("#colorPicker");
        const previewContainer = document.getElementById('previewContainer');
        
        if (selectedBackground === 'custom') {
            // 自定义颜色模式
            colorPicker.show();
            previewContainer.style.backgroundImage = '';
            previewContainer.style.backgroundColor = colorPicker.val();
        } else {
            // 图片背景模式
            colorPicker.hide();
            const bg = backgrounds[selectedBackground];
            previewContainer.style.backgroundImage = `url(${bg.value})`;
            previewContainer.style.backgroundSize = 'cover';
            previewContainer.style.backgroundPosition = 'center';
            previewContainer.style.backgroundColor = bg.fallbackColor;
        }
    });

    // 颜色选择器更新
    $('#colorPicker').change(function() {
        const previewContainer = document.getElementById('previewContainer');
        previewContainer.style.backgroundImage = '';
        previewContainer.style.backgroundColor = this.value;
    });

    // 修改缩放控制函数
    $('#zoomIn').click(function() {
        scale = Math.min(5, scale + 0.1); // 限制最大缩放比例为5倍
        updatePreviewStyle();
    });

    $('#zoomOut').click(function() {
        scale = Math.max(0.1, scale - 0.1); // 限制最小缩放比例为0.1倍
        updatePreviewStyle();
    });

    $('#resetZoom').click(function() {
        scale = 1;
        updatePreviewStyle();
    });

    // 清空按钮
    $('#clearButton').click(function() {
        selectedItems.length = 0;
        $('#previewContainer').empty();
        updatePreviewStyle();
    });

    // 保存按钮
    $('#saveButton').click(handleSave);

    // 布局设置变更
    $('#rowsInput, #orderSelect, #spacingRange').on('change input', updatePreviewStyle);

    // 点击卡片添加到预览
    $(document).on('click', '.collection-card', handleCardClick);
}

// 加载字库图片
function loadCollectionImages(library) {
    if (isLoading || isLastPage) return;

    isLoading = true;
    loading.style.display = 'block';

    const searchQuery = encodeURIComponent(searchInput.value);
    const fontType = fontTypeToggle.value;
    fetch(`/get_collection_images?library=${library}&search=${searchQuery}&fontType=${fontType}&page=${currentPage}&per_page=50`)
        .then(response => response.json())
        .then(data => {
            data.images.forEach(image => {
                const card = createCollectionCard(image);
                collectionGrid.appendChild(card);
            });

            currentPage = data.current_page + 1;
            isLastPage = data.current_page >= data.total_pages;
        })
        .catch(error => {
            console.error('加载失败:', error);
        })
        .finally(() => {
            isLoading = false;
            loading.style.display = 'none';
        });
}

// 修改 createCollectionCard 函数
function createCollectionCard(image) {
    const card = document.createElement('div');
    card.className = 'collection-card';
    card.dataset.id = image.id;
    
    // 检查是否为个人字库
    const isPersonalLibrary = libraryToggle.value === 'personal';
    
    if (image.is_svg) {
        const svgContainer = document.createElement('div');
        svgContainer.className = 'svg-container';
        svgContainer.innerHTML = image.svg;
        card.appendChild(svgContainer);
    } else {
        const imgContainer = document.createElement('div');
        imgContainer.className = 'img-container';
        const img = document.createElement('img');
        img.src = image.image_url;
        img.alt = image.description || '';
        imgContainer.appendChild(img);
        card.appendChild(imgContainer);
    }

    const details = document.createElement('div');
    details.className = 'collection-card-details';
    details.innerHTML = `<p>${image.description || ''}</p>`;
    card.appendChild(details);

    return card;
}

// 处理卡片点击
async function handleCardClick() {
    const card = $(this);
    const cardId = card.data('id');
    const isSvg = card.find('.svg-container').length > 0;
    const isPersonalLibrary = libraryToggle.value === 'personal';
    
    try {
        if (isSvg) {
            // 处理SVG内容
            const content = {
                type: 'svg',
                data: card.find('.svg-container').html(),
                description: card.find('.collection-card-details p').text(),
                id: cardId,
                library: isPersonalLibrary ? 'personal' : 'system'
            };
            selectedItems.push(content);
            updatePreviewStyle();
        } else {
            // 显示加载指示器
            loading.style.display = 'block';
            
            // 发送图片处理请求
            const response = await fetch('/api/process_image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    character_id: cardId,
                    library_type: isPersonalLibrary ? 'personal' : 'system'
                })
            });

            if (!response.ok) {
                throw new Error('Image processing failed');
            }

            // 创建blob URL
            const blob = await response.blob();
            const processedImageUrl = URL.createObjectURL(blob);
            
            // 创建新的内容对象
            const content = {
                type: 'image',
                data: processedImageUrl,
                description: card.find('.collection-card-details p').text(),
                id: cardId,
                library: isPersonalLibrary ? 'personal' : 'system'
            };
            
            selectedItems.push(content);
            updatePreviewStyle();
        }
    } catch (error) {
        console.error('处理图片失败:', error);
        alert('处理图片失败，请重试');
    } finally {
        loading.style.display = 'none';
    }
}

// 修改createPreviewItem函数
function createPreviewItem(content) {
    const container = document.createElement('div');
    container.className = 'preview-character';
    container.dataset.id = content.id;
    container.dataset.library = content.library;
    
    // 计算等比例缩放后的宽度和高度
    const scaledWidth = baseSettings.width * scale;
    container.style.width = `${scaledWidth}px`;

    if (content.type === 'svg') {
        // SVG处理逻辑保持不变
        let svgContent = content.data;
        svgContent = svgContent.replace(/style="[^"]*background[^"]*"/g, '');
        svgContent = svgContent.replace(/background[^;]*;/g, '');
        svgContent = svgContent.replace(/fill="white"/g, 'fill="none"');
        
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(svgContent, 'image/svg+xml');
        const svgElement = svgDoc.documentElement;
        
        if (svgElement) {
            svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet');
            svgElement.style.width = '100%';
            svgElement.style.height = '100%';
            svgElement.style.background = 'none';
            
            const allElements = svgElement.getElementsByTagName('*');
            for (let elem of allElements) {
                elem.style.background = 'none';
            }
            
            container.innerHTML = svgElement.outerHTML;
        }
    } else {
        // 处理图片
        const img = document.createElement('img');
        img.src = content.data;
        img.alt = content.description;
        img.style.width = '100%';
        img.style.height = 'auto';
        img.style.objectFit = 'contain';
        container.appendChild(img);
    }

    // 添加点击删除功能，包括清理blob URL
    container.addEventListener('click', function() {
        const index = selectedItems.indexOf(content);
        if (index > -1) {
            if (content.type === 'image') {
                // 清理blob URL
                URL.revokeObjectURL(content.data);
            }
            selectedItems.splice(index, 1);
        }
        this.remove();
        updatePreviewStyle();
    });

    return container;
}

// 更新预览样式的函数
function updatePreviewStyle() {
    const rowCount = parseInt($('#rowsInput').val());
    const order = $('#orderSelect').val();
    baseSettings.spacing = parseInt($('#spacingRange').val());

    $('#previewContainer').empty();

    const columns = Math.ceil(selectedItems.length / rowCount);
    const groupedItems = Array.from({ length: columns }, (_, i) =>
        selectedItems.slice(i * rowCount, (i + 1) * rowCount)
    );

    const orderedColumns = order === 'rtl' ? groupedItems.reverse() : groupedItems;

    orderedColumns.forEach(group => {
        const column = document.createElement('div');
        column.className = 'column';
        
        // 设置列的样式
        const scaledWidth = baseSettings.width * scale;
        const scaledSpacing = baseSettings.spacing * scale;
        
        Object.assign(column.style, {
            width: `${scaledWidth}px`,
            gap: `${scaledSpacing}px`,
            marginRight: `${scaledSpacing}px`
        });

        group.forEach(item => {
            const previewItem = createPreviewItem(item);
            column.appendChild(previewItem);
        });

        previewContainer.appendChild(column);
    });

    // 更新缩放显示
    document.getElementById('zoomValue').textContent = `${Math.round(scale * 100)}%`;
}

// 修改handleSave函数以清理blob URLs
function handleSave() {
    const title = document.getElementById('titleInput').value.trim();

    if (!title) {
        alert('字帖标题不能为空！');
        return;
    }
    
    html2canvas(previewContainer, {
        scrollX: window.scrollX,
        scrollY: window.scrollY,
        useCORS: true
    }).then(canvas => {
        const imageData = canvas.toDataURL('image/png');
        
        fetch('/api/save_copybook', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                image: imageData
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('保存结果:', data);
            if (data.downloadUrl) {
                alert('字帖保存成功！');
                $('#downloadLink').html(
                    `<a href="${data.downloadUrl}" target="_blank" download>点击下载字帖</a>`
                );
                
                // 清理所有blob URLs
                selectedItems.forEach(item => {
                    if (item.type === 'image') {
                        URL.revokeObjectURL(item.data);
                    }
                });
            } else {
                alert('字帖保存成功，但未生成下载链接！');
            }
        })
        .catch(error => {
            console.error('保存失败:', error);
            alert('保存字帖失败，请重试！');
        });
    });
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
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}