# ToneAgent 安装与排障

ToneAgent 是运行在测试机器上的代理程序，负责接收平台下发的测试步骤、执行脚本并回传日志和结果。

## 1. 安装
下载与机器架构匹配的 toneagent rpm 包后安装：

```bash
rpm -ivh toneagent-*.rpm
```

## 2. 配置
编辑 ToneAgent 配置文件，填写两项内容：
- tsn：在平台「机器管理」中添加机器时生成的机器序列号；
- server 地址：T-One 平台的访问地址。

## 3. 启动与开机自启

```bash
systemctl start toneagent
systemctl enable toneagent
```

## 4. 常见问题
### 4.1 平台上机器一直显示 Offline
通常是 ToneAgent 没有和平台建立心跳。依次检查：服务是否在运行、配置里的 TSN 是否和平台上的一致、机器到平台的网络是否通。
### 4.2 心跳超时
如果日志中频繁出现心跳超时，多半是网络抖动或机器负载过高，可以先重启 toneagent 服务再观察。
### 4.3 查看日志
ToneAgent 的运行日志可以用 journalctl -u toneagent 查看，排查问题时先看最近的报错。
