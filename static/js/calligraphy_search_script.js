const loadingIndicator = document.getElementById('loadingIndicator'); // 获取加载提示
document.addEventListener('DOMContentLoaded', () => {
    // 初始化加载指示器状态
    hideLoadingIndicator(); // 隐藏加载指示器
    setupSearchHandlers();  // 设置搜索事件处理
    setupModal();           // 设置模态框事件处理
    
    // 手动触发 searchType 的 change 事件，模拟选择某个选项
    const searchType = document.getElementById('searchType');
    // 假设你希望在页面加载时选择 "calligraphy" 选项
    searchType.value = 'calligraphy';
    // 触发 change 事件，执行与该事件绑定的处理函数
    const event = new Event('change');
    searchType.dispatchEvent(event);
});

// 显示加载提示
function showLoadingIndicator() {
    loadingIndicator.classList.remove('loading-hidden');
}

// 隐藏加载提示
function hideLoadingIndicator() {
    loadingIndicator.classList.add('loading-hidden');
}

// 搜索处理相关函数
function setupSearchHandlers() {
    const searchButton = document.getElementById('searchButton');
    const searchInput = document.getElementById('searchInput');
    const searchType = document.getElementById('searchType');
    const resultsContainer = document.getElementById('resultsContainer'); // 获取结果显示区域
    // 获取整个容器元素
    const toggleContainer = document.querySelector('.toggle-container');
    const fontTypeToggle = document.getElementById('fontTypeToggle');

    // 监听下拉框选择变化事件
    searchType.addEventListener('change', () => {
        // 获取搜索数据
        console.log('当前选择的搜索类型：', searchType.value);
        const searchData = {
            type: searchType.value,
            query: searchInput.value, // 如果没有输入内容，保持为空
            fontType: fontTypeToggle.value
        };
        
        // 在发送请求之前清空结果区域并显示加载提示
        resultsContainer.innerHTML = ''; // 清空搜索结果
        showLoadingIndicator(); // 显示加载提示
        if(searchType.value === 'calligraphy')
            toggleContainer.classList.remove('hidden'); // 显示容器
        else
            toggleContainer.classList.add('hidden'); // 隐藏容器

        console.log('搜索数据：', searchData);

        // 发送数据到后端
        fetch('/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(searchData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // 使用后端返回的数据展示结果
            console.log('后端返回数据：', data);
            displayResults(searchData, data);

            // 隐藏加载提示
            hideLoadingIndicator();
        })
        .catch(error => {
            // 处理错误
            console.error('发生错误:', error);
            alert('显示时发生错误，请稍后重试。');

            // 隐藏加载提示
            hideLoadingIndicator();
        });
    });

    searchButton.addEventListener('click', () => {
        // 获取搜索数据
        const searchData = {
            type: searchType.value,
            query: searchInput.value,
            fontType: fontTypeToggle.value
        };

        // 在发送请求之前清空结果区域并显示加载提示
        resultsContainer.innerHTML = ''; // 清空搜索结果
        showLoadingIndicator(); // 显示加载提示

        console.log('搜索数据：', searchData);

        // 发送数据到后端
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(searchData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // 使用后端返回的数据展示结果
            console.log('后端返回数据：', data);
            displayResults(searchData, data);

            // 隐藏加载提示
            hideLoadingIndicator();
        })
        .catch(error => {
            // 处理错误
            console.error('发生错误:', error);
            alert('搜索时发生错误，请稍后重试。');

            // 隐藏加载提示
            hideLoadingIndicator();
        });
    });

    fontTypeToggle.addEventListener('change', function() {
        console.log("字体类型选择改变，重新搜索");
        // 如果搜索框为空，则触发 searchType 的 change 事件
        if (searchInput.value === '') {
            const event = new Event('change');
            searchType.dispatchEvent(event);  // 手动触发原生 JavaScript 事件
        } 
        else {
            // 否则触发搜索按钮的 click 事件
            const clickEvent = new MouseEvent('click');
            searchButton.dispatchEvent(clickEvent);  // 手动触发 click 事件
        }
    });

}

