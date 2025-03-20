from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import sys
import numpy as np
import uuid
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入app.py中的Flask应用
from app import app as flask_app

# 导出应用供Vercel使用
app = flask_app
