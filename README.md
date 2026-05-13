# 财务收据自动生成应用

一个功能完整的Web应用，用于自动生成财务收据、记录管理、PDF导出等功能。

## 功能特性

✅ **仪表盘** - 数据概览与快速操作
- 今日/本月/全部收据统计
- 总金额统计
- 最近收据列表
- 快速操作入口

✅ **收据生成** - 智能表单
- 自动生成收据编号（格式：RCP-YYYYMMDD-XXX）
- 自动计算税额和总额
- 支持多币种（CNY, USD, EUR, GBP）
- 实时预览
- 保存并生成PDF

✅ **收据管理** - 列表与搜索
- 支持搜索（按编号、付款方、事由）
- 支持筛选（币种、日期范围）
- 分页显示
- 批量操作（删除、导出）
- 查看详情、下载PDF

✅ **PDF导出** - 高质量PDF生成
- 基于HTML模板生成PDF
- 支持中文字符
- 下载和打印功能

✅ **模板管理** - 自定义收据样式
- 预设标准模板
- 支持自定义HTML模板
- 设置默认模板
- 模板预览

✅ **数据统计** - 可视化分析
- 月度趋势图表
- 币种分布图表
- 按付款方统计
- 导出Excel报表（开发中）

## 技术栈

- **后端**: Flask 3.0.0 + Python 3.11
- **前端**: HTML5 + CSS3 + JavaScript + Bootstrap 5
- **数据库**: SQLite3
- **PDF生成**: xhtml2pdf
- **图表**: Chart.js

## 安装与运行

### 1. 安装依赖

```bash
cd /workspace/finance-receipt-app
pip3 install -r requirements.txt
```

### 2. 初始化数据库

```bash
python3 init_db.py
```

### 3. 启动应用

```bash
python3 app.py
```

应用将在 http://localhost:5000 启动。

## 项目结构

```
finance-receipt-app/
├── app.py                 # Flask主应用（API路由和页面渲染）
├── database.py            # 数据库操作类
├── pdf_generator.py       # PDF生成模块
├── init_db.py            # 数据库初始化脚本
├── requirements.txt       # Python依赖
├── static/              # 静态文件（CSS、JS、图片）
├── templates/           # HTML模板
│   ├── base.html        # 基础模板
│   ├── dashboard.html   # 仪表盘
│   ├── generate.html    # 开具收据
│   ├── receipts.html    # 收据列表
│   ├── receipt_detail.html  # 收据详情
│   ├── templates.html   # 模板管理
│   └── statistics.html  # 数据统计
├── receipts_pdf/        # 生成的PDF存储目录
└── instance/
    └── receipts.db      # SQLite数据库文件
```

## 使用说明

### 开具新收据

1. 点击左侧菜单"开具收据"
2. 填写付款方、金额、收款事由等信息
3. 点击"自动生成"按钮生成收据编号
4. 输入金额和税率，系统自动计算税额和总额
5. 点击"保存收据"或"保存并生成PDF"

### 管理收据

1. 点击左侧菜单"收据管理"
2. 查看所有收据列表
3. 使用搜索框搜索收据
4. 使用筛选器按币种或日期筛选
5. 点击操作按钮查看详情、下载PDF或删除

### 数据统计

1. 点击左侧菜单"数据统计"
2. 查看收据统计卡片
3. 查看月度趋势图表
4. 查看币种分布图表
5. 查看付款方统计

## API接口

### 收据管理
- `GET /api/receipts` - 获取收据列表
- `POST /api/receipts` - 创建新收据
- `GET /api/receipts/<id>` - 获取收据详情
- `PUT /api/receipts/<id>` - 更新收据
- `DELETE /api/receipts/<id>` - 删除收据
- `GET /api/receipts/<id>/pdf` - 生成并下载PDF
- `GET /api/receipts/generate-number` - 生成新收据编号

### 模板管理
- `GET /api/templates` - 获取所有模板
- `POST /api/templates` - 创建新模板

### 统计
- `GET /api/statistics/summary` - 获取统计摘要

## 数据库结构

### receipts表（收据记录）
- id: 主键
- receipt_number: 收据编号
- payer_name: 付款方名称
- payer_tax_id: 付款方税号
- amount: 金额
- currency: 币种
- payment_date: 付款日期
- purpose: 收款事由
- payee_name: 收款方名称
- payee_tax_id: 收款方税号
- tax_rate: 税率
- tax_amount: 税额
- total_amount: 总金额
- notes: 备注
- template_type: 模板类型
- created_at: 创建时间
- updated_at: 更新时间

## 后续开发计划

- [ ] 完善模板编辑功能
- [ ] 完善模板删除功能
- [ ] 实现数据统计图表数据接口
- [ ] 实现数据导出Excel功能
- [ ] 添加用户认证系统
- [ ] 支持邮件发送PDF
- [ ] 支持批量生成收据
- [ ] 添加更多预设模板

## 许可证

MIT License

## 作者

WorkBuddy AI Agent
