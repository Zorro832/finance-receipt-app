#!/usr/bin/env python3
"""
Flask主应用
实现所有API接口和前端页面路由
"""
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import pdf_generator
import os
from datetime import datetime
from database import Database

# 初始化Flask应用
app = Flask(__name__)
CORS(app)

# 初始化数据库（JSON文件存储）
db = Database()

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
def receipt_list():
    """收据列表页面"""
    return render_template('receipts.html')

@app.route('/receipt/<int:receipt_id>')
def receipt_detail(receipt_id):
    """收据详情页面"""
    return render_template('receipt_detail.html', receipt_id=receipt_id)

@app.route('/templates')
def templates_page():
    """模板管理页面"""
    return render_template('templates.html')

@app.route('/statistics')
def statistics_page():
    """数据统计页面"""
    return render_template('statistics.html')

# ==================== 收据管理API ====================

@app.route('/api/receipts', methods=['GET'])
def get_receipts():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '')
        currency = request.args.get('currency', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        result = db.get_receipts(page=page, limit=limit,
                              search=search if search else None,
                              currency=currency if currency else None,
                              date_from=date_from if date_from else None,
                              date_to=date_to if date_to else None)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts', methods=['POST'])
def create_receipt():
    try:
        data = request.get_json(force=True)
        required_fields = ['payer_name', 'amount', 'payment_date', 'purpose', 'payee_name']
        for f in required_fields:
            if f not in data or not data[f]:
                return jsonify({'error': f'缺少必填字段: {f}'}), 400

        if 'receipt_number' not in data or not data['receipt_number']:
            data['receipt_number'] = db.generate_receipt_number()
        amount = float(data['amount'])
        tax_rate = float(data.get('tax_rate', 0))
        tax_amount = amount * tax_rate / 100
        data['tax_amount'] = round(tax_amount, 2)
        data['total_amount'] = round(amount + tax_amount, 2)

        receipt_id = db.create_receipt(data)
        return jsonify({'success': True, 'receipt_id': receipt_id, 'receipt_number': data['receipt_number']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>', methods=['GET'])
def get_receipt_detail(receipt_id):
    try:
        receipt = db.get_receipt(receipt_id)
        if not receipt:
            return jsonify({'error': '收据不存在'}), 404
        currency_symbols = {'CNY': '¥', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
        receipt['currency_symbol'] = currency_symbols.get(receipt['currency'], '$')
        return jsonify(receipt)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>', methods=['PUT'])
def update_receipt(receipt_id):
    try:
        data = request.get_json(force=True)
        if 'amount' in data:
            amount = float(data['amount'])
            tax_rate = float(data.get('tax_rate', 0))
            data['tax_amount'] = round(amount * tax_rate / 100, 2)
            data['total_amount'] = round(amount + data['tax_amount'], 2)
        success = db.update_receipt(receipt_id, data)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>', methods=['DELETE'])
def delete_receipt(receipt_id):
    try:
        success = db.delete_receipt(receipt_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/<int:receipt_id>/pdf', methods=['GET'])
def generate_receipt_pdf(receipt_id):
    try:
        receipt = db.get_receipt(receipt_id)
        if not receipt:
            return jsonify({'error': '收据不存在'}), 404
        template = db.get_default_template()
        template_html = template['template_html'] if template else None
        pdf_path = pdf_generator.generate_pdf(receipt, template_html)
        return send_file(pdf_path, as_attachment=True,
                        download_name=f"收据_{receipt['receipt_number']}.pdf",
                        mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/receipts/generate-number', methods=['GET'])
def generate_number():
    try:
        return jsonify({'receipt_number': db.generate_receipt_number()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 模板管理API ====================

@app.route('/api/templates', methods=['GET'])
def get_templates():
    try:
        return jsonify({'templates': db.get_templates()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates', methods=['POST'])
def create_template():
    try:
        data = request.get_json(force=True)
        if 'name' not in data or not data['name']:
            return jsonify({'error': '模板名称不能为空'}), 400
        if 'template_html' not in data or not data['template_html']:
            return jsonify({'error': '模板内容不能为空'}), 400
        template_id = db.create_template(data)
        return jsonify({'success': True, 'template_id': template_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 统计API ====================

@app.route('/api/statistics/summary', methods=['GET'])
def get_statistics_summary():
    try:
        return jsonify(db.get_statistics_summary())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 错误及启动 ====================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': '接口不存在'}), 404
    return render_template('dashboard.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    os.makedirs('receipts_pdf', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    db.init_default_templates()
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("财务收据生成应用启动成功！")
    print(f"访问地址: http://localhost:{port}")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
