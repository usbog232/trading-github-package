这个目录是从当前运行中的 trading 项目复制出来的 GitHub 安全上传版。

特点：
- 不影响当前正在运行的原项目
- 已排除 .env / .venv / logs / dashboard 快照 / pid / 本地交易账本
- 保留代码、配置示例、启停脚本、Ubuntu 部署脚本

你上传 GitHub 时，建议上传这个目录里的内容。

上传前请再次确认：
1. config/settings.json 是否包含你不想公开的真实参数（如果有，建议删除，只保留 settings.example.json）
2. 不要把任何真实 .env 再手动拷进去
3. 如果要做公开仓库，建议补一个 README.md 说明用途和部署方式
