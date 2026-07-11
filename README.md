# Windows Server 快速部署

适用环境：Windows Server 2022。部署脚本使用项目内的独立运行环境，不安装 Git，
不修改系统 PATH，不使用或覆盖服务器已有的 Python，也不会停止旧网站或其他未知进程。

## 1. 下载并解压

在服务器浏览器打开：

<https://github.com/GuoZiqing555/Zzxwx_Class_Project/archive/refs/heads/main.zip>

下载后解压，将解压得到的文件夹移动并改名为：

```text
C:\sites\Zzxwx_Class_Project
```

不要覆盖旧网站目录。

## 2. 填写 API Key 和域名

进入 `C:\sites\Zzxwx_Class_Project`，复制 `.env.example` 并将副本命名为 `.env`。
如果资源管理器隐藏扩展名，建议在项目目录打开 PowerShell 后执行：

```powershell
Copy-Item .env.example .env
notepad .env
```

填写：

```dotenv
DEEPSEEK_API_KEY=实际API密钥
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DAILY_API_CALL_LIMIT=50
QUOTA_TIMEZONE=Asia/Shanghai
QUOTA_DB_PATH=data/quota.sqlite3
DOMAIN=实际子域名.example.com
```

`DOMAIN` 只填写域名，不包含 `https://`、路径或端口。该域名的 A 记录必须已经指向
服务器公网 IP。阿里云安全组需要放行 TCP 80/443，不要开放 8504。

## 3. 运行快速部署脚本

在项目文件夹空白处按住 Shift 并右键，选择“在此处打开 PowerShell”，然后执行：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy-windows.ps1
```

脚本会自动下载项目专用的 Python 3.12 64 位和 Caddy，全部放在项目的 `.runtime`
目录中，并创建两个独立的计划任务用于开机启动。首次运行需要下载依赖，通常需要几分钟。

完成后访问：

```text
https://实际子域名.example.com
```

## 安全边界

脚本只会：

- 写入当前项目的 `.runtime`、`data` 和 `logs` 目录
- 创建 `ZzxwxClassProject-App` 和 `ZzxwxClassProject-Caddy` 两个计划任务
- 新增 `ZzxwxClassProject-TCP-80/443` 两条 Windows 防火墙规则，不修改已有规则
- 使用本机回环地址 `127.0.0.1:8504`
- 在确认 80、443、8504 均未被占用后启动

脚本不会修改已有 Python、PATH、旧网站目录、3008 端口或未知进程。若目标端口已被占用，
脚本会显示占用 PID 并退出，不会结束该进程。

应用和代理日志分别保存在 `logs\app.log` 与 `logs\caddy.log`；Caddy 的 HTTPS 证书
数据保存在 `.runtime\caddy-data`，不会写入其他网站目录。

## 检查状态

```powershell
Get-ScheduledTask ZzxwxClassProject-App,ZzxwxClassProject-Caddy |
    Select-Object TaskName,State

Invoke-WebRequest http://127.0.0.1:8504/_stcore/health -UseBasicParsing
```

## 更新

再次从 GitHub 下载最新 ZIP。先保留旧目录中的 `.env` 和 `data` 文件夹，再用新文件覆盖
项目代码，最后重新运行：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy-windows.ps1
```

不要删除 `.env`、`data` 或 `.runtime`。

## 停止或恢复

```powershell
# 停止本项目，不影响其他网站
Stop-ScheduledTask -TaskName ZzxwxClassProject-Caddy
Stop-ScheduledTask -TaskName ZzxwxClassProject-App

# 恢复本项目
Start-ScheduledTask -TaskName ZzxwxClassProject-App
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName ZzxwxClassProject-Caddy
```