function displayResults(searchData, data) {
    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = ''; // 清空之前的结果

    const fragment = document.createDocumentFragment(); // 创建文档片段

    if (searchData.type === 'calligraphy') {
        data.forEach(item => {
            const card = createResultCard(item, 'calligraphy');
            fragment.appendChild(card);
        });
    } else {
        data.forEach(item => {
            const card = createResultCard(item, 'artwork');
            fragment.appendChild(card);
        });
    }

    resultsContainer.appendChild(fragment); // 一次性插入结果
}

function createResultCard(item, type) {
    const card = document.createElement('div');
    card.className = 'result-card';

    if (type === 'calligraphy') {
        const container = document.createElement('div');
        
        if (item.is_svg) {
            container.className = 'svg-container';
            container.innerHTML = item.svgContent;
        } else {
            container.className = 'img-container';
            const img = document.createElement('img');
            img.src = item.imageData;
            img.alt = item.info;
            container.appendChild(img);
        }
        
        const info = document.createElement('div');
        info.className = 'result-info';
        info.innerHTML = `<p>${item.info}</p>`;

        card.appendChild(container);
        card.appendChild(info);
    } else {
        // Artwork display logic remains unchanged
        const img = document.createElement('img');
        img.src = item.imageUrl;
        img.alt = '书法作品';

        const info = document.createElement('div');
        info.className = 'result-info';
        info.innerHTML = `
            <p>作品：${item.title}</p>
            <p>作者：${item.artist}</p>
            <p>朝代：${item.dynasty}</p>
            <p>收藏地：${item.location}</p>
        `;

        card.appendChild(img);
        card.appendChild(info);
    }

    card.addEventListener('click', () => {
        showModal(item, type);
    });

    return card;
}


// 模态框相关函数
function setupModal() {
    const modalContainer = document.getElementById('modalContainer');
    const closeButton = document.querySelector('.close-button');
    const downloadButton = document.getElementById('downloadButton');

    closeButton.addEventListener('click', () => {
        modalContainer.classList.add('hidden');
    });

    modalContainer.addEventListener('click', (e) => {
        if (e.target === modalContainer) {
            modalContainer.classList.add('hidden');
        }
    });

    // 下载按钮
    downloadButton.addEventListener('click', async () => {
        const modalContent = document.querySelector('.modal-content');
        const vectorId = modalContent.dataset.vectorId;
        const type = modalContent.dataset.type;
    
        if (type === 'calligraphy') {
            // SVG转PNG下载
            const svgContainer = document.querySelector('.modal-svg-container');
            const svgElement = svgContainer.querySelector('svg');
            
            // 创建Canvas
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            // 使用SVG的实际尺寸
            const svgWidth = svgElement.getAttribute('width') || svgElement.viewBox.baseVal.width;
            const svgHeight = svgElement.getAttribute('height') || svgElement.viewBox.baseVal.height;
            
            canvas.width = svgWidth;
            canvas.height = svgHeight;
            
            // 将SVG转换为图像
            const img = new Image();
            img.onload = () => {
                ctx.drawImage(img, 0, 0);
                
                // 转换为Blob并下载
                canvas.toBlob((blob) => {
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `calligraphy_${vectorId}.png`;
                    link.click();
                    URL.revokeObjectURL(url);
                }, 'image/png');
            };
            
            // 将SVG内容转为data URL
            const svgString = new XMLSerializer().serializeToString(svgElement);
            img.src = `data:image/svg+xml;base64,${btoa(svgString)}`;
        } 
        else {
            // 其他艺术作品直接下载
            const modalImg = document.getElementById('modalImage');
            if (modalImg && modalImg.src) {
                const link = document.createElement('a');
                link.href = modalImg.src;
                link.setAttribute('download', '书法作品.jpg'); // 设置下载的文件名
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                console.error('图片未找到或图片路径无效');
            }


        }
    });

}

