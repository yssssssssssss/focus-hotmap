from flask import Flask, request, render_template, jsonify, send_from_directory
import os
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
import uuid
import deepgaze_pytorch
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，避免在服务器上显示图形

app = Flask(__name__)

# 配置上传文件夹 - 为Vercel调整路径
UPLOAD_FOLDER = '/tmp/uploads' if os.environ.get('VERCEL') else 'uploads'
RESULTS_FOLDER = '/tmp/results' if os.environ.get('VERCEL') else 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# 设置设备 - 在Vercel上只能使用CPU
DEVICE = 'cuda' if torch.cuda.is_available() and not os.environ.get('VERCEL') else 'cpu'

# 加载模型 - 在Vercel环境中延迟加载
model = None

def load_model():
    global model
    if model is None:
        model = deepgaze_pytorch.DeepGazeIII(pretrained=True).to(DEVICE)
    return model

# 加载中心偏置 - 为Vercel调整路径
centerbias_template = None

def get_centerbias():
    global centerbias_template
    if centerbias_template is None:
        try:
            # 在不同环境中尝试不同路径
            possible_paths = [
                'centerbias_mit1003.npy',
                os.path.join(os.path.dirname(__file__), 'centerbias_mit1003.npy'),
                '/tmp/centerbias_mit1003.npy'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    centerbias_template = np.load(path)
                    break
            
            # 如果所有路径都失败，创建一个均匀的中心偏置
            if centerbias_template is None:
                centerbias_template = np.zeros((1024, 1024))
                print("警告：未找到中心偏置文件，使用均匀中心偏置")
        except Exception as e:
            print(f"加载中心偏置时出错: {str(e)}")
            centerbias_template = np.zeros((1024, 1024))
    
    return centerbias_template

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 生成唯一ID作为文件夹名
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(app.config['RESULTS_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)
    
    # 保存上传的文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{file.filename}")
    file.save(file_path)
    
    # 处理图像
    try:
        result_paths = process_image(file_path, session_folder)
        return jsonify({
            'success': True,
            'session_id': session_id,
            'result_paths': result_paths
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_image(image_path, output_folder):
    # 确保模型已加载
    model = load_model()
    
    # 获取中心偏置
    centerbias_template = get_centerbias()
    
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

    # 设置注视点历史 - 可以根据需要调整或从前端获取
    fixation_history_x = np.array([w // 4, 3 * w // 4, w // 4, 3 * w // 4])
    fixation_history_y = np.array([h // 4, h // 4, 3 * h // 4, 3 * h // 4])

    # 调整中心偏置大小
    centerbias = zoom(centerbias_template, (image.shape[0]/centerbias_template.shape[0], image.shape[1]/centerbias_template.shape[1]), order=0, mode='nearest')
    # 重新归一化对数密度
    centerbias -= logsumexp(centerbias)

    # 准备模型输入
    image_tensor = torch.tensor([image.transpose(2, 0, 1)]).to(DEVICE)
    centerbias_tensor = torch.tensor([centerbias]).to(DEVICE)
    x_hist_tensor = torch.tensor([fixation_history_x[model.included_fixations]]).to(DEVICE)
    y_hist_tensor = torch.tensor([fixation_history_y[model.included_fixations]]).to(DEVICE)

    # 获取模型预测
    log_density_prediction = model(image_tensor, centerbias_tensor, x_hist_tensor, y_hist_tensor)
    heatmap_data = log_density_prediction.detach().cpu().numpy()[0, 0]

    # 统一设置图片尺寸
    dpi = 100
    figsize = (8, 8)
    
    # 保存结果图像
    result_paths = {}
    
    # 图1：原始图像
    plt.figure(figsize=figsize, dpi=dpi)
    plt.imshow(image)
    plt.title('原始图像')
    plt.axis('off')
    plt.tight_layout()
    original_path = os.path.join(output_folder, 'original_image.png')
    plt.savefig(original_path, bbox_inches='tight')
    plt.close()
    result_paths['original'] = original_path
    
    # 图2：热力图
    plt.figure(figsize=figsize, dpi=dpi)
    plt.matshow(heatmap_data)
    plt.title('注意力热力图')
    plt.axis('off')
    plt.colorbar(fraction=0.046, pad=0.04)
    plt.tight_layout()
    heatmap_path = os.path.join(output_folder, 'attention_heatmap.png')
    plt.savefig(heatmap_path, bbox_inches='tight')
    plt.close()
    result_paths['heatmap'] = heatmap_path
    
    # 图3：简单透明度重合的热力图
    plt.figure(figsize=figsize, dpi=dpi)
    plt.imshow(image)
    plt.imshow(heatmap_data, alpha=0.5)
    plt.title('简单叠加')
    plt.axis('off')
    plt.colorbar(fraction=0.046, pad=0.04, label='注意力强度')
    plt.tight_layout()
    overlay_path = os.path.join(output_folder, 'simple_overlay.png')
    plt.savefig(overlay_path, bbox_inches='tight')
    plt.close()
    result_paths['overlay'] = overlay_path
    
    # 图4：高级热力图重合
    heatmap_normalized = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())
    heatmap_colored = cm.jet(heatmap_normalized)
    heatmap_colored = (heatmap_colored[:, :, :3] * 255).astype(np.uint8)
    
    image_np = np.array(image)
    if len(image_np.shape) == 2:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    elif image_np.shape[2] == 4:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
    
    heatmap_resized = cv2.resize(heatmap_colored, (image_np.shape[1], image_np.shape[0]))
    
    mask = heatmap_normalized > 0.3
    mask = np.expand_dims(mask, axis=2)
    mask = np.repeat(mask, 3, axis=2)
    
    kernel = np.ones((5,5), np.uint8)
    mask_dilated = cv2.dilate(mask.astype(np.uint8), kernel, iterations=1)
    mask_edge = mask_dilated - mask.astype(np.uint8)
    mask_edge = mask_edge > 0
    
    overlay_image = np.where(mask, heatmap_resized, image_np)
    overlay_image = np.where(mask_edge, [255, 255, 0], overlay_image)
    
    plt.figure(figsize=figsize, dpi=dpi)
    plt.imshow(overlay_image)
    plt.title('增强叠加')
    plt.axis('off')
    plt.tight_layout()
    enhanced_path = os.path.join(output_folder, 'enhanced_overlay.png')
    plt.savefig(enhanced_path, bbox_inches='tight')
    plt.close()
    result_paths['enhanced'] = enhanced_path
    
    # 图5：聚光灯效果
    black_background = np.zeros_like(image_np)
    alpha_mask = heatmap_normalized.copy()
    alpha_mask = np.power(alpha_mask, 10)
    alpha_mask = np.expand_dims(alpha_mask, axis=2)
    alpha_mask = np.repeat(alpha_mask, 3, axis=2)
    
    spotlight_image = image_np * alpha_mask + black_background * (1 - alpha_mask)
    spotlight_image = spotlight_image.astype(np.uint8)
    
    plt.figure(figsize=figsize, dpi=dpi)
    plt.imshow(spotlight_image)
    plt.title('聚光灯效果')
    plt.axis('off')
    plt.tight_layout()
    spotlight_path = os.path.join(output_folder, 'spotlight_effect.png')
    plt.savefig(spotlight_path, bbox_inches='tight')
    plt.close()
    result_paths['spotlight'] = spotlight_path
    
    # 图6：三张图横向排布
    fig, axs = plt.subplots(1, 3, figsize=(24, 8), dpi=dpi)
    
    axs[0].imshow(image)
    axs[0].set_title('原始图像')
    axs[0].axis('off')
    
    heatmap_plot = axs[1].matshow(heatmap_data)
    axs[1].set_title('注意力热力图')
    axs[1].axis('off')
    plt.colorbar(heatmap_plot, ax=axs[1], fraction=0.046, pad=0.04)
    
    axs[2].imshow(spotlight_image)
    axs[2].set_title('聚光灯效果')
    axs[2].axis('off')
    
    plt.tight_layout()
    combined_path = os.path.join(output_folder, 'combined_visualization.png')
    plt.savefig(combined_path, bbox_inches='tight')
    plt.close()
    result_paths['combined'] = combined_path
    
    # 清理上传的文件（可选）
    try:
        os.remove(image_path)
    except:
        pass
    
    return result_paths

@app.route('/results/<path:filename>')
def get_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
