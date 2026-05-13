#!/usr/bin/env python3
"""
Flask主应用
"""
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
from flask_cors import CORS
import pdf_generator
import os
import json
import hashlib
import uuid
from datetime import datetime
from database import Database
import openpyxl
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'finance-receipt-secret-key-2024')

CORS(app)

db = Database()

# ==================== 认证相关 ====================

ADMIN_FILE = os.path.join("data", "admin.json")
SESSION_FILE = os.path.join("data", "sessions.json")


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def get_admin_config():
    if not os.path.exists(ADMIN_FILE):
        os.makedirs("data", exist_ok=True)
        default_config = {
            "username": "admin",
            "password": hash_password("admin123"),
            "receipt_prefix": "RCP",
            "receipt_seq": 0,
            "last_reset_date": datetime.now().strftime("%Y%m%d")
        }
        with open(ADMIN_FILE, "w", encoding="utf-8") as fp:
            json.dump(default_config, fp, ensure_ascii=False, indent=2)
        return default_config
    with open(ADMIN_FILE, "r", encoding="utf-8") as fp:
        return json.load(fp)


def save_admin_config(config):
    os.makedirs("data", exist_ok=True)
    with open(ADMIN_FILE, "w", encoding="utf-8") as fp:
        json.dump(config, fp, ensure_ascii=False, indent=2)


def get_sessions():
    if not os.path.exists(SESSION_FILE):
        return {}
    with open(SESSION_FILE, "r", encoding="utf-8") as fp:
        return json.load(fp)


