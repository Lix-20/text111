import psutil
import os
import time
import sys

def kill_python_processes():
    current_pid = os.getpid()
    killed = False
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == 'python.exe' and proc.pid != current_pid:
                proc.kill()
                killed = True
                print(f"已终止 Python 进程 (PID: {proc.pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return killed

def cleanup_database():
    try:
        if os.path.exists('blog.db'):
            try:
                os.remove('blog.db')
                print("已删除旧的数据库文件")
            except PermissionError:
                print("无法删除数据库文件，请确保没有其他程序正在使用它")
                return False
        return True
    except Exception as e:
        print(f"清理数据库时出错：{str(e)}")
        return False

if __name__ == "__main__":
    print("正在清理环境...")
    if kill_python_processes():
        print("等待进程完全终止...")
        time.sleep(2)
    
    if cleanup_database():
        print("环境清理完成！")
        sys.exit(0)
    else:
        print("环境清理失败！")
        sys.exit(1)
