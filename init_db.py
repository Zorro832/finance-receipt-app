#!/usr/bin/env python3
"""
数据库初始化脚本
用于初始化数据库和创建默认数据
"""
from database import Database

def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")
    
    db = Database()
    db.init_default_templates()
    
    print("✓ 数据库初始化完成！")
    print(f"✓ 数据库位置: {db.db_path}")

if __name__ == '__main__':
    init_database()