def save_sessions(sessions):
    os.makedirs("data", exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as fp:
        json.dump(sessions, fp, ensure_ascii=False, indent=2)


def create_session(username):
    token = str(uuid.uuid4())
    sessions = get_sessions()
    sessions[token] = {
        "username": username,
        "created_at": datetime.now().isoformat()
    }
    save_sessions(sessions)
    return token


def validate_session(token):
    if not token:
        return False
    sessions = get_sessions()
    return token in sessions


def destroy_session(token):
    sessions = get_sessions()
    if token in sessions:
        del sessions[token]
        save_sessions(sessions)


def require_auth(f):
    """装饰器：要求管理员登录"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = session.get('admin_token', '')
        if not validate_session(token):
            return jsonify({'error': '请先登录', 'need_login': True}), 401
        return f(*args, **kwargs)
    return decorated


# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/generate')
def generate():
    return render_template('generate.html')


@app.route('/receipts')
def receipt_list():
    return render_template('receipts.html')


@app.route('/receipt/<int:receipt_id>')
def receipt_detail(receipt_id):
    return render_template('receipt_detail.html', receipt_id=receipt_id)


@app.route('/templates')
def templates_page():
    return render_template('templates.html')


@app.route('/statistics')
def statistics_page():
    return render_template('statistics.html')


@app.route('/batch')
def batch_page():
    return render_template('batch.html')


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


# ==================== 认证API ====================

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json(force=True)
        username = data.get('username', '')
        password = data.get('password', '')

        config = get_admin_config()
        if username == config['username'] and hash_password(password) == config['password']:
            token = create_session(username)
            session['admin_token'] = token
            return jsonify({'success': True, 'token': token, 'username': username})
        return jsonify({'error': '用户名或密码错误'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def admin_logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = session.get('admin_token', '')
    destroy_session(token)
    session.pop('admin_token', None)
    return jsonify({'success': True})


@app.route('/api/auth/check', methods=['GET'])
def auth_check():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = session.get('admin_token', '')
    if validate_session(token):
        config = get_admin_config()
        return jsonify({'logged_in': True, 'username': config['username']})
    return jsonify({'logged_in': False})


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    try:
        data = request.get_json(force=True)
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        config = get_admin_config()
        if hash_password(old_password) != config['password']:
            return jsonify({'error': '原密码错误'}), 400
        if len(new_password) < 6:
            return jsonify({'error': '新密码至少6位'}), 400

        config['password'] = hash_password(new_password)
        save_admin_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 管理员API ====================

@app.route('/api/admin/receipt-number-config', methods=['GET'])
@require_auth
def get_receipt_number_config():
    config = get_admin_config()
    return jsonify({
        'prefix': config.get('receipt_prefix', 'RCP'),
        'seq': config.get('receipt_seq', 0),
        'last_reset_date': config.get('last_reset_date', '')
    })


@app.route('/api/admin/receipt-number-config', methods=['PUT'])
@require_auth
def update_receipt_number_config():
    try:
        data = request.get_json(force=True)
        config = get_admin_config()

        if 'prefix' in data:
            prefix = data['prefix'].strip().upper()
            if not prefix:
                return jsonify({'error': '编号前缀不能为空'}), 400
            config['receipt_prefix'] = prefix

        if 'reset_seq' in data and data['reset_seq']:
            config['receipt_seq'] = 0
            config['last_reset_date'] = datetime.now().strftime("%Y%m%d")

        if 'set_seq' in data:
            config['receipt_seq'] = int(data['set_seq'])

        save_admin_config(config)
        return jsonify({
            'success': True,
            'prefix': config['receipt_prefix'],
            'seq': config['receipt_seq']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
@require_auth
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

        # 判断是否内联预览
        inline = request.args.get('inline', '0')
        if inline == '1':
            return send_file(pdf_path, as_attachment=False,
                            mimetype='application/pdf')
        return send_file(pdf_path, as_attachment=True,
                        download_name=f"收据_{receipt['receipt_number']}.pdf",
                        mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/receipts/<int:receipt_id>/preview', methods=['GET'])
def preview_receipt_html(receipt_id):
    """返回收据HTML用于页面内预览"""
    try:
        receipt = db.get_receipt(receipt_id)
        if not receipt:
            return jsonify({'error': '收据不存在'}), 404
        template = db.get_default_template()
        template_html = template['template_html'] if template else None
        html_content = pdf_generator.render_template(template_html or pdf_generator.get_default_template_html(), receipt)
        return html_content
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/receipts/preview-html', methods=['POST'])
def preview_receipt_from_data():
    """根据表单数据返回HTML预览（不保存收据）"""
    try:
        data = request.get_json(force=True)
        # 确保必要字段
        if 'amount' in data:
            amount = float(data['amount'])
            tax_rate = float(data.get('tax_rate', 0))
            data['tax_amount'] = round(amount * tax_rate / 100, 2)
            data['total_amount'] = round(amount + data['tax_amount'], 2)

        template = db.get_default_template()
        template_html = template['template_html'] if template else None
        html_content = pdf_generator.render_template(template_html or pdf_generator.get_default_template_html(), data)
        return html_content
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/receipts/generate-number', methods=['GET'])
def generate_number():
    try:
        return jsonify({'receipt_number': db.generate_receipt_number()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 付款人/收款人API ====================

@app.route('/api/payers', methods=['GET'])
def get_payers():
    try:
        keyword = request.args.get('keyword', '')
        return jsonify({'payers': db.get_payers(keyword if keyword else None)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/payees', methods=['GET'])
def get_payees():
    try:
        keyword = request.args.get('keyword', '')
        return jsonify({'payees': db.get_payees(keyword if keyword else None)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 批量导入API ====================

@app.route('/api/batch/import', methods=['POST'])
def batch_import():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '请上传Excel文件'}), 400
        file = request.files['file']
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': '请上传.xlsx格式的Excel文件'}), 400

        wb = openpyxl.load_workbook(file)
        ws = wb.active

        # 解析表头（第1行）
        headers = []
        for col in range(1, ws.max_column + 1):
            val = ws.cell(row=1, column=col).value
            headers.append(str(val) if val else '')

        # 解析数据行（从第2行开始）
        results = []
        errors = []
        for row_idx in range(2, ws.max_row + 1):
            try:
                row_data = {}
                for col_idx, header in enumerate(headers, 1):
                    row_data[header] = ws.cell(row=row_idx, column=col_idx).value

                # 提取字段
                payment_date = row_data.get('填制日期', '')
                if isinstance(payment_date, datetime):
                    payment_date = payment_date.strftime('%Y-%m-%d')

                payer_name = row_data.get('付款人名称', '') or row_data.get('名称', '')
                payer_tax_id = row_data.get('付款人税号', '') or row_data.get('税号', '')
                payee_name = row_data.get('收款人', '')
                payee_tax_id = row_data.get('收款人税号', '')

                # 计算各项金额
                items = []
                total = 0
                for key in ['代收代付社保', '代收代付公积金', '代收代付工资',
                           '代收代付个税', '代收代付商险', '代收代付福利', '代收代付其他']:
                    val = row_data.get(key, 0)
                    if val:
                        try:
                            amount = float(val)
                            if amount > 0:
                                items.append({'name': key.replace('代收代付', ''), 'amount': amount})
                                total += amount
                        except:
                            pass

                if not payer_name or total <= 0:
                    continue

                # 生成收据
                receipt_data = {
                    'receipt_number': db.generate_receipt_number(),
                    'payer_name': payer_name,
                    'payer_tax_id': str(payer_tax_id) if payer_tax_id else '',
                    'amount': total,
                    'currency': 'CNY',
                    'payment_date': str(payment_date) if payment_date else datetime.now().strftime('%Y-%m-%d'),
                    'purpose': '、'.join([i['name'] + '：' + str(i['amount']) for i in items]),
                    'payee_name': str(payee_name) if payee_name else '北京厚泽人力资源有限公司',
                    'payee_tax_id': str(payee_tax_id) if payee_tax_id else '',
                    'tax_rate': 0,
                    'tax_amount': 0,
                    'total_amount': total,
                    'notes': str(row_data.get('备注', '')) if row_data.get('备注') else ''
                }
                receipt_id = db.create_receipt(receipt_data)
                results.append({'id': receipt_id, 'receipt_number': receipt_data['receipt_number']})
            except Exception as e:
                errors.append({'row': row_idx, 'error': str(e)})

        return jsonify({
            'success': True,
            'created': len(results),
            'receipts': results,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/batch/template', methods=['GET'])
def download_template():
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "批量导入模板"

        # 表头
        headers = ['填制日期', '付款人名称', '付款人税号', '收款人', '收款人税号',
                   '代收代付社保', '代收代付公积金', '代收代付工资', '代收代付个税',
                   '代收代付商险', '代收代付福利', '代收代付其他', '合计', '备注']
        ws.append(headers)

        # 示例数据
        example = ['2026-05-13', '天津俊途企业管理咨询有限公司', '9112010175484682X1',
                   '北京厚泽人力资源有限公司', '911101055825295879',
                   '', '', '23399.77', '', '', '', '', '23399.77', 'C0247CL001171EZ\n2026.1']
        ws.append(example)

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return send_file(output, as_attachment=True,
                        download_name='批量导入模板.xlsx',
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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
@require_auth
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
    # 初始化管理员配置
    get_admin_config()
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("财务收据生成应用启动成功！")
    print(f"访问地址: http://localhost:{port}")
    print("默认管理员: admin / admin123")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
