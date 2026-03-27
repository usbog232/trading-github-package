# trading-github-package

Hyperliquid 合约交易本地工作台，包含：

- 行情 / K线 / 账户 / 挂单读取
- 1h 结构分析
- Swing 结构确认 + ATR 缓冲止损
- 自动 / 半自动执行控制
- 保护单管理
- 本地交易记录统计
- Web 面板

仓库地址：

```bash
https://github.com/usbog232/trading-github-package.git
```

> 本仓库为公开部署版，不包含真实 `.env`、真实 `config/settings.json`、日志、缓存数据库或本地运行账本。

---

## 环境要求

### Ubuntu
- Ubuntu 22.04 / 24.04
- Python 3.11+
- `git`
- `curl`
- `lsof`
- `pkill`
- 可访问 `https://api.hyperliquid.xyz`

### macOS
- macOS 13+
- Python 3.11+
- `git`
- `curl`
- `lsof`
- `pkill`
- 可访问 `https://api.hyperliquid.xyz`

---

## 快速开始

### Ubuntu

```bash
git clone https://github.com/usbog232/trading-github-package.git
cd trading-github-package
chmod +x ubuntu-oneclick-deploy.sh
./ubuntu-oneclick-deploy.sh
```

### macOS

```bash
git clone https://github.com/usbog232/trading-github-package.git
cd trading-github-package
chmod +x macos-oneclick-deploy.sh
./macos-oneclick-deploy.sh
```

---

## 一键部署脚本会做什么

### Ubuntu 部署脚本
- 安装系统依赖
- 创建 Python 虚拟环境
- 安装 `requirements.txt`
- 初始化 `config/settings.json`
- 初始化 `.env`
- 提示手动填写配置
- 首次启动系统
- 可选安装为 `systemd` 服务

### macOS 部署脚本
- 创建 Python 虚拟环境
- 安装 `requirements.txt`
- 初始化 `config/settings.json`
- 初始化 `.env`
- 提示手动填写配置
- 首次启动系统

---

## 需要手动填写的配置

### `.env`

```bash
HYPERLIQUID_SECRET_KEY=your_private_key_here
```

### `config/settings.json`
至少需要填写：

- `api.monitor_wallet_address`
- `api.execution_wallet_address`
- 风险参数
- 执行参数

如果项目目录中不存在 `config/settings.json`，部署脚本会从：

- `config/settings.example.json`

自动复制生成。

---

## 启动与停止

部署完成后，可直接使用：

```bash
./start_trading.sh
./stop_trading.sh
```

默认本地面板地址：

```bash
http://127.0.0.1:8787/web/
```

Toggle API 健康检查：

```bash
http://127.0.0.1:8788/api/health
```

---

## 仓库结构

```bash
config/
src/
web/
tests/
start_trading.sh
stop_trading.sh
ubuntu-oneclick-deploy.sh
macos-oneclick-deploy.sh
```

---

## 功能说明

### 分析与计划
- 1h 结构提取
- Swing 高低点确认
- ATR 缓冲止损
- RR 计算
- MACD 背离计划

### 风控与执行
- 单笔风险限制
- 最大风险上限
- 最大名义仓位 / 保证金限制
- 自动开仓控制
- 保护单自检 / 自愈
- Kill Switch

### 记录与展示
- 持仓明细
- Open Orders
- 执行摘要
- 风控设置
- 本地交易记录统计
- 交易所 fills 历史回补

---

## 安全说明

请不要上传以下内容：

- `.env`
- `config/settings.json`
- `logs/`
- `data/dashboard/`
- `data/market_cache/candles.db`
- 本地交易账本文件
- 私钥或真实钱包地址

建议仅保留：

- `config/settings.example.json`
- 源代码
- 测试
- README
- 部署脚本

---

## 说明

本项目更适合：

- 本地自用
- 私有部署
- 风控优先的半自动 / 自动交易实验

在未充分验证前，不建议直接用于高风险大资金实盘环境。

---

## License

公开发布前，建议补充合适的许可证（例如 MIT / Apache-2.0 / 私有保留）。
