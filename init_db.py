import os
import sys
from app import app, db, Category, Tag

def init_database():
    try:
        # 在应用上下文中创建所有表
        with app.app_context():
            db.create_all()
            print("已创建数据库表")
            
            # 创建默认分类
            categories = [
                Category(name='技术', description='技术相关文章'),
                Category(name='生活', description='生活随笔'),
                Category(name='学习', description='学习笔记')
            ]
            db.session.add_all(categories)
            
            # 创建默认标签
            tags = [
                Tag(name='Python'),
                Tag(name='Flask'),
                Tag(name='Web开发'),
                Tag(name='数据库'),
                Tag(name='前端')
            ]
            db.session.add_all(tags)
            
            db.session.commit()
            print("已添加默认分类和标签")
            
        return True
    except Exception as e:
        print(f"错误：{str(e)}")
        return False

if __name__ == "__main__":
    print("开始初始化数据库...")
    if init_database():
        print("数据库初始化成功！")
    else:
        print("数据库初始化失败！")
        sys.exit(1)
