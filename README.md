# 部署说明

仓库地址：<https://github.com/GuoZiqing555/Zzxwx_Class_Project.git>

本项目使用 Docker Compose 部署。Streamlit 仅在 Docker 内网监听 8504，Caddy
对外提供 HTTPS。服务器只需要开放 22、80 和 443 端口。

## 一、上传代码到 GitHub

在项目目录执行：

```bash
git init
git add .
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/GuoZiqing555/Zzxwx_Class_Project.git
git push -u origin main
```

如果已经配置过 `origin`，使用：

```bash
git remote set-url origin https://github.com/GuoZiqing555/Zzxwx_Class_Project.git
git push -u origin main
```

`.env`、`miyao` 和 `miyao.txt` 已加入 `.gitignore`，不要强制提交这些文件。

## 二、准备阿里云服务器

以下步骤适用于阿里云 Ubuntu 22.04/24.04。

1. 在阿里云安全组的入方向放行 TCP `22`、`80`、`443`。
2. 不要开放 `8504`，该端口只供 Docker 内部访问。
3. 给域名添加 A 记录，指向服务器公网 IP。
4. 等待域名解析生效。

SSH 登录服务器，安装 Docker：

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo docker compose version
```

## 三、下载项目

```bash
git clone https://github.com/GuoZiqing555/Zzxwx_Class_Project.git
cd Zzxwx_Class_Project
```

## 四、网站所有者填写 API Key

网站所有者通过 SSH 登录服务器，然后进入项目目录：

```bash
cd Zzxwx_Class_Project
cp .env.example .env
nano .env
```

将 `.env` 中的内容改为实际配置：

```dotenv
DEEPSEEK_API_KEY=实际的API密钥
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com

DAILY_API_CALL_LIMIT=50
QUOTA_TIMEZONE=Asia/Shanghai
QUOTA_DB_PATH=/app/data/quota.sqlite3

DOMAIN=实际域名.example.com
```

`DOMAIN` 只填写域名，不要添加 `http://`、`https://`、路径或端口。

在 nano 中按 `Ctrl+O`、回车保存，再按 `Ctrl+X` 退出。随后限制文件权限：

```bash
chmod 600 .env
```

API Key 只保存在服务器的 `.env` 中，不需要上传到 GitHub。即使密钥有限额，也不建议
写入仓库，因为公开仓库中的历史提交很难彻底清除。

## 五、启动网站

在服务器的项目目录执行：

```bash
sudo docker compose config --quiet
sudo docker compose up -d --build
sudo docker compose ps
```

正常情况下，`app` 最终显示 `healthy`，`caddy` 显示 `running`。查看启动日志：

```bash
sudo docker compose logs --tail=100 app caddy
```

首次启动时，Caddy 会自动申请 HTTPS 证书，通常需要几十秒。然后访问：

```text
https://实际域名
```

也可以在服务器上检查：

```bash
curl -I https://实际域名
```

如果 HTTPS 证书申请失败，检查域名 A 记录是否指向当前服务器公网 IP，以及阿里云
安全组是否已经放行 80 和 443。

## 六、更新网站

代码推送到 GitHub 后，在服务器执行：

```bash
cd Zzxwx_Class_Project
git pull
sudo docker compose up -d --build
```

## 七、常用维护命令

```bash
# 查看容器状态
sudo docker compose ps

# 查看实时日志
sudo docker compose logs -f

# 重启网站
sudo docker compose restart

# 停止网站
sudo docker compose down

# 再次启动
sudo docker compose up -d
```

普通更新、重启或 `docker compose down` 不会删除每日配额数据。不要执行
`docker compose down -v`，除非确定需要删除持久化数据。

## 八、更换 API Key

网站所有者登录服务器后执行：

```bash
cd Zzxwx_Class_Project
nano .env
sudo docker compose up -d --force-recreate app
```

修改 `DEEPSEEK_API_KEY` 并保存后，重新创建应用容器即可生效。
