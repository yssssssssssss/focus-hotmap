# 这里是基于deepgaze3，但是隐藏了视线的动线，但在代码底层是考了视线的动线的，只是没有最后画出来
# 它还是会影响最后的结果，所以这里可能需要将"视线的动线"作为一个参数传入，这样才能更好的控制视线的动线，同时可以针对不同的场景来设置不同的动线，感觉会更加贴合需求一些
# 


import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import zoom
from scipy.special import logsumexp
import torch
from PIL import Image
from tqdm import tqdm
import cv2
import numpy as np
from matplotlib import cm

import deepgaze_pytorch

DEVICE = 'cuda'

# you can use DeepGazeI or DeepGazeIIE
model = deepgaze_pytorch.DeepGazeIII(pretrained=True).to(DEVICE)


x = '开机-6'


# 指定图片路径
image_path = f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}.png'  

# 打开图片并获取尺寸
pil_image = Image.open(image_path)
w, h = pil_image.size

# 将PIL图像转换为numpy数组
image = np.array(pil_image)
# 如果图片是灰度图，转换为RGB
if len(image.shape) == 2:
    image = np.stack([image, image, image], axis=2)
# 确保图片是RGB格式（如果是RGBA，去掉Alpha通道）
elif image.shape[2] == 4:
    image = image[:, :, :3]

