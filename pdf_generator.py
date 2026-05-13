#!/usr/bin/env python3
"""
PDF生成模块
使用xhtml2pdf将HTML转换为PDF
"""
from xhtml2pdf import pisa
import os
import sys


def num_to_chinese(num):
    """数字转中文大写"""
    num = float(num)
    units = ['', '拾', '佰', '仟']
    nums = '零壹贰叁肆伍陆柒捌玖'
    decimal_unit = ['角', '分']
    
    integer_part = int(num)
    decimal_part = round((num - integer_part) * 100)
    
    if integer_part == 0 and decimal_part == 0:
        return '零元整'
    
    result = ''
    
    # 处理整数部分
    if integer_part > 0:
        str_int = str(integer_part)
        length = len(str_int)
        zero_flag = False
        
        for i, digit in enumerate(str_int):
            n = int(digit)
            pos = length - i - 1
            
            if n == 0:
                if not zero_flag and pos % 4 == 0 and pos > 0:
                    result += '零'
                    zero_flag = True
            else:
                zero_flag = False
                result += nums[n] + units[pos % 4]
            
            if pos % 4 == 0 and pos > 0:
                if pos == 4:
                    result += '万'
                elif pos == 8:
                    result += '亿'
        
        result += '元'
    else:
        result = '零元'
    
    # 处理小数部分
    if decimal_part > 0:
        jiao = decimal_part // 10
        fen = decimal_part % 10
        if jiao > 0:
            result += nums[jiao] + '角'
        if fen > 0:
            result += nums[fen] + '分'
    else:
        result += '整'
    
    return result


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.dirname(__file__))


def generate_pdf(receipt: dict, template_html: str = None) -> str:
    if not template_html:
        template_html = get_default_template_html()
    
    html_content = render_template(template_html, receipt)
    
    pdf_filename = f"receipt_{receipt['receipt_number']}.pdf"
    base_path = get_base_path()
    pdf_dir = os.path.join(base_path, 'receipts_pdf')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    with open(pdf_path, 'wb') as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file, encoding='UTF-8')
    
    if pisa_status.err:
        raise Exception("PDF生成失败")
    
    return pdf_path


def render_template(template: str, data: dict) -> str:
    currency_symbols = {'CNY': '¥', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
    data['currency_symbol'] = currency_symbols.get(data.get('currency', 'CNY'), '¥')
    
    # 金额大写
    total = float(data.get('total_amount', 0))
    data['total_amount_cn'] = num_to_chinese(total)
    
    # 格式化日期
    if 'created_at' in data and data['created_at']:
        if isinstance(data['created_at'], str):
            data['created_at'] = data['created_at'].replace('T', ' ').split('.')[0]
    
    # 处理多行项目
    purpose = data.get('purpose', '')
    items = []
    if purpose:
        for item in purpose.split('、'):
            if item.strip():
                items.append({'name': item.strip(), 'amount': ''})
    
    # 如果没有项目，显示空行
    if not items:
        items = [{'name': '', 'amount': ''}]
    
    # 生成项目HTML
    items_html = ''
    for item in items:
        items_html += f'<tr><td class="left-align" colspan="4">{item["name"]}</td><td class="right-align" colspan="4">{item["amount"]}</td></tr>\n'
    
    # 填充空行（至少显示5行）
    for _ in range(max(0, 5 - len(items))):
        items_html += '<tr><td class="left-align" colspan="4">&nbsp;</td><td class="right-align" colspan="4">&nbsp;</td></tr>\n'
    
    data['items_html'] = items_html
    data['issuer'] = data.get('issuer', '张军')
    
    # 替换模板变量
    html = template
    for key, value in data.items():
        placeholder = '{{ ' + key + ' }}'
        html = html.replace(placeholder, str(value) if value is not None else '')
    
    return html


def get_default_template_html() -> str:
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page { size: A4; margin: 1.5cm; }
body { font-family: "SimSun", "宋体", serif; font-size: 14px; line-height: 1.6; }
.receipt { width: 100%; max-width: 800px; margin: 0 auto; }
.header { text-align: center; margin-bottom: 20px; }
.company-name { font-size: 24px; font-weight: bold; }
.receipt-title { font-size: 20px; font-weight: bold; margin-top: 5px; }
.info-row { display: flex; justify-content: space-between; margin: 10px 0; font-size: 13px; }
.main-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
.main-table td, .main-table th { border: 1px solid #333; padding: 8px; text-align: center; }
.main-table .label { background: #f5f5f5; font-weight: bold; }
.main-table .left-align { text-align: left; }
.main-table .right-align { text-align: right; }
.total-row { font-weight: bold; }
.total-row .amount { font-size: 16px; color: #000; }
.footer-row { font-size: 12px; }
.sign-area { display: flex; justify-content: space-between; margin-top: 30px; padding: 0 20px; }
.sign-area .sign-box { text-align: center; }
.sign-area .sign-line { border-top: 1px solid #333; width: 120px; margin-top: 30px; padding-top: 5px; }
.bottom-note { margin-top: 20px; font-size: 11px; color: #666; text-align: center; }
</style>
</head>
<body>
<div class="receipt">
<div class="header">
<div class="company-name">北京厚泽人力资源有限公司</div>
<div class="receipt-title">电子收据</div>
</div>
<div class="info-row">
<div class="left">填制日期：{{ payment_date }}</div>
<div class="right">票号：{{ receipt_number }}</div>
</div>
<table class="main-table">
<tr>
<td class="label" rowspan="2" style="width:40px;">付款人</td>
<td class="label left-align">名称：</td>
<td class="left-align" colspan="2">{{ payer_name }}</td>
<td class="label" rowspan="2" style="width:40px;">收款人</td>
<td class="label left-align">名称：</td>
<td class="left-align" colspan="2">{{ payee_name }}</td>
</tr>
<tr>
<td class="label left-align">统一社会信用代码：</td>
<td class="left-align" colspan="2">{{ payer_tax_id }}</td>
<td class="label left-align">统一社会信用代码：</td>
<td class="left-align" colspan="2">{{ payee_tax_id }}</td>
</tr>
<tr>
<td class="label" colspan="4">收款内容</td>
<td class="label" colspan="4">金额</td>
</tr>
{{ items_html }}
<tr class="total-row">
<td class="label" colspan="2">合计金额（大写）：</td>
<td class="left-align" colspan="2">{{ total_amount_cn }}</td>
<td class="label" colspan="2">合计金额（小写）：</td>
<td class="right-align amount" colspan="2">{{ total_amount }}</td>
</tr>
<tr class="footer-row">
<td class="label" colspan="2">备注</td>
<td class="left-align" colspan="6">{{ notes }}</td>
</tr>
</table>
<div class="sign-area">
<div class="sign-box">
<div>开具人：{{ issuer }}</div>
</div>
<div class="sign-box">
<div class="sign-line">收款单位（盖章）</div>
</div>
</div>
<div class="bottom-note">
<p>本收据仅作对账使用，款项未实际到账前不视为已收款。</p>
<p>本收据由【快收据】平台开具，【腾讯云CA】认证，您可微信扫码或访问https://ksj.yimion.com 查验。</p>
</div>
</div>
</body>
</html>"""
