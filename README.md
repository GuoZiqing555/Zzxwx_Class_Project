# Windows Server 快速部署（公网 IP 访问）

适用环境：Windows Server 2022，没有域名，直接通过服务器公网 IP 访问。

**脚本会另外下载官方 Python 3.12.10 64 位，不使用服务器已有的 Python 3.14 32 位。**
独立 Python 保存在项目的 `.runtime\python`，不会安装到系统、修改 PATH 或覆盖旧 Python，
也不会停止旧网站或其他未知进程。

## 1. 下载并解压

在服务器浏览器打开：

<https://github.com/GuoZiqing555/Zzxwx_Class_Project/archive/refs/heads/main.zip>

下载后解压，将解压得到的文件夹移动并改名为：

```text
C:\sites\Zzxwx_Class_Project
```

不要覆盖旧网站目录。

## 2. 填写 API Key

进入 `C:\sites\Zzxwx_Class_Project`，在项目目录打开 PowerShell，执行：

```powershell
Copy-Item .env.example .env
notepad .env
```

只需要把 `DEEPSEEK_API_KEY` 改成实际密钥：

```dotenv
DEEPSEEK_API_KEY=实际API密钥
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DAILY_API_CALL_LIMIT=50
QUOTA_TIMEZONE=Asia/Shanghai
QUOTA_DB_PATH=data/quota.sqlite3
DOMAIN=
```

保存并关闭记事本。API Key 只保存在服务器的 `.env` 中，不会发送给访问网站的用户。

## 3. 放行端口

在阿里云安全组入方向添加 TCP `80`，授权对象根据实际访问范围设置：

- 仅内部人员使用：填写办公网络的固定公网 IP，例如 `1.2.3.4/32`，更安全。
- 需要所有人访问：填写 `0.0.0.0/0`。

不要开放 8504。脚本会添加一条 TCP 80 的 Windows 防火墙规则，但阿里云安全组仍需手动配置。

## 4. 运行快速部署脚本

在项目目录打开“管理员 PowerShell”，执行：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy-windows.ps1
```

脚本会自动从 Python 官网下载项目专用的 **Python 3.12.10 64 位**，并强制检查版本和
64 位架构；不符合时会立即停止。Python、Caddy 和依赖全部放在项目的 `.runtime` 目录，
并通过两个独立计划任务开机启动。首次运行需要下载依赖，通常需要几分钟。

完成后访问：

```text
http://服务器公网IP
```

注意是 `http://`，不是 `https://`，也不需要添加 `:8504`。

## 重要安全提示

没有域名时，本方案使用普通 HTTP，浏览器与服务器之间的内容没有加密。API Key 始终只在
服务器端，不会因此直接暴露；但用户填写的沟通内容可能被网络链路上的第三方看到。

建议优先在阿里云安全组中将 TCP 80 限制为指定办公公网 IP。若网站需要长期公开使用或
处理敏感信息，应购买并备案域名，之后再启用 HTTPS。

## 脚本安全边界

脚本只会：

- 写入当前项目的 `.runtime`、`data` 和 `logs` 目录
- 创建 `ZzxwxClassProject-App` 和 `ZzxwxClassProject-Caddy` 两个计划任务
- 新增 `ZzxwxClassProject-TCP-80` 一条 Windows 防火墙规则，不修改已有规则
- 使用本机回环地址 `127.0.0.1:8504`
- 在确认 80 和 8504 均未被占用后启动

脚本不会修改已有 Python、PATH、旧网站目录、3008 端口或未知进程。若目标端口已被占用，
脚本会显示占用 PID 并退出，不会结束该进程。

应用和代理日志分别保存在 `logs\app.log` 与 `logs\caddy.log`。

## 检查状态

```powershell
Get-ScheduledTask ZzxwxClassProject-App,ZzxwxClassProject-Caddy |
    Select-Object TaskName,State

Invoke-WebRequest http://127.0.0.1:8504/_stcore/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1/ -UseBasicParsing
```

## 更新

再次下载最新 ZIP。保留旧目录中的 `.env`、`data` 和 `.runtime`，用新文件覆盖项目代码，
然后重新运行：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy-windows.ps1
```

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
