let recognitionCurrentPage = 1;
let isRecognitionLoading = false;
let isLastRecognitionPage = false;

// 初始加载
loadRecognitions();

// 无限滚动
document.querySelector('.recognition-area').addEventListener('scroll', function(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && !isRecognitionLoading && !isLastRecognitionPage) {
        loadRecognitions();
    }
});

// 加载识别记录
function loadRecognitions() {
    if (isRecognitionLoading || isLastRecognitionPage) return;
    
    isRecognitionLoading = true;
    document.getElementById('recognition-loading').style.display = 'block';

    fetch(`/get_recognitions?page=${recognitionCurrentPage}&per_page=10`)
        .then(response => response.json())
        .then(data => {
            data.recognitions.forEach(recognition => {
                const record = createRecognitionRecord(recognition);
                document.getElementById('recognitionList').appendChild(record);
            });

            recognitionCurrentPage = data.current_page + 1;
            isLastRecognitionPage = data.current_page >= data.total_pages;
            isRecognitionLoading = false;
            document.getElementById('recognition-loading').style.display = 'none';
        })
        .catch(error => {
            console.error('加载失败:', error);
            isRecognitionLoading = false;
            document.getElementById('recognition-loading').style.display = 'none';
        });
}

// 创建识别记录
function createRecognitionRecord(recognition) {
    const record = document.createElement('div');
    record.className = 'table-row';
    record.dataset.id = recognition.record_id;
    
    const date = new Date(recognition.upload_date);
    const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    
    record.innerHTML = `
        <div class="table-cell">${recognition.record_id}</div>
        <div class="table-cell filename" title="${recognition.original_image_name}">${recognition.original_image_name}</div>
        <div class="table-cell">${recognition.work_layout || '未设置'}</div>
        <div class="table-cell">${formattedDate}</div>
        <div class="table-cell actions">
            <button class="edit-btn" title="编辑记录">
                <i class="fas fa-edit"></i>
            </button>
            <button class="delete-btn" title="删除记录">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    // 编辑按钮事件
    const editBtn = record.querySelector('.edit-btn');
    editBtn.addEventListener('click', () => {
        window.location.href = `/ocr_edit/${recognition.image_name}`;
    });
    
    // 删除按钮事件
    const deleteBtn = record.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', () => {
        deleteRecognition(recognition.record_id);
    });
    
    return record;
}

// 删除识别记录
async function deleteRecognition(recordId) {
    if (!confirm('确定要删除这条识别记录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/delete_recognition/${recordId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const record = document.querySelector(`[data-id="${recordId}"]`);
            record.remove();
            showToast('删除成功');
        } else {
            showToast('删除失败', 'error');
        }
    } catch (error) {
        console.error('删除失败:', error);
        showToast('删除失败', 'error');
    }
}