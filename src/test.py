import shutil,os
src = r"C:\Users\WDai\Documents\Temu资料\020_所有商品信息\2507月-AE9\主图\4.jpg"  # 你确定存在的图片
dst = r"C:\Users\WDai\Documents\Temu资料\100_Tools\ImageBatchProcessor\AI_process_temp\comfy_api_input"
file = 'test.jpg'
print(os.path.exists(src))
print(os.path.exists(dst))
shutil.copy2(src, os.path.join(dst, file))