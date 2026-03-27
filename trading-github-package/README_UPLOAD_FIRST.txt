这是给 GitHub 准备的 trading 安全上传版。

你应该上传这个目录里的内容，而不是直接上传原始运行目录。

已做的处理：
- 不包含 .env
- 不包含 .venv
- 不包含 logs/
- 不包含 data/dashboard/latest.json
- 不包含 *.pid
- 保留 src/web/config/requirements/启停脚本/Ubuntu 部署脚本

上传前建议你再确认：
1. config/settings.example.json 是否适合作为公开示例
2. README 是否需要补充你的项目说明
3. 不要把任何真实私钥、真实 .env、真实日志再拷进去
