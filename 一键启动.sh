#!/bin/bash
# 财务收据系统 - 一键启动脚本
# 沙箱唤醒后运行此脚本即可恢复服务

cd /workspace/finance-receipt-app

# 杀掉旧进程
pkill -f "python3 app.py" 2>/dev/null
sleep 1
lsof -ti:5000 | xargs kill -9 2>/dev/null 2>/dev/null
sleep 1

# 启动应用
nohup python3 app.py > /dev/null 2>&1 &

sleep 3

# 检查是否启动成功
if curl -s http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ 财务收据系统启动成功！"
    echo ""
    echo "访问地址："
    echo "https://webview.e2b.bj6.sandbox.cloudstudio.club/?x-cs-sandbox-id=5329d080e75d4e938bdcc28046836028&x-cs-sandbox-port=5000"
else
    echo "❌ 启动失败，请检查日志"
fi
