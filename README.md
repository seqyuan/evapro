# evapro

遍历lims数据库，把新下的lims任务单添加到anneva监控

## 安装

```bash
pip install evapro
```

或者使用poetry:

```bash
poetry add evapro
```

## 使用

```bash
evapro [options]
```

## 配置

配置文件位于 `evapro/config/evapro.yaml`，包含以下配置项：

- 数据库连接信息
- 监控参数设置
- 任务处理选项

## 功能

- 自动检测新lims任务单
- 将任务单添加到anneva监控系统
- 状态跟踪和报告

## 开发

```bash
git clone https://github.com/seqyuan/evapro.git
cd evapro
poetry install
poetry run pytest
```

## 贡献

欢迎提交Pull Request。请确保通过所有测试并更新文档。

## 许可证

[MIT](LICENSE)