# location of previous scanpath fixations in x and y (pixel coordinates), starting with the initial fixation on the image.
# 修改后的注视点历史
fixation_history_x = np.array([w // 4, 3 * w // 4, w // 4, 3 * w // 4])
fixation_history_y = np.array([h // 4, h // 4, 3 * h // 4, 3 * h // 4])

print("修改后的注视点横坐标:", fixation_history_x)
print("修改后的注视点纵坐标:", fixation_history_y)

# load precomputed centerbias log density (from MIT1003) over a 1024x1024 image
# you can download the centerbias from https://github.com/matthias-k/DeepGaze/releases/download/v1.0.0/centerbias_mit1003.npy
# alternatively, you can use a uniform centerbias via `centerbias_template = np.zeros((1024, 1024))`.
centerbias_template = np.load('D://project//dongdesign//test_data2//centerbias_mit1003.npy')
# rescale to match image size
centerbias = zoom(centerbias_template, (image.shape[0]/centerbias_template.shape[0], image.shape[1]/centerbias_template.shape[1]), order=0, mode='nearest')
# renormalize log density
centerbias -= logsumexp(centerbias)

image_tensor = torch.tensor([image.transpose(2, 0, 1)]).to(DEVICE)
centerbias_tensor = torch.tensor([centerbias]).to(DEVICE)
x_hist_tensor = torch.tensor([fixation_history_x[model.included_fixations]]).to(DEVICE)
y_hist_tensor = torch.tensor([fixation_history_y[model.included_fixations]]).to(DEVICE)

log_density_prediction = model(image_tensor, centerbias_tensor, x_hist_tensor, y_hist_tensor)

# 获取热力图数据
heatmap_data = log_density_prediction.detach().cpu().numpy()[0, 0]

# 设置matplotlib使用支持中文的字体
import matplotlib.font_manager as fm
# 尝试使用系统中常见的中文字体
try:
    # 尝试使用微软雅黑
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'NSimSun', 'FangSong', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
except:
    # 如果找不到中文字体，使用英文标题
    print("未找到合适的中文字体，将使用英文标题")

# 创建进度条
progress_bar = tqdm(total=6, desc="生成图像")  # 更新为6个任务

# 统一设置图片尺寸为800x800像素
dpi = 100  # 设置DPI
figsize = (8, 8)  # 8英寸 x 8英寸，在100 DPI下会生成800x800像素的图像

# 图1：原始图像
plt.figure(figsize=figsize, dpi=dpi)
plt.imshow(image)
plt.title('Original Image')  # 使用英文标题避免字体问题
plt.axis('off')
plt.tight_layout()
plt.savefig(f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}//original_image.png', bbox_inches='tight')
plt.close()
progress_bar.update(1)  # 更新进度条

# 图2：热力图
plt.figure(figsize=figsize, dpi=dpi)
plt.matshow(heatmap_data)  # 使用原来的颜色方式
plt.title('Attention Heatmap')  # 使用英文标题避免字体问题
plt.axis('off')
plt.colorbar(fraction=0.046, pad=0.04)
plt.tight_layout()
plt.savefig(f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}//attention_heatmap.png', bbox_inches='tight')
plt.close()
progress_bar.update(1)  # 更新进度条

# 图3：简单透明度重合的热力图
plt.figure(figsize=figsize, dpi=dpi)
plt.imshow(image)
plt.imshow(heatmap_data, alpha=0.5)  # 使用原来的颜色方式，添加半透明效果
plt.title('Simple Overlay')  # 使用英文标题避免字体问题
plt.axis('off')
plt.colorbar(fraction=0.046, pad=0.04, label='Attention Intensity')
plt.tight_layout()
plt.savefig(f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}//simple_overlay.png', bbox_inches='tight')
plt.close()
progress_bar.update(1)  # 更新进度条

# 图4：高级热力图重合 - 使用颜色映射和阈值处理
# 将热力图数据归一化到0-1范围
heatmap_normalized = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())

# 将热力图转换为彩色图像
heatmap_colored = cm.jet(heatmap_normalized)
heatmap_colored = (heatmap_colored[:, :, :3] * 255).astype(np.uint8)

# 将原始图像转换为numpy数组并确保是RGB格式
image_np = np.array(image)
if len(image_np.shape) == 2:  # 如果是灰度图
    image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
elif image_np.shape[2] == 4:  # 如果是RGBA
    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

# 调整热力图大小以匹配原始图像
heatmap_resized = cv2.resize(heatmap_colored, (image_np.shape[1], image_np.shape[0]))

# 创建掩码，只在热力图值较高的区域显示热力图
mask = heatmap_normalized > 0.3  # 阈值可以调整
mask = np.expand_dims(mask, axis=2)
mask = np.repeat(mask, 3, axis=2)

# 创建高亮边缘
kernel = np.ones((5,5), np.uint8)
mask_dilated = cv2.dilate(mask.astype(np.uint8), kernel, iterations=1)
mask_edge = mask_dilated - mask.astype(np.uint8)
mask_edge = mask_edge > 0

# 创建最终的叠加图像
overlay_image = np.where(mask, heatmap_resized, image_np)
# 在边缘处添加高亮
overlay_image = np.where(mask_edge, [255, 255, 0], overlay_image)  # 黄色边缘

# 显示并保存高级重合图
plt.figure(figsize=figsize, dpi=dpi)
plt.imshow(overlay_image)
plt.title('Enhanced Overlay')
plt.axis('off')
plt.tight_layout()
plt.savefig(f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}//enhanced_overlay.png', bbox_inches='tight')
plt.close()
progress_bar.update(1)  # 更新进度条

# 图5：类似示例图的效果 - 只显示热力图区域，其他部分为黑色
# 将热力图数据归一化到0-1范围
heatmap_normalized = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())

# 创建一个黑色背景图像
black_background = np.zeros_like(image_np)

# 创建透明度掩码 - 使用热力图值作为透明度
alpha_mask = heatmap_normalized.copy()
# 可以调整透明度的计算方式，使效果更明显
alpha_mask = np.power(alpha_mask, 10)  # 使用平方根增强低值区域的可见性
# 扩展为3通道
alpha_mask = np.expand_dims(alpha_mask, axis=2)
alpha_mask = np.repeat(alpha_mask, 3, axis=2)

# 将原图与黑色背景混合，使用热力图值作为透明度
spotlight_image = image_np * alpha_mask + black_background * (1 - alpha_mask)
spotlight_image = spotlight_image.astype(np.uint8)

# 显示并保存聚光灯效果图
plt.figure(figsize=figsize, dpi=dpi)
plt.imshow(spotlight_image)
plt.title('Spotlight Effect')
plt.axis('off')
plt.tight_layout()
plt.savefig(f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}//spotlight_effect.png', bbox_inches='tight')
plt.close()
progress_bar.update(1)  # 更新进度条

# 图6：三张图横向排布的完整图片（包含聚光灯效果图）
fig, axs = plt.subplots(1, 3, figsize=(24, 8), dpi=dpi)  # 横向排布3张图，总宽度为24英寸

# 左侧：原图
axs[0].imshow(image)
axs[0].set_title('Original Image')
axs[0].axis('off')

# 中间：热力图
heatmap_plot = axs[1].matshow(heatmap_data)
axs[1].set_title('Attention Heatmap')
axs[1].axis('off')
# 添加颜色条
plt.colorbar(heatmap_plot, ax=axs[1], fraction=0.046, pad=0.04)

# 右侧：聚光灯效果图
axs[2].imshow(spotlight_image)
axs[2].set_title('Spotlight Effect')
axs[2].axis('off')

# 调整布局并保存
plt.tight_layout()
plt.savefig(f'D://project//dongdesign//AB预测//AB预测data//openimg//{x}//combined_visualization.png', bbox_inches='tight')
plt.close()
progress_bar.update(1)  # 更新进度条

# 关闭进度条
progress_bar.close()
print("所有图像已保存完成！")
