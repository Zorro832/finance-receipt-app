#!/usr/bin/env python3
"""
数据持久化模块 - JSON文件存储
替换SQLite，数据保存在文件中，重启后可通过git恢复
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

DATA_DIR = "data"
RECEIPTS_FILE = os.path.join(DATA_DIR, "receipts.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    for f in [RECEIPTS_FILE, SETTINGS_FILE, TEMPLATES_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as fp:
                if "templates" in f:
                    json.dump([get_default_template_data()], fp, ensure_ascii=False)
                else:
                    json.dump([], fp, ensure_ascii=False)


def get_default_template_data():
    return {
        "id": 1,
        "name": "标准模板",
        "description": "标准格式的财务收据模板",
        "template_html": """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page { size: A4; margin: 2cm; }
body { font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; }
.receipt { max-width: 800px; margin: 0 auto; }
.header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }
.title { font-size: 32px; font-weight: bold; margin-bottom: 10px; }
.subtitle { font-size: 14px; color: #666; }
.info-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
.info-table td { padding: 12px; border: 1px solid #ddd; vertical-align: top; }
.info-table .label { background: #f5f5f5; font-weight: bold; width: 120px; text-align: center; }
.amount { font-size: 18px; font-weight: bold; color: #d32f2f; }
.footer { margin-top: 50px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #ddd; padding-top: 20px; }
.seal-area { margin-top: 60px; text-align: right; padding-right: 50px; }
.seal-line { display: inline-block; border-top: 2px solid #333; width: 150px; padding-top: 10px; text-align: center; }
</style>
</head>
<body>
<div class="receipt">
<div class="header">
<div class="title">财务收据</div>
<div class="subtitle">FINANCIAL RECEIPT</div>
</div>
<table class="info-table">
<tr><td class="label">收据编号</td><td>{{ receipt_number }}</td><td class="label">日期</td><td>{{ payment_date }}</td></tr>
<tr><td class="label">付款方</td><td>{{ payer_name }}</td><td class="label">付款方税号</td><td>{{ payer_tax_id }}</td></tr>
<tr><td class="label">收款事由</td><td colspan="3">{{ purpose }}</td></tr>
<tr><td class="label">金额</td><td class="amount" colspan="3">{{ currency_symbol }}{{ amount }}</td></tr>
<tr><td class="label">税率</td><td>{{ tax_rate }}%</td><td class="label">税额</td><td>{{ currency_symbol }}{{ tax_amount }}</td></tr>
<tr><td class="label">总金额</td><td class="amount" colspan="3">{{ currency_symbol }}{{ total_amount }}</td></tr>
<tr><td class="label">收款方</td><td>{{ payee_name }}</td><td class="label">收款方税号</td><td>{{ payee_tax_id }}</td></tr>
<tr><td class="label">备注</td><td colspan="3">{{ notes }}</td></tr>
</table>
<div class="seal-area"><div class="seal-line">收款方签章</div></div>
<div class="footer"><p>本收据由系统自动生成，无需签字盖章</p><p>生成时间：{{ created_at }}</p></div>
</div>
</body>
</html>""",
        "is_default": True,
        "created_at": datetime.now().isoformat()
    }


class Database:
    def __init__(self, db_path: str = None):
        ensure_data_dir()
        self.next_id = self._get_next_id()

    def _get_next_id(self):
        ensure_data_dir()
        with open(RECEIPTS_FILE, "r", encoding="utf-8") as fp:
            receipts = json.load(fp)
        if not receipts:
            return 1
        return max(r["id"] for r in receipts) + 1

    def _read_receipts(self):
        ensure_data_dir()
        with open(RECEIPTS_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def _write_receipts(self, receipts):
        ensure_data_dir()
        with open(RECEIPTS_FILE, "w", encoding="utf-8") as fp:
            json.dump(receipts, fp, ensure_ascii=False, indent=2)

    def init_db(self):
        ensure_data_dir()

    def create_receipt(self, data: Dict[str, Any]) -> int:
        receipts = self._read_receipts()
        receipt_id = self.next_id
        self.next_id += 1
        now = datetime.now().isoformat()
        record = {
            "id": receipt_id,
            "receipt_number": data.get("receipt_number", ""),
            "payer_name": data.get("payer_name", ""),
            "payer_tax_id": data.get("payer_tax_id", ""),
            "amount": float(data.get("amount", 0)),
            "currency": data.get("currency", "CNY"),
            "payment_date": data.get("payment_date", ""),
            "purpose": data.get("purpose", ""),
            "payee_name": data.get("payee_name", ""),
            "payee_tax_id": data.get("payee_tax_id", ""),
            "tax_rate": float(data.get("tax_rate", 0)),
            "tax_amount": float(data.get("tax_amount", 0)),
            "total_amount": float(data.get("total_amount", 0)),
            "notes": data.get("notes", ""),
            "template_type": data.get("template_type", "standard"),
            "created_at": now,
            "updated_at": now
        }
        receipts.append(record)
        self._write_receipts(receipts)
        return receipt_id

    def get_receipt(self, receipt_id: int) -> Optional[Dict]:
        receipts = self._read_receipts()
        for r in receipts:
            if r["id"] == receipt_id:
                return r
        return None

    def get_receipt_by_number(self, receipt_number: str) -> Optional[Dict]:
        receipts = self._read_receipts()
        for r in receipts:
            if r["receipt_number"] == receipt_number:
                return r
        return None

    def get_receipts(self, page=1, limit=20, search=None, currency=None, date_from=None, date_to=None):
        receipts = self._read_receipts()
        filtered = list(receipts)

        if search:
            s = search.lower()
            filtered = [r for r in filtered if
                      s in r["receipt_number"].lower() or
                      s in r["payer_name"].lower() or
                      s in r["purpose"].lower() or
                      s in r["payee_name"].lower()]

        if currency:
            filtered = [r for r in filtered if r["currency"] == currency]

        if date_from:
            filtered = [r for r in filtered if r["payment_date"] >= date_from]
        if date_to:
            filtered = [r for r in filtered if r["payment_date"] <= date_to]

        total = len(filtered)
        start = (page - 1) * limit
        end = start + limit
        paged = filtered[start:end]

        return {
            "receipts": paged,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit or 1
        }

    def update_receipt(self, receipt_id: int, data: Dict[str, Any]) -> bool:
        receipts = self._read_receipts()
        for r in receipts:
            if r["id"] == receipt_id:
                for k in ["payer_name", "payer_tax_id", "amount", "currency",
                         "payment_date", "purpose", "payee_name", "payee_tax_id",
                         "tax_rate", "tax_amount", "total_amount", "notes", "template_type"]:
                    if k in data:
                        r[k] = data[k]
                r["updated_at"] = datetime.now().isoformat()
                self._write_receipts(receipts)
                return True
        return False

    def delete_receipt(self, receipt_id: int) -> bool:
        receipts = self._read_receipts()
        new_receipts = [r for r in receipts if r["id"] != receipt_id]
        if len(new_receipts) < len(receipts):
            self._write_receipts(new_receipts)
            return True
        return False

    def generate_receipt_number(self) -> str:
        today = datetime.now().strftime("%Y%m%d")
        receipts = self._read_receipts()
        count = sum(1 for r in receipts if r["receipt_number"].startswith(f"RCP-{today}-"))
        return f"RCP-{today}-{count + 1:03d}"

    def get_statistics_summary(self):
        today_str = datetime.now().date().isoformat()
        receipts = self._read_receipts()

        total_count = len(receipts)
        total_amount = sum(r["total_amount"] for r in receipts)

        today_items = [r for r in receipts if r.get("created_at", "").startswith(today_str)]
        today_count = len(today_items)
        today_amount = sum(r["total_amount"] for r in today_items)

        first_of_month = datetime.now().replace(day=1).date().isoformat()
        month_items = [r for r in receipts if r.get("created_at", "") >= first_of_month]
        month_count = len(month_items)
        month_amount = sum(r["total_amount"] for r in month_items)

        return {
            "total": {"count": total_count, "amount": total_amount},
            "today": {"count": today_count, "amount": today_amount},
            "month": {"count": month_count, "amount": month_amount}
        }

    def create_template(self, data: Dict[str, Any]) -> int:
        ensure_data_dir()
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as fp:
            templates = json.load(fp)

        new_id = max((t["id"] for t in templates), default=0) + 1
        if data.get("is_default"):
            for t in templates:
                t["is_default"] = False

        record = {
            "id": new_id,
            "name": data.get("name", "新模板"),
            "description": data.get("description", ""),
            "template_html": data.get("template_html", ""),
            "is_default": data.get("is_default", False),
            "created_at": datetime.now().isoformat()
        }
        templates.append(record)
        with open(TEMPLATES_FILE, "w", encoding="utf-8") as fp:
            json.dump(templates, fp, ensure_ascii=False, indent=2)
        return new_id

    def get_templates(self):
        ensure_data_dir()
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def get_default_template(self):
        templates = self.get_templates()
        for t in templates:
            if t.get("is_default"):
                return t
        return templates[0] if templates else None

    def init_default_templates(self):
        ensure_data_dir()
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as fp:
            templates = json.load(fp)
        if not templates:
            templates = [get_default_template_data()]
            with open(TEMPLATES_FILE, "w", encoding="utf-8") as fp:
                json.dump(templates, fp, ensure_ascii=False, indent=2)
