#!/usr/bin/env python3
"""
数据持久化模块 - JSON文件存储
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

DATA_DIR = "data"
RECEIPTS_FILE = os.path.join(DATA_DIR, "receipts.json")
PAYERS_FILE = os.path.join(DATA_DIR, "payers.json")
PAYEES_FILE = os.path.join(DATA_DIR, "payees.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    for f in [RECEIPTS_FILE, PAYERS_FILE, PAYEES_FILE, TEMPLATES_FILE]:
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
        "template_html": get_default_template_html(),
        "is_default": True,
        "created_at": datetime.now().isoformat()
    }


def get_default_template_html():
    # 导入pdf_generator中的模板，保持一致
    from pdf_generator import get_default_template_html as _get_tpl
    return _get_tpl()


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

    # ===== 文件读写工具 =====
    def _read_json(self, filepath):
        ensure_data_dir()
        with open(filepath, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def _write_json(self, filepath, data):
        ensure_data_dir()
        with open(filepath, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

    # ===== 收据操作 =====
    def create_receipt(self, data: Dict[str, Any]) -> int:
        receipts = self._read_json(RECEIPTS_FILE)
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
        self._write_json(RECEIPTS_FILE, receipts)
        
        # 自动保存付款人和收款人
        self.save_payer(data.get("payer_name", ""), data.get("payer_tax_id", ""))
        self.save_payee(data.get("payee_name", ""), data.get("payee_tax_id", ""))
        
        return receipt_id

    def get_receipt(self, receipt_id: int) -> Optional[Dict]:
        receipts = self._read_json(RECEIPTS_FILE)
        for r in receipts:
            if r["id"] == receipt_id:
                return r
        return None

    def get_receipt_by_number(self, receipt_number: str) -> Optional[Dict]:
        receipts = self._read_json(RECEIPTS_FILE)
        for r in receipts:
            if r["receipt_number"] == receipt_number:
                return r
        return None

    def get_receipts(self, page=1, limit=20, search=None, currency=None, date_from=None, date_to=None):
        receipts = self._read_json(RECEIPTS_FILE)
        filtered = list(receipts)

        if search:
            s = search.lower()
            filtered = [r for r in filtered if
                      s in r.get("receipt_number", "").lower() or
                      s in r.get("payer_name", "").lower() or
                      s in r.get("purpose", "").lower() or
                      s in r.get("payee_name", "").lower()]

        if currency:
            filtered = [r for r in filtered if r.get("currency") == currency]

        if date_from:
            filtered = [r for r in filtered if r.get("payment_date", "") >= date_from]
        if date_to:
            filtered = [r for r in filtered if r.get("payment_date", "") <= date_to]

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
        receipts = self._read_json(RECEIPTS_FILE)
        for r in receipts:
            if r["id"] == receipt_id:
                for k in ["payer_name", "payer_tax_id", "amount", "currency",
                         "payment_date", "purpose", "payee_name", "payee_tax_id",
                         "tax_rate", "tax_amount", "total_amount", "notes", "template_type",
                         "status", "email", "receipt_number"]:
                    if k in data:
                        r[k] = data[k]
                r["updated_at"] = datetime.now().isoformat()
                self._write_json(RECEIPTS_FILE, receipts)
                return True
        return False

    def delete_receipt(self, receipt_id: int) -> bool:
        receipts = self._read_json(RECEIPTS_FILE)
        new_receipts = [r for r in receipts if r["id"] != receipt_id]
        if len(new_receipts) < len(receipts):
            self._write_json(RECEIPTS_FILE, new_receipts)
            return True
        return False

    def generate_receipt_number(self) -> str:
        # 优先使用管理员配置的编号规则
        admin_config_path = os.path.join(DATA_DIR, "admin.json")
        if os.path.exists(admin_config_path):
            with open(admin_config_path, "r", encoding="utf-8") as fp:
                admin_config = json.load(fp)
            prefix = admin_config.get("receipt_prefix", "RCP")
            seq = admin_config.get("receipt_seq", 0)
            today = datetime.now().strftime("%Y%m%d")

            # 如果日期变了，重置序号
            if admin_config.get("last_reset_date") != today:
                seq = 0

            seq += 1
            admin_config["receipt_seq"] = seq
            admin_config["last_reset_date"] = today
            with open(admin_config_path, "w", encoding="utf-8") as fp:
                json.dump(admin_config, fp, ensure_ascii=False, indent=2)

            return f"{prefix}-{today}-{seq:03d}"

        # 默认逻辑
        today = datetime.now().strftime("%Y%m%d")
        receipts = self._read_json(RECEIPTS_FILE)
        count = sum(1 for r in receipts if r.get("receipt_number", "").startswith(f"RCP-{today}-"))
        return f"RCP-{today}-{count + 1:03d}"

    # ===== 付款人/收款人存储 =====
    def get_payers(self, keyword=None):
        payers = self._read_json(PAYERS_FILE)
        if keyword:
            kw = keyword.lower()
            payers = [p for p in payers if kw in p.get("name", "").lower() or kw in p.get("tax_id", "").lower()]
        return payers

    def save_payer(self, name, tax_id=""):
        if not name:
            return
        payers = self._read_json(PAYERS_FILE)
        for p in payers:
            if p["name"] == name:
                if tax_id and not p.get("tax_id"):
                    p["tax_id"] = tax_id
                    p["updated_at"] = datetime.now().isoformat()
                    self._write_json(PAYERS_FILE, payers)
                return
        payers.append({
            "id": len(payers) + 1,
            "name": name,
            "tax_id": tax_id,
            "created_at": datetime.now().isoformat()
        })
        self._write_json(PAYERS_FILE, payers)

    def get_payees(self, keyword=None):
        payees = self._read_json(PAYEES_FILE)
        if keyword:
            kw = keyword.lower()
            payees = [p for p in payees if kw in p.get("name", "").lower() or kw in p.get("tax_id", "").lower()]
        return payees

    def save_payee(self, name, tax_id=""):
        if not name:
            return
        payees = self._read_json(PAYEES_FILE)
        for p in payees:
            if p["name"] == name:
                if tax_id and not p.get("tax_id"):
                    p["tax_id"] = tax_id
                    p["updated_at"] = datetime.now().isoformat()
                    self._write_json(PAYEES_FILE, payees)
                return
        payees.append({
            "id": len(payees) + 1,
            "name": name,
            "tax_id": tax_id,
            "created_at": datetime.now().isoformat()
        })
        self._write_json(PAYEES_FILE, payees)

    # ===== 统计 =====
    def get_statistics_summary(self):
        today_str = datetime.now().date().isoformat()
        receipts = self._read_json(RECEIPTS_FILE)

        total_count = len(receipts)
        total_amount = sum(r.get("total_amount", 0) for r in receipts)

        today_items = [r for r in receipts if r.get("created_at", "").startswith(today_str)]
        today_count = len(today_items)
        today_amount = sum(r.get("total_amount", 0) for r in today_items)

        first_of_month = datetime.now().replace(day=1).date().isoformat()
        month_items = [r for r in receipts if r.get("created_at", "") >= first_of_month]
        month_count = len(month_items)
        month_amount = sum(r.get("total_amount", 0) for r in month_items)

        return {
            "total": {"count": total_count, "amount": total_amount},
            "today": {"count": today_count, "amount": today_amount},
            "month": {"count": month_count, "amount": month_amount}
        }

    # ===== 模板 =====
    def get_templates(self):
        return self._read_json(TEMPLATES_FILE)

    def get_default_template(self):
        templates = self.get_templates()
        for t in templates:
            if t.get("is_default"):
                return t
        return templates[0] if templates else None

    def create_template(self, data: Dict[str, Any]) -> int:
        templates = self._read_json(TEMPLATES_FILE)
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
        self._write_json(TEMPLATES_FILE, templates)
        return new_id

    def init_default_templates(self):
        templates = self._read_json(TEMPLATES_FILE)
        # 更新默认模板为最新版本（如果包含旧的不兼容CSS）
        from pdf_generator import get_default_template_html as _get_new_tpl
        new_html = _get_new_tpl()
        updated = False
        for t in templates:
            if t.get("is_default"):
                old_html = t.get("template_html", "")
                if "SimSun" in old_html or "display: flex" in old_html or "宋体" in old_html:
                    t["template_html"] = new_html
                    t["updated_at"] = datetime.now().isoformat()
                    updated = True
        if not templates:
            templates = [get_default_template_data()]
            updated = True
        if updated:
            self._write_json(TEMPLATES_FILE, templates)
