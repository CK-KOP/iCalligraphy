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
function handleCardClick() {
    const isSvg = $(this).find('.svg-container').length > 0;
    let content;

    if (isSvg) {
        content = {
            type: 'svg',
            data: $(this).find('.svg-container').html(),
            description: $(this).find('.collection-card-details p').text()
        };
    } else {
        content = {
            type: 'image',
            data: $(this).find('img').attr('src'),
            description: $(this).find('.collection-card-details p').text()
        };
    }

    selectedItems.push(content);
    updatePreviewStyle();
}

// 修改创建预览项的函数
function createPreviewItem(content) {
    const container = document.createElement('div');
    container.className = 'preview-character';
    
    // 计算等比例缩放后的宽度和高度
    const scaledWidth = baseSettings.width * scale;
    container.style.width = `${scaledWidth}px`;

    if (content.type === 'svg') {
        // 处理SVG内容
        let svgContent = content.data;
        
        // 移除所有背景相关属性
        svgContent = svgContent.replace(/style="[^"]*background[^"]*"/g, '');
        svgContent = svgContent.replace(/background[^;]*;/g, '');
        svgContent = svgContent.replace(/fill="white"/g, 'fill="none"');
        
        // 解析SVG并设置属性
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(svgContent, 'image/svg+xml');
        const svgElement = svgDoc.documentElement;
        
        if (svgElement) {
            // 确保SVG是等比例缩放的
            svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet');
            svgElement.style.width = '100%';
            svgElement.style.height = '100%';
            svgElement.style.background = 'none';
            
            // 移除所有子元素的背景
            const allElements = svgElement.getElementsByTagName('*');
            for (let elem of allElements) {
                elem.style.background = 'none';
            }
            
            container.innerHTML = svgElement.outerHTML;
        }
    } else {
        // 处理图片内容
        const img = document.createElement('img');
        img.src = content.data;
        img.alt = content.description;
        img.style.width = '100%';
        img.style.height = 'auto';
        img.style.objectFit = 'contain';
        container.appendChild(img);
    }

    // 添加点击删除功能
    container.addEventListener('click', function() {
        const index = selectedItems.indexOf(content);
        if (index > -1) {
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

// 处理保存
function handleSave() {
    const title = document.getElementById('titleInput').value.trim(); // 去除多余空格

    if (!title) {
        alert('字帖标题不能为空！');
        return; // 阻止提交
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