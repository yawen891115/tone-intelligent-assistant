# 使用 kdump 收集内核崩溃信息

当系统发生内核崩溃（panic）时，kdump 可以保存崩溃时的内存镜像 vmcore，便于事后分析原因。

## 1. 预留内存
在内核启动参数中加入 crashkernel 参数为 kdump 预留内存，例如 crashkernel=auto，修改后需要重启生效。

## 2. 启动服务

```bash
systemctl enable --now kdump
```

## 3. 查看 vmcore
系统崩溃重启后，vmcore 默认保存在 /var/crash 目录。可以使用 crash 工具配合对应版本的 debuginfo 包进行分析。
