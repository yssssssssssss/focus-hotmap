# 视觉注意力热力图分析Web应用

这个Web应用基于DeepGaze III模型，用于分析图像中的视觉注意力分布并生成热力图。

## 功能特点

- 上传图片进行视觉注意力分析
- 生成多种可视化效果：
  - 原始图像
  - 注意力热力图
  - 简单叠加效果
  - 增强叠加效果
  - 聚光灯效果
  - 组合可视化

## 本地运行

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 下载中心偏置文件：
   从 https://github.com/matthias-k/DeepGaze/releases/download/v1.0.0/centerbias_mit1003.npy 下载，并放在项目根目录。

3. 运行应用：
   ```
   python app.py
   ```

4. 在浏览器中访问：
   ```
   http://localhost:5000
   ```

## 部署到云服务器

### 准备工作

1. 准备一台云服务器（推荐配置：2核4G以上，Ubuntu 20.04 LTS）
2. 域名（可选，用于配置HTTPS）

### 部署步骤

1. 连接到您的云服务器

2. 安装必要的系统依赖：
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools nginx git
   ```

3. 克隆项目到服务器：
   ```bash
   git clone <您的项目Git仓库URL> /var/www/visual-attention-app
   cd /var/www/visual-attention-app
   ```

4. 创建并激活虚拟环境：
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. 安装依赖：
   ```bash
   pip install -r requirements.txt
   pip install gunicorn
   ```

6. 下载中心偏置文件：
   ```bash
   wget https://github.com/matthias-k/DeepGaze/releases/download/v1.0.0/centerbias_mit1003.npy
   ```

7. 创建Gunicorn服务文件：
   ```bash
   sudo nano /etc/systemd/system/visual-attention.service
   ```

   添加以下内容：
   ```
   [Unit]
   Description=Gunicorn instance to serve visual attention app
   After=network.target

   [Service]
   User=<您的用户名>
   Group=www-data
   WorkingDirectory=/var/www/visual-attention-app
   Environment="PATH=/var/www/visual-attention-app/venv/bin"
   ExecStart=/var/www/visual-attention-app/venv/bin/gunicorn --workers 3 --bind unix:visual-attention.sock -m 007 app:app

   [Install]
   WantedBy=multi-user.target
   ```

8. 启动并启用Gunicorn服务：
   ```bash
   sudo systemctl start visual-attention
   sudo systemctl enable visual-attention
   ```

9. 配置Nginx：
   ```bash
   sudo nano /etc/nginx/sites-available/visual-attention
   ```

   添加以下内容：
   ```
   server {
       listen 80;
       server_name <您的域名或服务器IP>;

       location / {
           include proxy_params;
           proxy_pass http://unix:/var/www/visual-attention-app/visual-attention.sock;
       }

       location /static {
           alias /var/www/visual-attention-app/static;
       }

       location /uploads {
           alias /var/www/visual-attention-app/uploads;
           internal;
       }

       location /results {
           alias /var/www/visual-attention-app/results;
       }
   }
   ```

10. 启用Nginx配置并重启Nginx：
    ```bash
    sudo ln -s /etc/nginx/sites-available/visual-attention /etc/nginx/sites-enabled
    sudo systemctl restart nginx
    ```

11. 配置防火墙（如果启用）：
    ```bash
    sudo ufw allow 'Nginx Full'
    ```

12. 设置HTTPS（可选，推荐）：
    ```bash
    sudo apt install -y certbot python3-certbot-nginx
    sudo certbot --nginx -d <您的域名>
    ```

### 维护和更新

1. 更新应用代码：
   ```bash
   cd /var/www/visual-attention-app
   git pull
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart visual-attention
   ```

2. 查看日志：
   ```bash
   sudo journalctl -u visual-attention
   ```

## 注意事项

- 确保服务器有足够的磁盘空间来存储上传的图片和生成的结果
- 考虑定期清理uploads和results文件夹中的旧文件
- 如果您的服务器没有GPU，模型将在CPU上运行，处理速度会较慢

## 安全建议

- 限制上传文件的大小和类型
- 配置HTTPS以保护数据传输
- 定期更新系统和依赖包
- 考虑添加用户认证机制，特别是在公开环境中
