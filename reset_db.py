import os
import sys
import time
from app import app, db, Category

def reset_database():
    try:
        # 删除旧的数据库文件
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if os.path.exists('blog.db'):
                    os.remove('blog.db')
                    print("已删除旧的数据库文件")
                break
            except PermissionError:
                if attempt < max_attempts - 1:
                    print(f"尝试 {attempt + 1}/{max_attempts}: 数据库文件被占用，等待2秒后重试...")
                    time.sleep(2)
                else:
                    print("无法删除数据库文件，请手动关闭所有使用该文件的程序")
                    return False
        
        # 等待一下确保文件系统已经完全释放了文件
        time.sleep(1)
        
        # 创建新的数据库
        with app.app_context():
            db.create_all()
            print("已创建新的数据库结构")
            
            # 创建默认分类
            categories = [
                Category(id=1, name='日记', description='记录生活点滴和心情感悟'),
                Category(id=2, name='学习', description='学习笔记和知识总结'),
                Category(id=3, name='旅行', description='旅行见闻和精彩瞬间')
            ]
            db.session.add_all(categories)
            db.session.commit()
            print("已添加默认分类")
            
        return True
    except Exception as e:
        print(f"数据库重置失败：{str(e)}")
        return False

if __name__ == "__main__":
    print("开始重置数据库...")
    if reset_database():
        print("数据库重置成功！")
    else:
        print("数据库重置失败！")
        sys.exit(1)
