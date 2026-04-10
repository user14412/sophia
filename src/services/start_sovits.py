import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 2. 从环境变量获取 SoVITS 路径
sovits_path = os.getenv("SOVITS_ROOT_PATH")

if not sovits_path or not os.path.exists(sovits_path):
    print(f"❌ 错误: 在 .env 中未找到有效的 SOVITS_ROOT_PATH ({sovits_path})")
    exit(1)

print(f"🚀 正在启动 GPT-SoVITS API 服务...")
print(f"📂 工作目录: {sovits_path}")

# 3. 使用 subprocess 启动 bat 脚本，关键是设定 cwd (Current Working Directory)
try:
    # 切换到 sovits 目录并执行 go-api.bat
    subprocess.run(
        ["cmd.exe", "/c", "go-api.bat"], 
        cwd=sovits_path, 
        check=True
    )
except KeyboardInterrupt:
    print("\n🛑 服务已手动停止")
except Exception as e:
    print(f"\n❌ 启动失败: {e}")