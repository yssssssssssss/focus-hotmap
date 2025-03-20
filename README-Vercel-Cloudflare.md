# 在Vercel和Cloudflare上部署视觉注意力热力图分析项目

本文档详细介绍了如何将视觉注意力热力图分析项目部署到Vercel和Cloudflare平台上。

## 一、Vercel部署流程

Vercel是一个专注于前端部署的平台，但它也支持Python应用程序的部署。以下是详细的部署步骤：

### 1. 准备工作

- 注册Vercel账号：访问[Vercel官网](https://vercel.com)注册账号
- 安装Git：确保您的电脑上已安装Git
- 安装Node.js和npm：Vercel CLI需要Node.js环境

### 2. 项目准备

我们已经对项目进行了一些调整，使其适合Vercel部署：

- 创建了`vercel.json`配置文件
- 修改了`app.py`以适应Vercel的无服务器环境
- 创建了`api/index.py`文件作为Vercel的入口点
- 准备了`requirements-vercel.txt`文件，列出了适合Vercel环境的依赖

### 3. 安装Vercel CLI并登录

```bash
# 安装Vercel CLI
npm install -g vercel

# 登录Vercel
vercel login
```

### 4. 创建GitHub仓库

1. 在GitHub上创建一个新仓库
2. 将项目推送到GitHub仓库：

```bash
# 初始化Git仓库
git init

# 添加所有文件
git add .

# 提交更改
git commit -m "初始化项目"

# 添加远程仓库
git remote add origin https://github.com/您的用户名/您的仓库名.git

# 推送到GitHub
git push -u origin main
```

### 5. 在Vercel上部署

#### 方法一：通过Vercel网站部署

1. 登录[Vercel控制台](https://vercel.com/dashboard)
2. 点击"New Project"按钮
3. 从"Import Git Repository"部分选择您的GitHub仓库
4. 配置项目：
   - Framework Preset: 选择"Other"
   - Build Command: 留空
   - Output Directory: 留空
   - Install Command: `pip install -r requirements-vercel.txt`
5. 点击"Environment Variables"，添加以下环境变量：
   - `VERCEL`: `1`
6. 点击"Deploy"按钮开始部署

#### 方法二：通过Vercel CLI部署

```bash
# 进入项目目录
cd 项目目录

# 部署到Vercel
vercel --prod
```

在部署过程中，CLI会询问一些问题：
- 是否要链接到现有项目？选择"No"创建新项目
- 项目名称：输入您想要的项目名称
- 构建命令：留空
- 输出目录：留空
- 开发命令：留空

### 6. 处理中心偏置文件

由于Vercel的无服务器环境不允许在部署后写入文件系统，我们需要将中心偏置文件作为静态资源包含在部署中：

1. 确保`centerbias_mit1003.npy`文件位于项目根目录
2. 在`vercel.json`中添加以下配置，确保文件被正确部署：

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    },
    {
      "src": "centerbias_mit1003.npy",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

### 7. 限制和注意事项

Vercel的无服务器环境有一些限制，需要注意：

- 执行时间限制：函数执行时间最长为10秒（免费计划）或60秒（付费计划）
- 内存限制：函数内存最大为1GB（免费计划）或3GB（付费计划）
- 存储限制：`/tmp`目录可用于临时存储，但有大小限制
- 无GPU支持：Vercel不提供GPU支持，模型将在CPU上运行，处理速度较慢
- 无状态：每次请求都会在新的环境中执行，不能依赖于之前请求的状态

针对这些限制，我们的解决方案：

1. 简化模型处理流程，减少执行时间
2. 使用`/tmp`目录存储上传的文件和结果
3. 在代码中添加了延迟加载模型的逻辑
4. 使用CPU版本的模型

## 二、Cloudflare Pages部署流程

Cloudflare Pages是Cloudflare提供的静态网站托管服务，但它也支持通过Cloudflare Workers运行服务器端代码。

### 1. 准备工作

- 注册Cloudflare账号：访问[Cloudflare官网](https://www.cloudflare.com)注册账号
- 安装Wrangler CLI：Cloudflare的命令行工具

```bash
# 安装Wrangler CLI
npm install -g wrangler

# 登录Cloudflare
wrangler login
```

### 2. 项目调整

我们需要调整项目结构，使其适合Cloudflare Pages和Workers的部署模式：

1. 创建`workers-site`目录，用于存放Worker代码
2. 创建前端静态文件目录

#### 创建Worker脚本

创建`workers-site/index.js`文件：

```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  // 处理静态资源
  if (url.pathname.startsWith('/static/')) {
    // 从KV存储或其他存储服务获取静态资源
    return fetch(request)
  }
  
  // 处理API请求
  if (url.pathname.startsWith('/api/')) {
    // 调用Python API（可能需要部署在其他服务上）
    return fetch('https://your-python-api.example.com' + url.pathname)
  }
  
  // 默认返回前端页面
  return fetch(request)
}
```

#### 创建Cloudflare Pages配置文件

创建`wrangler.toml`文件：

```toml
name = "visual-attention-app"
type = "webpack"
account_id = "your-account-id"
workers_dev = true
route = ""
zone_id = ""

[site]
bucket = "./public"
entry-point = "workers-site"
```

### 3. 分离前端和后端

由于Cloudflare Workers对Python支持有限，我们需要将项目分为前端和后端两部分：

#### 前端部分（部署到Cloudflare Pages）

1. 创建`public`目录，用于存放静态文件
2. 将HTML、CSS、JavaScript文件移动到`public`目录
3. 修改前端代码，使其调用后端API

#### 后端部分（部署到其他支持Python的平台）

1. 将Python代码部署到支持Python的平台（如Heroku、AWS Lambda、Google Cloud Functions等）
2. 确保API端点可以被Cloudflare Pages访问

### 4. 使用Cloudflare Workers AI（可选）

如果您想使用Cloudflare的AI功能，可以考虑使用Cloudflare Workers AI：

```javascript
import { Ai } from '@cloudflare/ai'

export default {
  async fetch(request, env) {
    const ai = new Ai(env.AI)
    
    // 处理图像
    const formData = await request.formData()
    const image = formData.get('image')
    
    // 使用AI模型处理图像
    const result = await ai.run('@cf/your-model', { image })
    
    return new Response(JSON.stringify(result))
  }
}
```

### 5. 部署到Cloudflare Pages

```bash
# 发布Worker
wrangler publish

# 部署Pages
wrangler pages publish public
```

### 6. 限制和注意事项

Cloudflare的环境也有一些限制：

- Workers执行时间限制：CPU时间最长为10ms（免费计划）或50ms（付费计划）
- 内存限制：Workers内存最大为128MB
- 不支持直接运行Python代码：需要将Python代码部署到其他平台
- 存储限制：KV存储和R2存储有容量限制

## 三、混合部署方案（推荐）

考虑到Vercel和Cloudflare的各自限制，推荐采用混合部署方案：

1. 前端界面部署到Cloudflare Pages
2. Python后端API部署到Vercel或其他支持Python的平台
3. 使用Cloudflare R2存储上传的图片和生成的结果

### 实施步骤

1. 将前端代码部署到Cloudflare Pages
2. 将后端API部署到Vercel
3. 配置Cloudflare R2存储：

```bash
# 创建R2存储桶
wrangler r2 bucket create visual-attention-uploads
wrangler r2 bucket create visual-attention-results
```

4. 修改Worker代码，使用R2存储：

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    
    // 处理上传
    if (url.pathname === '/upload' && request.method === 'POST') {
      const formData = await request.formData()
      const file = formData.get('file')
      
      // 存储到R2
      const key = crypto.randomUUID()
      await env.UPLOADS.put(key, file)
      
      // 调用Vercel API处理图像
      const apiResponse = await fetch('https://your-vercel-api.vercel.app/process', {
        method: 'POST',
        body: JSON.stringify({ key })
      })
      
      return apiResponse
    }
    
    // 获取结果
    if (url.pathname.startsWith('/results/')) {
      const key = url.pathname.replace('/results/', '')
      const object = await env.RESULTS.get(key)
      
      if (object === null) {
        return new Response('Not found', { status: 404 })
      }
      
      return new Response(object.body)
    }
    
    // 默认返回前端页面
    return env.ASSETS.fetch(request)
  }
}
```

## 四、总结

### Vercel部署优势

- 简单易用，支持Python
- 免费计划功能丰富
- 自动CI/CD集成
- 全球CDN分发

### Cloudflare部署优势

- 强大的CDN和安全功能
- Workers执行速度快
- R2存储成本低
- 全球边缘网络

### 推荐方案

1. **小规模应用**：直接使用Vercel部署
2. **中等规模应用**：使用混合部署方案
3. **大规模应用**：考虑使用专业的云服务提供商（AWS、GCP、阿里云等）

无论选择哪种方案，都建议进行以下优化：

1. 减小模型大小或使用更轻量级的模型
2. 优化图像处理流程
3. 实现结果缓存机制
4. 添加用户认证和访问控制
5. 监控应用性能和使用情况
