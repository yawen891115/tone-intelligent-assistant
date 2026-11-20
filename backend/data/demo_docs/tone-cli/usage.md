# tone-cli 使用说明

tone-cli 是 T-One 的命令行测试工具，可以脱离平台直接在机器上运行测试套件。

## 1. 安装

```bash
make install
```

## 2. 常用命令
- tone list：展示支持的测试套件列表；
- tone list testsuite_name：展示某个测试套件下的全部 testconf；
- tone fetch testsuite_name：拉取指定测试套件的代码；
- tone install testsuite_name：安装指定测试套件；
- tone run testsuite_name：运行该套件下的全部 testconf，也可以只运行某一个 testconf；
- tone uninstall testsuite_name：卸载指定测试套件；
- tone archive：把离线测试的结果打成 tar 包，上传到 T-One 平台后进行分析。

## 3. 查看帮助
执行 tone --help 或 tone -h 查看所有命令说明。
