let evaluationCurrentPage = 1;
let isEvaluationLoading = false;
let isLastEvaluationPage = false;

// 初始加载
loadEvaluations();

// 无限滚动
document.querySelector('.evaluation-area').addEventListener('scroll', function(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && !isEvaluationLoading && !isLastEvaluationPage) {
        loadEvaluations();
    }
});

// 加载评定记录
function loadEvaluations() {
    if (isEvaluationLoading || isLastEvaluationPage) return;
    
    isEvaluationLoading = true;
    document.getElementById('evaluation-loading').style.display = 'block';

    fetch(`/get_evaluations?page=${evaluationCurrentPage}&per_page=10`)
        .then(response => response.json())
        .then(data => {
            data.evaluations.forEach(evaluation => {
                const card = createEvaluationCard(evaluation);
                document.getElementById('evaluationList').appendChild(card);
            });

            evaluationCurrentPage = data.current_page + 1;
            isLastEvaluationPage = data.current_page >= data.total_pages;
            isEvaluationLoading = false;
            document.getElementById('evaluation-loading').style.display = 'none';
        })
        .catch(error => {
            console.error('加载失败:', error);
            isEvaluationLoading = false;
            document.getElementById('evaluation-loading').style.display = 'none';
        });
}

// 创建评定记录卡片
function createEvaluationCard(evaluation) {
    const card = document.createElement('div');
    card.className = 'evaluation-card';
    card.dataset.id = evaluation.evaluation_id;
    
    // 处理评定文本，将换行符转换为<br>标签
    const formattedText = evaluation.evaluation_text ? evaluation.evaluation_text.replace(/\n/g, '<br>') : '';
    
    card.innerHTML = `
        <div class="evaluation-content">
            <div class="evaluation-image">
                <img src="${evaluation.img_filepath}" alt="评定图片" />
            </div>
            <div class="evaluation-details">
                <div class="evaluation-date">${new Date(evaluation.upload_date).toLocaleString()}</div>
                <div class="evaluation-text">
                    <div class="evaluation-text-container">
                        <div class="evaluation-text-content">${formattedText}</div>
                        <div class="evaluation-text-mask"></div>
                    </div>
                    <div class="expand-btn">展开全文</div>
                </div>
                <div class="card-actions">
                    <button class="delete-btn" title="删除评定">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 获取相关元素
    const textContainer = card.querySelector('.evaluation-text-container');
    const textContent = card.querySelector('.evaluation-text-content');
    const expandBtn = card.querySelector('.expand-btn');
    const textMask = card.querySelector('.evaluation-text-mask');
    
    // 检查文本是否需要展开按钮
    setTimeout(() => {
        const needsExpansion = textContent.scrollHeight > textContainer.clientHeight;
        if (needsExpansion) {
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
    const img = card.querySelector('.evaluation-image img');
    img.addEventListener('click', () => {
        showImagePreview(evaluation.img_filepath, '评定图片');
    });
    
    // 删除按钮事件
    const deleteBtn = card.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', () => {
        deleteEvaluation(evaluation.evaluation_id);
    });
    
    return card;
}

// 删除评定记录
async function deleteEvaluation(evaluationId) {
    if (!confirm('确定要删除这条评定记录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/delete_evaluation/${evaluationId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const card = document.querySelector(`[data-id="${evaluationId}"]`);
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