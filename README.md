# Trading GitHub Package

一个面向 **Hyperliquid 合约交易** 的本地交易工作台，强调：

- 风险控制优先
- 结构化交易计划
- 自动 / 半自动执行
- 持仓、挂单、保护单可视化
- 本地交易记录统计

> 这是一个适合上传 GitHub 的部署版仓库，不包含你的真实私钥、真实 `.env`、真实运行日志或本机敏感配置。

---

## 功能概览

### 市场与策略
- Hyperliquid 行情 / K线 / 账户 / 挂单获取
- 1h 结构分析
- Swing 结构确认
- ATR 缓冲止损
- MACD 背离计划
- RR（风险回报比）计算

### 风控与执行
- 单笔风险控制
- 最大风险上限
- 最大名义仓位 / 最大保证金限制
- 自动测试单 / 自动实盘开关
- 保护单自动管理
- Kill Switch / 超时自动平仓

### Web 面板
- 市场状态
- 执行摘要
- 持仓明细
- Open Orders
- 风控参数设置
- 本地交易记录统计
- K 线缓存状态

### 本地交易记录
- 开仓时间
- 开仓价 / 平仓价
- 盈亏
- 开仓手续费 / 平仓手续费 / 总手续费
- 累计毛盈亏 / 净盈亏 / 胜率
- 支持从 Hyperliquid fills 历史回补

---

## 目录结构

```bash
config/      # 配置示例
src/         # 核心逻辑
web/         # 本地面板与控制接口
tests/       # 测试
start_trading.sh
stop_trading.sh
ubuntu-oneclick-deploy.sh
macos-oneclick-deploy.sh
```

---

## 环境要求

### Ubuntu
推荐：
- Ubuntu 22.04 / 24.04
- Python 3.11+
- 可访问 `https://api.hyperliquid.xyz`

### macOS
推荐：
- macOS 13+
- Python 3.11+
- 可访问 `https://api.hyperliquid.xyz`

---

## 一键部署

### Ubuntu
仓库根目录执行：

```bash
chmod +x ubuntu-oneclick-deploy.sh
./ubuntu-oneclick-deploy.sh
```

脚本会一步一步提示你：
- 输入 Git 仓库地址
- 输入安装目录
- 输入 Python 命令
- 选择是否安装为 systemd 服务
- 手动编辑 `.env` 与 `config/settings.json`
- 自动完成依赖安装和首次启动

---

### macOS
仓库根目录执行：

```bash
chmod +x macos-oneclick-deploy.sh
./macos-oneclick-deploy.sh
```

脚本会一步一步提示你：
- 输入 Git 仓库地址
- 输入安装目录
- 输入 Python 命令
- 手动编辑 `.env` 与 `config/settings.json`
- 自动完成依赖安装和首次启动

---

## 手动部署

```bash
git clone <your-repo-url>
cd trading-github-package
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.json config/settings.json
cp .env.example .env
```

然后手动填写：
- `config/settings.json`
- `.env`

最后运行：

```bash
./start_trading.sh
```

停止：

```bash
./stop_trading.sh
```

---

## 必填配置

### `.env`

```bash
HYPERLIQUID_SECRET_KEY=你的真实私钥
```

### `config/settings.json`
至少需要填写：
- `api.monitor_wallet_address`
- `api.execution_wallet_address`
- 风险参数
- 执行参数

> 注意：不要把真实 `.env` 和真实 `config/settings.json` 上传到 GitHub。

---

## 默认端口

- Dashboard: `http://127.0.0.1:8787/web/`
- Toggle API: `http://127.0.0.1:8788/api/health`

---

## 启停脚本

### `start_trading.sh`
会做：
- 清理旧进程
- 检查端口
- 启动 runner / dashboard / toggle server
- 校验只有一个 runner 在运行
- 校验 HTTP 服务可用

### `stop_trading.sh`
会做：
- 先执行 Kill Switch
- 清理 pid
- 清理 runner / web / toggle 相关进程
- 清理 8787 / 8788 端口残留监听

---

## GitHub 安全说明

建议上传：
- `src/`
- `web/`
- `tests/`
- `config/settings.example.json`
- `requirements.txt`
- `start_trading.sh`
- `stop_trading.sh`
- `ubuntu-oneclick-deploy.sh`
- `macos-oneclick-deploy.sh`

不要上传：
- `.env`
- `.venv/`
- `logs/`
- `data/dashboard/`
- `config/settings.json`
- 本地交易账本 / 缓存数据库

---

## 当前定位

这套系统更适合：
- 本地自用
- 私有部署
- 风控优先的半自动 / 自动交易实验

不建议在未充分验证前直接用于高风险大资金实盘。

---

## License

公开发布前，建议补充合适的许可证（例如 MIT / Apache-2.0 / 私有保留）。
