import urllib.request
import os

def download_file(url, filename):
    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, filename)
    print(f"Downloaded {filename}")

# 创建目录
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('static/img', exist_ok=True)

# 下载 Bootstrap CSS
download_file(
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'static/css/bootstrap.min.css'
)

# 下载 Bootstrap JS
download_file(
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    'static/js/bootstrap.bundle.min.js'
)

# 下载示例头像
download_file(
    'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&s=200',
    'static/img/avatar.jpg'
)
