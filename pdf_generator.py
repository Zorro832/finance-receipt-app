#!/usr/bin/env python3
"""
PDF生成模块
使用xhtml2pdf将HTML转换为PDF
"""
from xhtml2pdf import pisa
from io import BytesIO
import os
import sys
from datetime import datetime

def get_base_path():
    """获取应用根目录（打包后也能正常工作）"""
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        return os.path.dirname(sys.executable)
    else:
        # 开发时的路径
        return os.path.abspath(os.path.dirname(__file__))

def generate_pdf(receipt: dict, template_html: str = None) -> str:
    """
    生成PDF文件
    
    Args:
        receipt: 收据数据字典
        template_html: HTML模板（如果为None则使用默认模板）
    
    Returns:
        PDF文件的路径
    """
    # 如果没有提供模板，使用默认模板
    if not template_html:
        template_html = get_default_template_html()
    
    # 替换模板中的变量
    html_content = render_template(template_html, receipt)
    
    # 生成PDF文件名
    pdf_filename = f"receipt_{receipt['receipt_number']}.pdf"
    base_path = get_base_path()
    pdf_dir = os.path.join(base_path, 'receipts_pdf')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    # 生成PDF
    with open(pdf_path, 'wb') as pdf_file:
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=pdf_file,
            encoding='UTF-8'
        )
    
    if pisa_status.err:
        raise Exception("PDF生成失败")
    
    return pdf_path

def render_template(template: str, data: dict) -> str:
    """
    简单的模板渲染函数
    替换模板中的 {{ variable }} 占位符
    """
    # 添加货币符号
    currency_symbols = {
        'CNY': '¥',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥'
    }
    
    data['currency_symbol'] = currency_symbols.get(data.get('currency', 'CNY'), '$')
    
    # 格式化日期和时间
    if 'created_at' in data and data['created_at']:
        if isinstance(data['created_at'], str):
            data['created_at'] = data['created_at'].replace('T', ' ').split('.')[0]
    
    # 替换模板变量
    html = template
    for key, value in data.items():
        placeholder = '{{ ' + key + ' }}'
        html = html.replace(placeholder, str(value) if value is not None else '')
    
    return html

def get_default_template_html() -> str:
    """获取默认模板HTML"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body { 
                font-family: Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
            }
            .receipt { max-width: 800px; margin: 0 auto; }
            .header { 
                text-align: center; 
                margin-bottom: 30px;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
            }
            .title { 
                font-size: 32px; 
                font-weight: bold; 
                margin-bottom: 10px;
            }
            .subtitle { 
                font-size: 14px; 
                color: #666; 
            }
            .info-table { 
                width: 100%; 
                border-collapse: collapse; 
                margin: 20px 0; 
            }
            .info-table td { 
                padding: 12px; 
                border: 1px solid #ddd; 
                vertical-align: top;
            }
            .info-table .label { 
                background: #f5f5f5; 
                font-weight: bold; 
                width: 120px; 
                text-align: center;
            }
            .amount { 
                font-size: 18px; 
                font-weight: bold; 
                color: #d32f2f; 
            }
            .footer { 
                margin-top: 50px; 
                text-align: center; 
                font-size: 12px; 
                color: #999; 
                border-top: 1px solid #ddd;
                padding-top: 20px;
            }
            .seal-area {
                margin-top: 60px;
                text-align: right;
                padding-right: 50px;
            }
            .seal-line {
                display: inline-block;
                border-top: 2px solid #333;
                width: 150px;
                padding-top: 10px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <div class="title">财务收据</div>
                <div class="subtitle">FINANCIAL RECEIPT</div>
            </div>
            
            <table class="info-table">
                <tr>
                    <td class="label">收据编号</td>
                    <td>{{ receipt_number }}</td>
                    <td class="label">日期</td>
                    <td>{{ payment_date }}</td>
                </tr>
                <tr>
                    <td class="label">付款方</td>
                    <td>{{ payer_name }}</td>
                    <td class="label">付款方税号</td>
                    <td>{{ payer_tax_id }}</td>
                </tr>
                <tr>
                    <td class="label">收款事由</td>
                    <td colspan="3">{{ purpose }}</td>
                </tr>
                <tr>
                    <td class="label">金额</td>
                    <td class="amount" colspan="3">{{ currency_symbol }}{{ amount }}</td>
                </tr>
                <tr>
                    <td class="label">税率</td>
                    <td>{{ tax_rate }}%</td>
                    <td class="label">税额</td>
                    <td>{{ currency_symbol }}{{ tax_amount }}</td>
                </tr>
                <tr>
                    <td class="label">总金额</td>
                    <td class="amount" colspan="3">{{ currency_symbol }}{{ total_amount }}</td>
                </tr>
                <tr>
                    <td class="label">收款方</td>
                    <td>{{ payee_name }}</td>
                    <td class="label">收款方税号</td>
                    <td>{{ payee_tax_id }}</td>
                </tr>
                <tr>
                    <td class="label">备注</td>
                    <td colspan="3">{{ notes }}</td>
                </tr>
            </table>
            
            <div class="seal-area">
                <div class="seal-line">收款方签章</div>
            </div>
            
            <div class="footer">
                <p>本收据由系统自动生成，无需签字盖章</p>
                <p>生成时间：{{ created_at }}</p>
            </div>
        </div>
    </body>
    </html>
    '''
