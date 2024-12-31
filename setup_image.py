import os
import shutil
import sys

def setup_image():
    try:
        # 源图片路径
        src_image = r"D:\微信图片_20241229204908.jpg"
        
        # 检查源图片是否存在
        if not os.path.exists(src_image):
            print(f"错误：找不到源图片文件：{src_image}")
            return False
            
        # 创建 static/img 目录
        img_dir = os.path.join('static', 'img')
        os.makedirs(img_dir, exist_ok=True)
        
        # 目标图片路径
        dst_image = os.path.join(img_dir, 'about.jpg')
        
        # 如果目标文件已存在，先删除
        if os.path.exists(dst_image):
            os.remove(dst_image)
            
        # 复制图片
        shutil.copy2(src_image, dst_image)
        
        print(f"成功：图片已复制到 {dst_image}")
        return True
        
    except Exception as e:
        print(f"错误：复制图片时发生错误：{str(e)}")
        return False

if __name__ == "__main__":
    if setup_image():
        print("图片设置完成！")
    else:
        print("图片设置失败！")
        sys.exit(1)
