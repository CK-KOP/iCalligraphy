import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim  # 新增

def preprocess_image(image_path):
    # 读取和处理图像
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法读取图像：{image_path}")
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(
        gray_image, 128, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return binary_image

def align_image(image):
    # 图像对齐
    moments = cv2.moments(image)
    if moments['m00'] != 0:
        center_x = int(moments['m10'] / moments['m00'])
        center_y = int(moments['m01'] / moments['m00'])
    else:
        center_x, center_y = image.shape[1] // 2, image.shape[0] // 2

    h, w = image.shape
    transform_matrix = np.float32(
        [[1, 0, w // 2 - center_x], [0, 1, h // 2 - center_y]])
    aligned_image = cv2.warpAffine(image, transform_matrix, (w, h))
    return aligned_image

def normalize_image(image, target_size=(128, 128)):
    # 图像归一化
    h, w = image.shape
    scale_factor = min(target_size[0] / h, target_size[1] / w)
    new_size = (int(w * scale_factor), int(h * scale_factor))
    resized_image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    normalized_image = np.zeros(target_size, dtype=np.uint8)
    offset_x = (target_size[1] - new_size[0]) // 2
    offset_y = (target_size[0] - new_size[1]) // 2
    normalized_image[offset_y:offset_y + new_size[1],
                     offset_x:offset_x + new_size[0]] = resized_image

    return normalized_image

def sift_feature_matching(image1, image2):
    # SIFT特征匹配
    sift = cv2.SIFT_create()
    keypoints1, descriptors1 = sift.detectAndCompute(image1, None)
    keypoints2, descriptors2 = sift.detectAndCompute(image2, None)

    if descriptors1 is None or descriptors2 is None:
        return [], [], []  # 如果没有描述符，则返回空的结果

    # 使用BFMatcher替代FLANN以提高稳定性
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)

    # 应用Ratio Test来选取好的匹配
    good_matches = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:  # 调整阈值，从0.75降低到0.7
            good_matches.append(m)

    return keypoints1, keypoints2, good_matches

def template_matching_score(image1, image2):
    # 模板匹配得分
    resized_image1 = cv2.resize(image1, (128, 128))
    resized_image2 = cv2.resize(image2, (128, 128))
    result = cv2.matchTemplate(
        resized_image1, resized_image2, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    score = max_val * 100  # 将匹配值缩放到0-100
    score = min(max(score, 0), 100)  # 确保得分在0-100之间

    return score

def structural_similarity_score(image1, image2):
    # 结构相似性得分（SSIM）
    resized_image1 = cv2.resize(image1, (128, 128))
    resized_image2 = cv2.resize(image2, (128, 128))
    score, _ = ssim(resized_image1, resized_image2, full=True)
    score = score * 100  # 将得分缩放到0-100
    score = min(max(score, 0), 100)  # 确保得分在0-100之间
    return score

def combined_similarity(image_path1, image_path2):
    # 计算综合相似度
    image1 = preprocess_image(image_path1)
    image2 = preprocess_image(image_path2)
    aligned_image1 = align_image(image1)
    aligned_image2 = align_image(image2)
    normalized_image1 = normalize_image(aligned_image1)
    normalized_image2 = normalize_image(aligned_image2)

    # SIFT特征匹配得分
    keypoints1, keypoints2, good_matches = sift_feature_matching(
        normalized_image1, normalized_image2)

    if len(keypoints1) == 0 or len(keypoints2) == 0:
        sift_score = 0
    else:
        sift_score = (len(good_matches) / min(len(keypoints1), len(keypoints2))) * 100
        sift_score = min(sift_score, 100)  # 确保得分不超过100

    # 模板匹配得分
    template_score = template_matching_score(
        normalized_image1, normalized_image2)

    # 结构相似性得分（SSIM）
    ssim_score = structural_similarity_score(
        normalized_image1, normalized_image2)

    # 综合得分，调整权重
    # 可以根据测试结果调整权重，使得相同字的相似度更高
    combined_score = 0.3 * sift_score + 0.3 * template_score + 0.4 * ssim_score

    combined_score = min(max(combined_score, 0), 100)  # 确保总得分在0-100之间

    print(f"SIFT Score: {sift_score:.2f}%")
    print(f"Template Matching Score: {template_score:.2f}%")
    print(f"SSIM Score: {ssim_score:.2f}%")
    print(f"Combined Score: {combined_score:.2f}%")

    return sift_score, template_score, ssim_score, combined_score