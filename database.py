#!/usr/bin/env python3
"""
数据库操作模块
处理SQLite数据库的连接和CRUD操作
"""
import sqlite3
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Any

def get_base_path():
    """获取应用根目录（打包后也能正常工作）"""
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        return os.path.dirname(sys.executable)
    else:
        # 开发时的路径
        return os.path.abspath(os.path.dirname(__file__))

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_path = get_base_path()
            self.db_path = os.path.join(base_path, 'instance', 'receipts.db')
        else:
            self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建收据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_number VARCHAR(50) UNIQUE NOT NULL,
            payer_name VARCHAR(200) NOT NULL,
            payer_tax_id VARCHAR(50),
            amount DECIMAL(15, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'CNY',
            payment_date DATE NOT NULL,
            purpose TEXT NOT NULL,
            payee_name VARCHAR(200) NOT NULL,
            payee_tax_id VARCHAR(50),
            tax_rate DECIMAL(5, 2) DEFAULT 0,
            tax_amount DECIMAL(15, 2) DEFAULT 0,
            total_amount DECIMAL(15, 2) NOT NULL,
            notes TEXT,
            template_type VARCHAR(50) DEFAULT 'standard',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建设置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(50) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建模板表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            template_html TEXT NOT NULL,
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    # ==================== 收据操作 ====================
    
    def create_receipt(self, data: Dict[str, Any]) -> int:
        """创建新收据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO receipts (
            receipt_number, payer_name, payer_tax_id, amount, currency,
            payment_date, purpose, payee_name, payee_tax_id,
            tax_rate, tax_amount, total_amount, notes, template_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['receipt_number'],
            data['payer_name'],
            data.get('payer_tax_id'),
            data['amount'],
            data.get('currency', 'CNY'),
            data['payment_date'],
            data['purpose'],
            data['payee_name'],
            data.get('payee_tax_id'),
            data.get('tax_rate', 0),
            data.get('tax_amount', 0),
            data['total_amount'],
            data.get('notes'),
            data.get('template_type', 'standard')
        ))
        
        receipt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return receipt_id
    
    def get_receipt(self, receipt_id: int) -> Optional[Dict]:
        """获取单个收据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_receipt_by_number(self, receipt_number: str) -> Optional[Dict]:
        """根据收据编号获取收据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM receipts WHERE receipt_number = ?', (receipt_number,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_receipts(self, page: int = 1, limit: int = 20, 
                     search: str = None, currency: str = None,
                     date_from: str = None, date_to: str = None) -> Dict:
        """获取收据列表（支持分页和筛选）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建查询
        query = 'SELECT * FROM receipts WHERE 1=1'
        params = []
        
        if search:
            query += ''' AND (receipt_number LIKE ? OR payer_name LIKE ? 
                        OR purpose LIKE ? OR payee_name LIKE ?)'''
            search_pattern = f'%{search}%'
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
        if currency:
            query += ' AND currency = ?'
            params.append(currency)
        
        if date_from:
            query += ' AND payment_date >= ?'
            params.append(date_from)
        
        if date_to:
            query += ' AND payment_date <= ?'
            params.append(date_to)
        
        # 获取总数
        count_query = f'SELECT COUNT(*) as count FROM ({query})'
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        # 添加排序和分页
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, (page - 1) * limit])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return {
            'receipts': [dict(row) for row in rows],
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    
    def update_receipt(self, receipt_id: int, data: Dict[str, Any]) -> bool:
        """更新收据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE receipts SET
            payer_name = ?, payer_tax_id = ?, amount = ?, currency = ?,
            payment_date = ?, purpose = ?, payee_name = ?, payee_tax_id = ?,
            tax_rate = ?, tax_amount = ?, total_amount = ?, notes = ?,
            template_type = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (
            data['payer_name'],
            data.get('payer_tax_id'),
            data['amount'],
            data.get('currency', 'CNY'),
            data['payment_date'],
            data['purpose'],
            data['payee_name'],
            data.get('payee_tax_id'),
            data.get('tax_rate', 0),
            data.get('tax_amount', 0),
            data['total_amount'],
            data.get('notes'),
            data.get('template_type', 'standard'),
            receipt_id
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_receipt(self, receipt_id: int) -> bool:
        """删除收据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM receipts WHERE id = ?', (receipt_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def generate_receipt_number(self) -> str:
        """生成唯一的收据编号"""
        today = datetime.now().strftime('%Y%m%d')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 查询今天的收据数量
        cursor.execute('''
        SELECT COUNT(*) as count FROM receipts 
        WHERE receipt_number LIKE ?
        ''', (f'RCP-{today}-%',))
        
        count = cursor.fetchone()['count'] + 1
        conn.close()
        
        return f'RCP-{today}-{count:03d}'
    
    # ==================== 统计操作 ====================
    
    def get_statistics_summary(self) -> Dict:
        """获取统计摘要"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        first_day_of_month = today.replace(day=1)
        
        # 总统计
        cursor.execute('''
        SELECT 
            COUNT(*) as total_count,
            SUM(total_amount) as total_amount
        FROM receipts
        ''')
        total_stats = dict(cursor.fetchone())
        
        # 今日统计
        cursor.execute('''
        SELECT 
            COUNT(*) as today_count,
            SUM(total_amount) as today_amount
        FROM receipts
        WHERE DATE(created_at) = ?
        ''', (today,))
        today_stats = dict(cursor.fetchone())
        
        # 本月统计
        cursor.execute('''
        SELECT 
            COUNT(*) as month_count,
            SUM(total_amount) as month_amount
        FROM receipts
        WHERE created_at >= ?
        ''', (first_day_of_month,))
        month_stats = dict(cursor.fetchone())
        
        conn.close()
        
        return {
            'total': {
                'count': total_stats['total_count'] or 0,
                'amount': float(total_stats['total_amount'] or 0)
            },
            'today': {
                'count': today_stats['today_count'] or 0,
                'amount': float(today_stats['today_amount'] or 0)
            },
            'month': {
                'count': month_stats['month_count'] or 0,
                'amount': float(month_stats['month_amount'] or 0)
            }
        }
    
    # ==================== 模板操作 ====================
    
    def create_template(self, data: Dict[str, Any]) -> int:
        """创建模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 如果设置为默认，先取消其他默认
        if data.get('is_default'):
            cursor.execute('UPDATE templates SET is_default = 0')
        
        cursor.execute('''
        INSERT INTO templates (name, description, template_html, is_default)
        VALUES (?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('description'),
            data['template_html'],
            data.get('is_default', 0)
        ))
        
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template_id
    
    def get_templates(self) -> List[Dict]:
        """获取所有模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM templates ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_default_template(self) -> Optional[Dict]:
        """获取默认模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM templates WHERE is_default = 1 LIMIT 1')
        row = cursor.fetchone()
        
        if not row:
            cursor.execute('SELECT * FROM templates ORDER BY id LIMIT 1')
            row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def init_default_templates(self):
        """初始化默认模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 检查是否已有模板
        cursor.execute('SELECT COUNT(*) as count FROM templates')
        if cursor.fetchone()['count'] > 0:
            conn.close()
            return
        
        # 标准模板
        standard_template = '''
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
        
        cursor.execute('''
        INSERT INTO templates (name, description, template_html, is_default)
        VALUES (?, ?, ?, ?)
        ''', ('标准模板', '标准格式的财务收据模板', standard_template, 1))
        
        conn.commit()
        conn.close()
