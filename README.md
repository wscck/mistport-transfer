# MistPort（雾港传输）2.2

自托管临时文件传输服务，局域网 / 互联网均可访问。应用容器监听 `8000`，推荐宿主机映射 `5555:8000`。

## 功能
- 发送、接收均使用居中毛玻璃弹窗。
- 支持发送单个/多个文件、整个文件夹（自动打包 ZIP）、文字（UTF-8 TXT）。
- 上传完成生成 6 位随机数字接收码，不生成分享链接。
- 不提供管理员登录、不设置提取密码。
- 默认接收码有效期 1 小时，可选 3 / 6 / 12 / 24 小时。
- 接收码在文件有效期间保持占用；过期清理后才可再次生成。
- 后台每 60 秒清理过期文件。
- 最近传输显示遮蔽文件名、时间、大小和下载次数。
- 数据库和上传文件统一保存在 `/data`，必须使用宿主机目录挂载持久化。

## Docker Hub：构建并推送镜像

在项目根目录（有本 Dockerfile 的目录）执行。把 `cwkcck` 替换为自己的 Docker Hub 用户名（如果不同）：

```bash
docker login
docker build -t cwkcck/mistport:2.2 -t cwkcck/mistport:latest .
docker push cwkcck/mistport:2.2
docker push cwkcck/mistport:latest
```

先在 Docker Hub 创建仓库 `mistport`。如仓库设为 Private，服务器拉取前也需要 `docker login`。

## Linux 服务器：单条 docker run 部署

```bash
sudo mkdir -p /data/mistport/storage
docker pull cwkcck/mistport:latest
docker run -d \
  --name mistport \
  --restart unless-stopped \
  -p 5555:8000 \
  -v /data/mistport/storage:/data \
  -e DATA_DIR=/data \
  -e MAX_FILE_MB=2048 \
  cwkcck/mistport:latest
```

访问 `http://服务器IP:5555`。

## 数据目录
- `/data/files/`：上传文件
- `/data/mistport.db`：元数据数据库

宿主机数据目录为 `/data/mistport/storage`。更换镜像或删除容器不会删除此目录。不要执行 `docker run --rm`，也不要删除挂载目录。

## 更新镜像

```bash
docker pull cwkcck/mistport:latest
docker stop mistport
docker rm mistport
docker run -d \
  --name mistport \
  --restart unless-stopped \
  -p 5555:8000 \
  -v /data/mistport/storage:/data \
  -e DATA_DIR=/data \
  -e MAX_FILE_MB=2048 \
  cwkcck/mistport:latest
```

## 检查与日志

```bash
docker ps
 docker logs -f mistport
```

## 安全提示
公网使用建议配置域名和 HTTPS 反向代理。不要把管理/数据库目录暴露到公网。定期备份 `/data/mistport/storage`。
