# MistPort（雾港传输）

**简单、轻量、私有化部署的临时文件传输服务。**

MistPort 是一款基于 Python 和 FastAPI 开发的自托管临时文件传输工具，旨在让不同设备之间的文件分享更加简单、方便。

无需生成分享链接，通过自动生成的 6 位数字接收码即可完成文件传输。支持单个文件、整个文件夹以及文本内容的发送与接收。

项目采用 Docker 容器化部署，可以运行在 Linux 服务器上，让用户使用自己的服务器搭建专属文件传输服务。

---

## ✨ 功能特点

- **6 位数字接收码**：自动生成随机 6 位接收码，无需手动设置。
- **临时文件传输**：支持设置传输有效期，过期后接收码失效。
- **自动清理文件**：传输文件到期后自动删除，减少服务器存储占用。
- **文件传输**：支持单个文件上传、接收和下载。
- **文件夹传输**：支持整个文件夹上传，自动打包为 ZIP，并保留原有目录结构。
- **文本传输**：支持发送文字内容，自动生成 UTF-8 编码的 TXT 文件。
- **最近传输记录**：显示最近传输信息，包括文件名（部分遮蔽）、时间、大小和下载次数。
- **Docker 部署**：通过 Docker 快速部署，无需复杂的运行环境配置。
- **持久化存储**：支持挂载宿主机目录，容器重建后仍可保留上传文件。

## 🛠️ 技术栈

| 技术 | 用途 |
|---|---|
| Python | 后端开发语言 |
| FastAPI | Web 服务框架 |
| Uvicorn | ASGI 服务运行环境 |
| HTML | 页面结构 |
| CSS | 页面样式 |
| JavaScript | 前端交互 |
| Docker | 应用容器化部署 |

## 🚀 快速部署

### 1. 拉取 Docker 镜像

```bash
sudo docker pull cwkcck/mistport:latest
```

### 2. 创建文件存储目录

```bash
sudo mkdir -p /data/home/mistport/storage
```

### 3. 启动 MistPort

```bash
sudo docker run -d \
  --name mistport \
  --restart unless-stopped \
  -p 5555:8000 \
  -v /data/home/mistport/storage:/data \
  -e DATA_DIR=/data \
  -e MAX_FILE_MB=2048 \
  cwkcck/mistport:latest
```

### 4. 访问服务

在浏览器中打开：

```text
http://服务器IP:5555
```

将 `服务器IP` 替换为自己的服务器公网 IP 或局域网 IP。

---

## ⚙️ 部署配置

MistPort 当前部署采用以下配置：

| 配置项目 | 配置值 | 说明 |
|---|---|---|
| 外部访问端口 | `5555` | 浏览器访问服务使用的端口 |
| 容器内部端口 | `8000` | Docker 容器内应用监听端口 |
| 宿主机存储路径 | `/data/home/mistport/storage` | 上传文件实际保存位置 |
| 容器存储路径 | `/data` | 容器内部数据目录 |
| 最大文件大小配置 | `2048 MB` | 上传文件大小限制配置 |
| 容器自动重启 | `unless-stopped` | Docker 重启后自动启动，除非手动停止 |

### 端口映射说明

```text
服务器 5555 端口
       ↓
Docker 容器 8000 端口
       ↓
MistPort Web 服务
```

### 文件存储说明

```text
宿主机：
/data/home/mistport/storage

       ↓ Docker 数据卷挂载

容器内部：
/data
```

上传的文件保存在宿主机目录中，即使删除或重新创建 Docker 容器，也不会因为容器本身被删除而丢失这些文件。

## 🐳 Docker 管理命令

### 查看容器运行状态

```bash
sudo docker ps
```

### 查看运行日志

```bash
sudo docker logs -f mistport
```

### 停止服务

```bash
sudo docker stop mistport
```

### 启动服务

```bash
sudo docker start mistport
```

### 重启服务

```bash
sudo docker restart mistport
```

### 删除容器

```bash
sudo docker rm -f mistport
```

注意：删除容器不会自动删除宿主机上的文件存储目录。

## 📦 Docker 镜像

Docker Hub：

https://hub.docker.com/r/cwkcck/mistport

当前发布版本：

| 镜像标签 | 说明 |
|---|---|
| `cwkcck/mistport:2.2` | MistPort 2.2 版本 |
| `cwkcck/mistport:latest` | 当前最新发布标签 |

拉取指定版本：

```bash
sudo docker pull cwkcck/mistport:2.2
```

拉取最新标签：

```bash
sudo docker pull cwkcck/mistport:latest
```

## 🔒 安全说明

MistPort 适合部署在个人服务器或自有 Linux 服务器上。

如果需要开放公网访问，建议：

- 配置 HTTPS 加密访问。
- 合理设置服务器防火墙。
- 注意服务器磁盘空间和上传文件大小限制。
- 定期检查服务运行日志。
- 不要将不可信的服务器环境直接暴露在公网。

## 🗺️ 项目定位

MistPort 希望提供一种简单、方便的临时文件传输方式。

不依赖第三方文件托管平台，不需要生成复杂的分享链接，只需要自己的服务器，就可以在不同设备之间传输文件。

## 📄 开源许可证

项目开源许可证暂未确定，后续将在确定授权方式后补充 LICENSE 文件。

---

**MistPort（雾港传输）——让文件传输更简单。**
