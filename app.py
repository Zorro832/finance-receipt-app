#!/usr/bin/env python3
"""
Flask主应用
实现所有API接口和前端页面路由
"""
from flask import Flask, request, jsonify, render_template, send_file, make_response
from flask_cors import CORS
from database import Database
import pdf_generator
import os
import sys
from datetime import datetime
from typing import Dict, Any

# 获取应用根目录（打包后也能正常工作）
if getattr(sys, 'frozen', False):
    # 打包后的路径
    basedir = sys._MEIPASS
    instance_path = os.path.dirname(sys.executable)
else:
    # 开发时的路径
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = basedir

# 初始化Flask应用
app = Flask(__name__, 
            template_folder=os.path.join(basedir, 'templates'),
            static_folder=os.path.join(basedir, 'static'))
CORS(app)

# 初始化数据库
db = Database(db_path=os.path.join(instance_path, 'instance', 'receipts.db'))

# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    """首页 - 仪表盘"""
    return render_template('dashboard.html')

@app.route('/generate')
def generate():
    """收据生成页面"""
    return render_template('generate.html')

@app.route('/receipts')
def receipts_list():
    """收据列表页面"""
    return render_template('receipts.html')

@app.route('/receipt/<int:receipt_id>')
def receipt_detail(receipt_id):
    """收据详情页面"""
    return render_template('receipt_detail.html', receipt_id=receipt_id)

@app.route('/templates')
def templates():
    """模板管理页面"""
    return render_template('templates.html')

@app.route('/statistics')
def statistics():
    """数据统计页面"""
    return render_template('statistics.html')

# ==================== API路由 - 收据管理 ====================

@app.route('/api/receipts', methods=['GET'])
def get_receipts():
    """获取收据列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '')
        currency = request.args.get('currency', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        result = db.get_receipts(
            page=page,
            limit=limit,
            search=search if search else None,
            currency=currency if currency else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts', methods=['POST'])
def create_receipt():
    """创建新收据"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['payer_name', 'amount', 'payment_date', 'purpose', 'payee_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'缺少必填字段: {field}'}), 400
        
        # 自动生成收据编号
        if 'receipt_number' not in data or not data['receipt_number']:
            data['receipt_number'] = db.generate_receipt_number()
        
        # 计算税额和总额
        amount = float(data['amount'])
        tax_rate = float(data.get('tax_rate', 0))
        tax_amount = amount * tax_rate / 100
        total_amount = amount + tax_amount
        
        data['tax_amount'] = round(tax_amount, 2)
        data['total_amount'] = round(total_amount, 2)
        
        receipt_id = db.create_receipt(data)
        
        return jsonify({
            'success': True,
            'receipt_id': receipt_id,
            'receipt_number': data['receipt_number']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>', methods=['GET'])
def get_receipt(receipt_id):
    """获取单个收据详情"""
    try:
        receipt = db.get_receipt(receipt_id)
        if not receipt:
            return jsonify({'error': '收据不存在'}), 404
        
        # 添加货币符号
        currency_symbols = {
            'CNY': '¥',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥'
        }
        receipt['currency_symbol'] = currency_symbols.get(receipt['currency'], '$')
        
        return jsonify(receipt)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>', methods=['PUT'])
def update_receipt(receipt_id):
    """更新收据"""
    try:
        data = request.get_json()
        
        # 计算税额和总额
        if 'amount' in data:
            amount = float(data['amount'])
            tax_rate = float(data.get('tax_rate', 0))
            tax_amount = amount * tax_rate / 100
            total_amount = amount + tax_amount
            
            data['tax_amount'] = round(tax_amount, 2)
            data['total_amount'] = round(total_amount, 2)
        
        success = db.update_receipt(receipt_id, data)
        
        if not success:
            return jsonify({'error': '收据不存在'}), 404
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>', methods=['DELETE'])
def delete_receipt(receipt_id):
    """删除收据"""
    try:
        success = db.delete_receipt(receipt_id)
        
        if not success:
            return jsonify({'error': '收据不存在'}), 404
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>/pdf', methods=['GET'])
def generate_receipt_pdf(receipt_id):
    """生成并下载PDF"""
    try:
        receipt = db.get_receipt(receipt_id)
        if not receipt:
            return jsonify({'error': '收据不存在'}), 404
        
        # 获取模板
        template = db.get_default_template()
        template_html = template['template_html'] if template else None
        
        # 生成PDF
        pdf_path = pdf_generator.generate_pdf(receipt, template_html)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"收据_{receipt['receipt_number']}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/generate-number', methods=['GET'])
def generate_number():
    """生成新的收据编号"""
    try:
        receipt_number = db.generate_receipt_number()
        return jsonify({'receipt_number': receipt_number})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== API路由 - 模板管理 ====================

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """获取所有模板"""
    try:
        templates = db.get_templates()
        return jsonify({'templates': templates})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates', methods=['POST'])
def create_template():
    """创建新模板"""
    try:
        data = request.get_json()
        
        if 'name' not in data or not data['name']:
            return jsonify({'error': '模板名称不能为空'}), 400
        
        if 'template_html' not in data or not data['template_html']:
            return jsonify({'error': '模板内容不能为空'}), 400
        
        template_id = db.create_template(data)
        
        return jsonify({
            'success': True,
            'template_id': template_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """更新模板"""
    # TODO: 实现模板更新逻辑
    return jsonify({'error': '暂未实现'}), 501

@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """删除模板"""
    # TODO: 实现模板删除逻辑
    return jsonify({'error': '暂未实现'}), 501

# ==================== API路由 - 统计 ====================

@app.route('/api/statistics/summary', methods=['GET'])
def get_statistics_summary():
    """获取统计摘要"""
    try:
        summary = db.get_statistics_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

# ==================== 启动应用 ====================

if __name__ == '__main__':
    # 确保PDF存储目录和数据库目录存在
    os.makedirs('receipts_pdf', exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    
    # 初始化默认模板
    db.init_default_templates()
    
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("财务收据生成应用启动成功！")
    print(f"访问地址: http://localhost:{port}")
    print("="*50)
    
    app.run(debug=False, host='0.0.0.0', port=port)
