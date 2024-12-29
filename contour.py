import cv2
import numpy as np

def extract_text_contours(input_image_path, output_image_path):
    """
    从输入图片中提取文字轮廓，并生成透明背景的图像。

    参数:
    - input_image_path: str，输入图片路径。
    - output_image_path: str，保存结果图片的路径。
    """
    # 读取图片
    image = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"无法读取图片，请检查路径是否正确: {input_image_path}")

    # 转为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 二值化处理
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 提取轮廓及其层级信息
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    # 创建一张透明背景的 RGBA 图像
    transparent_image = np.zeros((*image.shape[:2], 4), dtype=np.uint8)
    transparent_image[:, :, 3] = 0  # 初始化背景透明

    # 获取图像尺寸
    img_height, img_width = gray.shape[:2]

    # 遍历轮廓并绘制
    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        if w == img_width and h == img_height:  # 忽略整个图像的边框轮廓
            continue
        if hierarchy[0][i][3] == -1:  # 外轮廓
            cv2.drawContours(transparent_image, [contour], -1, (0, 0, 0, 255), thickness=cv2.FILLED)
        else:  # 内轮廓（空缺区域）
            cv2.drawContours(transparent_image, [contour], -1, (0, 0, 0, 0), thickness=cv2.FILLED)

    # 保存结果
    cv2.imwrite(output_image_path, transparent_image)
    print(f"处理完成，结果已保存到: {output_image_path}")

# if __name__ == "__main__":
#     input_image_path = "static/imgs/5.png"
#     output_image_path = "output.png"
#     extract_text_contours(input_image_path, output_image_path)