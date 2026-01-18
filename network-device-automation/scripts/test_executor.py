#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通用执行器
"""

import sys
sys.path.insert(0, "E:/knowlegdge_base/claude/.claude/skills/network-device-automation/scripts")

from universal_executor import UniversalNetworkExecutor

def test_basic_commands():
    """测试基本命令执行"""
    print("\n" + "="*60)
    print("测试通用执行器 - 基本命令执行")
    print("="*60 + "\n")

    executor = UniversalNetworkExecutor()

    try:
        # 连接到192.168.56.3
        print("[测试1] 连接到192.168.56.3...")
        if not executor.connect(
            host="192.168.56.3",
            username="admin",
            password="Qch@202503",
            device_type="H3C"
        ):
            print("[FAIL] 连接失败")
            return False

        print("[OK] 连接成功\n")

        # 执行简单命令
        print("[测试2] 执行简单命令...")
        results = executor.execute_commands([
            "display version",
            "display vlan"
        ], timeout=30, save_config=False)

        print(f"\n执行结果: {len(results)} 条命令")
        for i, result in enumerate(results, 1):
            status = "OK" if result["success"] else "ERROR"
            print(f"  {i}. [{status}]")
            if result["output"]:
                lines = result["output"].split('\n')
                # 显示前3行
                for line in lines[:3]:
                    if line.strip():
                        print(f"     {line}")
                if len(lines) > 3:
                    print(f"     ...(共{len(lines)}行)")

        print("\n[OK] 基本命令执行测试通过")

        return True

    except Exception as e:
        print(f"[ERROR] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        executor.disconnect()

if __name__ == "__main__":
    success = test_basic_commands()
    print(f"\n测试结果: {'通过' if success else '失败'}")
    sys.exit(0 if success else 1)