function showModal(item, type) {
    const modal = document.getElementById('modalContainer');
    const modalContent = document.querySelector('.modal-content');
    const modalImg = document.getElementById('modalImage');
    const modalInfo = document.getElementById('modalInfo');
    const favoriteButton = document.getElementById('favoriteButton');

    // 清理之前的内容
    const existingSvgContainer = document.querySelector('.modal-svg-container');
    if (existingSvgContainer) {
        existingSvgContainer.remove();
    }
    modalImg.src = '';
    modalImg.style.display = 'none';

    modalContent.dataset.type = type;

    // 重置收藏按钮
    favoriteButton.replaceWith(favoriteButton.cloneNode(true));
    const newFavoriteButton = document.getElementById('favoriteButton');
    
    if (type === 'calligraphy') {
        modalContent.style.width = '50vw';
        modalContent.style.height = '80vh';
        modalContent.dataset.vectorId = item.vectorId;

        if (item.is_svg) {
            // SVG 显示处理
            const svgContainer = document.createElement('div');
            svgContainer.className = 'modal-svg-container';
            svgContainer.innerHTML = item.svgContent;
            svgContainer.style.width = '100%';
            svgContainer.style.height = '70vh';
            modalImg.parentElement.insertBefore(svgContainer, modalImg);
        } else {
            // 图片显示处理
            modalImg.style.display = 'block';
            modalImg.src = item.imageData;
            modalImg.style.width = 'auto';
            modalImg.style.height = '70vh';
            modalImg.style.objectFit = 'contain';
        }

        modalInfo.innerHTML = `<p>${item.info}</p>`;
        newFavoriteButton.style.display = 'block';

        // 添加收藏功能
        newFavoriteButton.addEventListener('click', async () => {
            newFavoriteButton.disabled = true;
            // 根据内容类型选择要保存的内容
            const contentToSave = item.is_svg ? item.svgContent : item.imageData;
            await addToFavourites(item.info, contentToSave, item.is_svg);
            newFavoriteButton.disabled = false;
        });
    } else {
        // 作品展示逻辑保持不变
        modalImg.style.display = 'block';
        modalImg.src = item.imageUrl;
        modalInfo.innerHTML = `
            <p>作品：${item.title}</p>
            <p>作者：${item.artist}</p>
            <p>朝代：${item.dynasty}</p>
            <p>收藏地：${item.location}</p>
        `;
        newFavoriteButton.style.display = 'none';
    }

    modal.classList.remove('hidden');
}

function createAlert(message, type = 'success') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    
    // 创建消息文本节点
    const messageText = document.createTextNode(message);
    alert.appendChild(messageText);
    
    // 创建关闭按钮
    const closeBtn = document.createElement('span');
    closeBtn.className = 'close-btn';
    closeBtn.innerHTML = '×';
    closeBtn.onclick = () => {
        alert.classList.add('fade-out');
        setTimeout(() => alert.remove(), 300);
    };
    alert.appendChild(closeBtn);
    
    // 获取现有的提示框来计算位置
    const existingAlerts = document.querySelectorAll('.alert');
    let topOffset = 20;
    
    existingAlerts.forEach(existing => {
        topOffset += existing.offsetHeight + 10; // 10px 是间距
    });
    
    alert.style.top = `${topOffset}px`;
    document.body.appendChild(alert);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alert.parentNode) {  // 检查元素是否仍在文档中
            alert.classList.add('fade-out');
            setTimeout(() => {
                if (alert.parentNode) {  // 再次检查，以防已被手动关闭
                    alert.remove();
                }
            }, 300);
        }
    }, 3000);
}


// 更新收藏功能以支持两种格式
async function addToFavourites(info, content, is_svg) {
    try {
        const response = await fetch('/add_favourite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                info: info,
                content: content,
                is_svg: is_svg
            })
        });

        const data = await response.json();
        if (response.ok) {
            alert('收藏成功！');
        } else {
            alert(data.error || '收藏失败，请重试');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('收藏失败，请重试');
    }
}