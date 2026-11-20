# ANCK 内核

ANCK（Anolis Cloud Kernel）是龙蜥社区维护的云内核，是 Anolis OS 的默认内核。

## 1. 特点
ANCK 针对云场景做了性能和稳定性优化，并持续回合上游社区的安全修复。

## 2. 查看当前内核
执行 uname -r 查看正在运行的内核版本。

## 3. 安装其他版本
使用 dnf 安装指定版本的 kernel 包，安装后用 grubby 设置默认启动项，然后重启：

```bash
grubby --default-kernel
grubby --set-default /boot/vmlinuz-<版本号>
```
