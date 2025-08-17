import requests
import time

# 测试一个肯定存在的文件
def test_view_performance():
    base_url = "http://100.83.51.62:8188"
    
    # 方法1：测试一个已存在很久的文件
    print("测试1：访问已存在的文件")
    start = time.time()
    r1 = requests.get(
        f"{base_url}/view",
        params={
            "filename": "20250817_010230_938261_ComfyUI_00078_.png",  # 放一个测试文件
            "subfolder": "comfy_api_input",
            "type": "input"
        },
        timeout=30
    )
    print(f"状态: {r1.status_code}, 耗时: {time.time()-start:.3f}秒")
    
    # 方法2：不带参数
    print("\n测试2：不带参数的 /view")
    start = time.time()
    r2 = requests.get(f"{base_url}/view", timeout=30)
    print(f"状态: {r2.status_code}, 耗时: {time.time()-start:.3f}秒")
    
    # 方法3：测试其他接口
    print("\n测试3：其他接口速度")
    start = time.time()
    r3 = requests.get(f"{base_url}/system_stats", timeout=5)
    print(f"/system_stats 耗时: {time.time()-start:.3f}秒")

test_view_performance()