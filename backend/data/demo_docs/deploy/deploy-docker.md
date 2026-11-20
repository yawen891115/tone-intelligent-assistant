# T-One 开源版部署

T-One 开源版可以通过 tone-deploy 项目一键部署，适合在企业内网搭建自己的测试平台。

## 1. 环境依赖
部署机器需要安装 python3、docker 和 docker-compose，建议至少 4 核 CPU、8G 内存。

## 2. 一键部署

```bash
git clone https://gitee.com/anolis/tone-deploy.git /tmp/tone-deploy
sh /tmp/tone-deploy/Scripts/source_code_build/rapid_deploy/start.sh IP
```

其中 IP 替换为部署机器的公网或内网 IP。脚本会拉取镜像并启动 tone-web、tone-front 以及数据库等容器。

## 3. 访问平台
部署完成后，在浏览器中访问部署机器的 IP 即可打开 T-One。首次登录后请尽快修改管理员密码。
