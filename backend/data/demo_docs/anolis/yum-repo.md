# 配置软件源

Anolis OS 使用 dnf（兼容 yum 命令）管理软件包，软件源的配置文件位于 /etc/yum.repos.d/ 目录下。

## 1. 查看当前软件源

```bash
dnf repolist
```

## 2. 更换镜像地址
如果默认源下载速度慢，可以把 /etc/yum.repos.d/ 下 repo 文件中的 baseurl 改成离你更近的镜像站地址。修改前先备份原文件。

## 3. 刷新缓存

```bash
dnf clean all
dnf makecache
```

## 4. 常见报错
如果出现 "Failed to download metadata for repo"，通常是网络不通或者 baseurl 写错了，先用 curl 访问 baseurl 确认地址是否可达。
