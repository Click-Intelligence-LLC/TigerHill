#!/bin/bash

# Streamlit Dashboard启动脚本

# 切换到项目根目录
cd "$(dirname "$0")/../../.."

# 设置PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 运行streamlit
streamlit run tigerhill/web/dashboard/app.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.gatherUsageStats false
