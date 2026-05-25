#!/usr/bin/env python3
"""
PDF生成模块
使用xhtml2pdf将HTML转换为PDF
"""
from xhtml2pdf import pisa
from xhtml2pdf.default import DEFAULT_CSS
import os
import sys
import base64


# 注册中文字体 - 使用reportlab内置CID字体（跨平台无需额外字体文件）
def _register_cjk_fonts():
    """注册中文字体以支持PDF中文显示"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    except Exception as e:
        print(f"Warning: Failed to register STSong-Light: {e}")

_register_cjk_fonts()


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


def get_seal_base64():
    """获取财务章图片的base64编码"""
    seal_path = os.path.join(get_base_path(), 'static', 'seal.png')
    if os.path.exists(seal_path):
        with open(seal_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return ''


def generate_pdf(receipt: dict, template_html: str = None) -> str:
    if not template_html:
        template_html = get_default_template_html()

    html_content = render_template(template_html, receipt)

    pdf_filename = f"receipt_{receipt['receipt_number']}.pdf"
    base_path = get_base_path()
    pdf_dir = os.path.join(base_path, 'receipts_pdf')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    # link callback for xhtml2pdf to resolve local file paths
    def link_callback(uri, rel):
        if uri.startswith('/') or uri.startswith('file://'):
            return uri.replace('file://', '')
        return os.path.join(base_path, uri)

    with open(pdf_path, 'wb') as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file, encoding='UTF-8',
                                      link_callback=link_callback)

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
        parts = purpose.split('、')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if ':' in part:
                name, amt = part.split(':', 1)
                items.append({'name': name.strip(), 'amount': amt.strip()})
            elif '：' in part:
                name, amt = part.split('：', 1)
                items.append({'name': name.strip(), 'amount': amt.strip()})
            else:
                items.append({'name': part, 'amount': ''})

    if not items:
        items = [{'name': '', 'amount': ''}]

    # 生成项目HTML - 4列表格: colspan=2 for 收款内容, colspan=2 for 金额
    items_html = ''
    for item in items:
        amt_display = item["amount"] if item["amount"] else ''
        items_html += '<tr><td colspan="2" style="text-align:left; padding:5px 8px; border:1px solid #333;">' + item["name"] + '</td><td colspan="2" style="text-align:right; padding:5px 8px; border:1px solid #333;">' + amt_display + '</td></tr>\n'

    # 填充空行（至少显示4行）
    for _ in range(max(0, 4 - len(items))):
        items_html += '<tr><td colspan="2" style="padding:5px 8px; border:1px solid #333;">&nbsp;</td><td colspan="2" style="padding:5px 8px; border:1px solid #333;">&nbsp;</td></tr>\n'

    data['items_html'] = items_html
    data['issuer'] = data.get('issuer', '陈婷')

    # 金额格式化
    total_amount = data.get('total_amount', 0)
    if isinstance(total_amount, (int, float)):
        data['total_amount_display'] = '{:,.2f}'.format(total_amount)
    else:
        data['total_amount_display'] = str(total_amount)

    # 财务章图片 - xhtml2pdf不支持base64，使用文件路径
    seal_path = os.path.join(get_base_path(), 'static', 'seal.png')
    if os.path.exists(seal_path):
        data['seal_img'] = '<img src="' + seal_path + '" style="width:80px; height:80px; opacity:0.7;" />'
    else:
        data['seal_img'] = ''

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
@font-face {
    font-family: STSong-Light;
    src: url('STSong-Light');
    -pdf-font-name: STSong-Light;
    -pdf-use-cidfont: true;
}
@page {
    size: 24cm 14cm landscape;
    margin: 1cm 1.5cm;
}
body {
    font-family: STSong-Light, SimSun, Arial, Helvetica, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    color: #000;
}
.receipt-wrap {
    width: 100%;
}
h2 {
    text-align: center;
    font-size: 18px;
    margin: 0 0 2px 0;
    letter-spacing: 2px;
}
h3 {
    text-align: center;
    font-size: 15px;
    margin: 0 0 8px 0;
    letter-spacing: 6px;
}
.info-row {
    width: 100%;
    margin-bottom: 4px;
    font-size: 11px;
}
.info-row td {
    padding: 1px 0;
}
.mtbl {
    width: 100%;
    border-collapse: collapse;
    border: 2px solid #000;
}
.mtbl td {
    border: 1px solid #333;
    padding: 4px 6px;
    font-size: 11px;
    vertical-align: middle;
}
.mtbl .lb {
    background-color: #f0f0f0;
    font-weight: bold;
    text-align: center;
}
.sign-row {
    width: 100%;
    margin-top: 15px;
    font-size: 11px;
}
.sign-row td {
    padding: 3px 0;
    vertical-align: bottom;
}
.seal-area {
    margin-left: 5px;
}
.note {
    text-align: center;
    font-size: 9px;
    color: #888;
    margin-top: 12px;
}
</style>
</head>
<body>
<div class="receipt-wrap">
    <h2>天津俊途人力资源服务有限公司</h2>
    <h3>电 子 收 据</h3>

    <table class="info-row" cellpadding="0" cellspacing="0">
        <tr>
            <td style="text-align:left;">填制日期：{{ payment_date }}</td>
            <td style="text-align:right;">票号：{{ receipt_number }}</td>
        </tr>
    </table>

    <table class="mtbl" cellpadding="0" cellspacing="0">
        <tr>
            <td class="lb" style="width:60px;">付款人</td>
            <td>{{ payer_name }}</td>
            <td class="lb" style="width:60px;">收款人</td>
            <td>天津俊途人力资源服务有限公司</td>
        </tr>
        <tr>
            <td class="lb" colspan="2">收款内容</td>
            <td class="lb" colspan="2">金额</td>
        </tr>
        {{ items_html }}
        <tr>
            <td class="lb">合计金额（大写）</td>
            <td>{{ total_amount_cn }}</td>
            <td class="lb">合计金额（小写）</td>
            <td style="text-align:right; font-weight:bold; font-size:13px;">{{ total_amount_display }}</td>
        </tr>
        <tr>
            <td class="lb">备注</td>
            <td colspan="3">{{ notes }}</td>
        </tr>
    </table>

    <table class="sign-row" cellpadding="0" cellspacing="0">
        <tr>
            <td style="width:50%;">开具人：陈婷</td>
            <td style="width:50%; text-align:right;">收款单位（盖章）：<span class="seal-area">{{ seal_img }}</span></td>
        </tr>
    </table>

    <div class="note">
        <p>本收据仅作对账使用，款项未实际到账前不视为已收款。</p>
    </div>
</div>
</body>
</html>"""
