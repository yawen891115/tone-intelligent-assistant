# 为 tone-cli 集成新的测试工具

如果想让 tone-cli 支持一个新的测试工具，需要在 tests 目录下为它新建一个子目录，并提供几个脚本。

## 1. 安装脚本 install.sh
在 install.sh 中通过 GIT_URL 或 WEB_URL 指定测试工具的下载地址，tone fetch 会根据它拉取远程代码，然后编写编译和安装步骤。

## 2. 运行脚本
运行脚本负责调用测试工具，并把参数从 testconf 中读出来传给工具。

## 3. 结果解析
测试工具的原始输出各不相同，需要编写解析脚本，把结果转换成统一格式：功能测试输出每个用例的 Pass、Fail 或 Skip，性能测试输出"指标名: 数值"。

## 4. 本地验证
完成后依次执行 tone fetch、tone install、tone run，确认结果解析正确，再提交 PR 到 tone-cli 仓库。
