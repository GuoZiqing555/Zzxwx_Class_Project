# Windows Server 部署说明

仓库：<https://github.com/GuoZiqing555/Zzxwx_Class_Project.git>

本说明适用于阿里云 Windows Server。Streamlit 只监听本机 `127.0.0.1:8504`，
Caddy 对外提供 HTTPS，NSSM 负责将两者注册为开机自动启动的 Windows 服务。

## 一、部署前准备

1. 给域名添加 A 记录，指向服务器公网 IP。
2. 在阿里云安全组入方向开放 TCP `80` 和 `443`。
3. 如果需要远程桌面，保留 TCP `3389`；不要在公网开放 `8504`。
4. 使用远程桌面登录服务器，打开“管理员 PowerShell”。

## 二、安装部署工具

在管理员 PowerShell 中安装 Chocolatey：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

安装 Git、Python、Caddy 和 NSSM：

```powershell
choco install -y git python312 caddy nssm
```

安装结束后关闭 PowerShell，再重新打开一个管理员 PowerShell，使 PATH 生效。确认命令可用：

```powershell
git --version
python --version
caddy version
nssm version
```

## 三、下载项目

建议安装到 `C:\sites`：

```powershell
New-Item -ItemType Directory -Force C:\sites | Out-Null
Set-Location C:\sites
git clone https://github.com/GuoZiqing555/Zzxwx_Class_Project.git
Set-Location .\Zzxwx_Class_Project
```

## 四、网站所有者填写 API Key

复制配置模板并用记事本打开：

```powershell
Copy-Item .env.example .env
notepad .env
```

填写实际配置：

```dotenv
DEEPSEEK_API_KEY=实际的API密钥
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DAILY_API_CALL_LIMIT=50
QUOTA_TIMEZONE=Asia/Shanghai
QUOTA_DB_PATH=data/quota.sqlite3
DOMAIN=实际域名.example.com
```

`DOMAIN` 只填写域名，不添加 `http://`、`https://`、路径或端口。保存并关闭记事本。
API Key 只保存在服务器的 `.env`，不需要上传到 GitHub。

## 五、一键部署

仍在项目目录中，以管理员 PowerShell 执行：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy-windows.ps1 -Domain "实际域名.example.com"
```

脚本会自动完成以下操作：

- 创建 Python 虚拟环境并安装固定版本依赖
- 注册并启动 `ZzxwxApp` 服务
- 注册并启动 `ZzxwxCaddy` 服务
- 设置开机自动启动
- 开放 Windows 防火墙 TCP 80/443
- 将日志写入项目的 `logs` 目录

部署完成后访问：

```text
https://实际域名
```

Caddy 首次申请 HTTPS 证书可能需要几十秒。如果打不开，先检查服务和日志：

```powershell
Get-Service ZzxwxApp,ZzxwxCaddy
Get-Content .\logs\app-error.log -Tail 100
Get-Content .\logs\caddy-error.log -Tail 100
```

## 六、更新网站

管理员 PowerShell 执行：

```powershell
Set-Location C:\sites\Zzxwx_Class_Project
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Restart-Service ZzxwxApp
Restart-Service ZzxwxCaddy
```

## 七、更换 API Key

```powershell
Set-Location C:\sites\Zzxwx_Class_Project
notepad .env
Restart-Service ZzxwxApp
```

保存新的 `DEEPSEEK_API_KEY` 后重启应用服务即可生效。

## 八、常用维护命令

```powershell
# 查看状态
Get-Service ZzxwxApp,ZzxwxCaddy

# 重启
Restart-Service ZzxwxApp,ZzxwxCaddy

# 停止
Stop-Service ZzxwxCaddy,ZzxwxApp

# 启动
Start-Service ZzxwxApp,ZzxwxCaddy
```

每日配额数据库保存在 `data\quota.sqlite3`。更新代码或重启服务不会删除该文件。
