# Trading Control Scripts

## Start

```bash
cd /path/to/trading   # 替换为你的本地路径
cp .env.example .env   # 首次时复制
# 然后在 .env 里填入 HYPERLIQUID_SECRET_KEY
./start_trading.sh
```

作用：
- 加载本地 `.env`（若存在）
- 先清理旧的 trading 残留进程
- 启动 runner 后台刷新
- 启动 dashboard web 服务
- 启动 toggle server（用于网页实盘开关）
- 输出 dashboard 本地地址与全部 PID

## Stop

```bash
cd /path/to/trading   # 替换为你的本地路径
./stop_trading.sh
```

当前作用：
- 先执行 Kill Switch（若 live execution 开启则尝试真实平仓）
- 停止 runner / dashboard / toggle 进程
- 兜底扫描并清扫所有 trading 相关残留进程

## Important

`stop_trading.sh` 里“立马终止交易市价平仓”目前还只是安全占位。
原因：当前系统还没有接入 Hyperliquid 的真实签名执行层。

在没有完成以下内容前，不允许脚本自动市价平仓：
- Hyperliquid exchange endpoint 签名
- 执行钱包权限校验
- 防重复发单
- 平仓目标仓位识别
- 失败重试与回执确认

所以目前停机脚本的含义是：
- 停掉策略/监控
- 不替你发送真实交易指令
