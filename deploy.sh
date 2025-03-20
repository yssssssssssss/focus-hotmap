#!/bin/bash

# 视觉注意力热力图分析Web应用部署脚本

echo "开始部署视觉注意力热力图分析Web应用..."

# 更新系统
echo "正在更新系统..."
sudo apt update
sudo apt upgrade -y

# 安装必要的系统依赖
echo "正在安装系统依赖..."
sudo apt install -y python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools nginx git

# 创建应用目录
echo "正在创建应用目录..."
sudo mkdir -p /var/www/visual-attention-app
sudo chown -R $USER:$USER /var/www/visual-attention-app

# 复制应用文件
echo "正在复制应用文件..."
cp -r * /var/www/visual-attention-app/

# 创建虚拟环境
echo "正在创建虚拟环境..."
cd /var/www/visual-attention-app
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "正在安装依赖..."
pip install -r requirements.txt
pip install gunicorn

# 下载中心偏置文件
echo "正在下载中心偏置文件..."
wget https://github.com/matthias-k/DeepGaze/releases/download/v1.0.0/centerbias_mit1003.npy

# 创建Gunicorn服务文件
echo "正在创建Gunicorn服务文件..."
sudo bash -c 'cat > /etc/systemd/system/visual-attention.service << EOL
[Unit]
Description=Gunicorn instance to serve visual attention app
After=network.target

[Service]
User='$USER'
Group=www-data
WorkingDirectory=/var/www/visual-attention-app
Environment="PATH=/var/www/visual-attention-app/venv/bin"
ExecStart=/var/www/visual-attention-app/venv/bin/gunicorn --workers 3 --bind unix:visual-attention.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
EOL'

# 启动并启用Gunicorn服务
echo "正在启动Gunicorn服务..."
sudo systemctl start visual-attention
sudo systemctl enable visual-attention

# 配置Nginx
echo "正在配置Nginx..."
sudo bash -c 'cat > /etc/nginx/sites-available/visual-attention << EOL
server {
    listen 80;
    server_name '$HOSTNAME';

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
EOL'

# 启用Nginx配置并重启Nginx
echo "正在启用Nginx配置..."
sudo ln -s /etc/nginx/sites-available/visual-attention /etc/nginx/sites-enabled
sudo systemctl restart nginx

# 配置防火墙
echo "正在配置防火墙..."
sudo ufw allow 'Nginx Full'

echo "部署完成！您可以通过以下地址访问应用："
echo "http://$HOSTNAME"
echo ""
echo "如需配置HTTPS，请运行以下命令："
echo "sudo apt install -y certbot python3-certbot-nginx"
echo "sudo certbot --nginx -d <您的域名>"
