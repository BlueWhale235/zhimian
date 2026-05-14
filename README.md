# 职面

职面是一个本地单机版智能简历管理与文字模拟面试 MVP。

## 后端环境

```powershell
conda env create -f environment.yml
conda activate zhimian
```

如果环境已经创建过，更新依赖：

```powershell
conda env update -f environment.yml --prune
conda activate zhimian
```

## 启动后端

```powershell
cd .\backend
python -m uvicorn app.main:app --reload --port 8000
```

后端地址：`http://127.0.0.1:8000`

如果 Windows 报错 `[WinError 10013]`，通常是端口已经被占用或系统不允许绑定。先检查 `8000` 是否已有服务：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

如果已有职面后端在运行，直接使用即可；如果要换端口，可以启动到 `8010`：

```powershell
python -m uvicorn app.main:app --reload --port 8010
```

换端口后，前端需要设置同样的 API 地址，例如：

```powershell
cd .\frontend
npm run dev
```

## 启动前端

```powershell
cd .\frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`

前端默认连接 `http://127.0.0.1:8000`。如需修改，设置 `VITE_API_BASE`。

前端使用 Vue Router，开发模式支持热更新，可以直接访问：

- `http://127.0.0.1:5173/resumes`
- `http://127.0.0.1:5173/builder`
- `http://127.0.0.1:5173/jds`
- `http://127.0.0.1:5173/interview`
- `http://127.0.0.1:5173/history`
- `http://127.0.0.1:5173/settings`

## 第一版范围

- PDF 简历上传、缩略图、预览、下载、删除。
- 在线简历表单自动保存，支持导出 PDF 并加入简历库。
- JD 粘贴导入，支持用 OpenAI 兼容接口提取技能要求。
- 文字模拟面试，支持普通/压力模式。
- 面试历史与 STAR 复盘报告。
- 本地 SQLite 与 `backend/static/` 静态文件存储。
