import os,sys
from PIL import Image

# 源图和目标图标路径
SOURCE_PNG = "source_icon.png"       # 你的原始图标文件名
OUTPUT_ICO = "src/resources/app_icon.ico"  # 输出到项目resources目录

# 建议的多尺寸集合
ICON_SIZES = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]

def build_icon():
    print("当前工作目录:", os.getcwd())
    print("检查文件是否存在:", os.path.abspath(SOURCE_PNG), os.path.exists(SOURCE_PNG))

    if not os.path.exists(SOURCE_PNG):
        print(f"❌ 未找到源图标文件：{SOURCE_PNG}")
        return

    # 创建输出目录
    os.makedirs(os.path.dirname(OUTPUT_ICO), exist_ok=True)

    # 打开源图像
    img = Image.open(SOURCE_PNG).convert("RGBA")

    # 保存为多尺寸ico
    img.save(OUTPUT_ICO, sizes=ICON_SIZES)
    print(f"✅ 生成完成：{OUTPUT_ICO}")
    print("包含尺寸：", ICON_SIZES)

if __name__ == "__main__":
    build_icon()
    sys.stdout.flush()