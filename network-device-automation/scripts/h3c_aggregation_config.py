#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C交换机聚合口配置脚本
配置vlan100和g1/0/1、g1/0/3的聚合口
"""

import paramiko
import time
import sys

def configure_switch():
    """配置交换机"""
    # 连接信息
    host = "192.168.56.3"
    username = "admin"
    password = "Qch@202503"
    port = 22

    print(f"[INFO] 正在连接到 {host}...")

    try:
        # 创建SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=30,
            auth_timeout=30,
            banner_timeout=30,
            allow_agent=False,
            look_for_keys=False
        )

        # 使用invoke_shell（H3C必须使用此方法）
        shell = ssh.invoke_shell()
        time.sleep(2)

        # 清空初始输出
        if shell.recv_ready():
            shell.recv(65535)

        print("[OK] 连接成功")

        def handle_pagination(timeout=30):
            """处理分页并返回完整输出"""
            output = ""
            start_time = time.time()
            last_data_time = time.time()

            while time.time() - start_time < timeout:
                if shell.recv_ready():
                    chunk = shell.recv(65535).decode('utf-8', errors='ignore')
                    output += chunk
                    last_data_time = time.time()

                    # 处理分页提示符
                    if "---- More ----" in chunk:
                        shell.send(" ")
                        time.sleep(0.3)
                        continue

                    # 检测命令完成（检测到用户视图提示符）
                    if "<" in chunk and ">" in chunk and len(output) > 50:
                        time.sleep(0.5)
                        if not shell.recv_ready():
                            break

                # 超过5秒无数据，认为完成
                if time.time() - last_data_time > 5 and len(output) > 50:
                    break

                time.sleep(0.2)

            return output

        def send_cmd(cmd, delay=1):
            """发送命令"""
            print(f"[EXEC] {cmd}")
            shell.send(cmd + '\n')
            time.sleep(delay)
            output = handle_pagination(timeout=30)

            # 打印输出的最后部分
            if output:
                lines = output.split('\n')
                for line in lines[-10:]:
                    if line.strip():
                        print(f"  {line}")

            return output

        print("\n" + "="*60)
        print("开始配置")
        print("="*60)

        # 进入系统视图
        print("\n[STEP 1] 进入系统视图")
        send_cmd("system-view", 2)

        # 创建vlan 100
        print("\n[STEP 2] 创建vlan 100")
        send_cmd("vlan 100", 1)
        send_cmd("name TEST_VLAN100", 1)
        send_cmd("quit", 1)

        # 创建聚合口
        print("\n[STEP 3] 创建Bridge-Aggregation 1")
        send_cmd("interface Bridge-Aggregation 1", 1)
        send_cmd("port link-type trunk", 1)
        send_cmd("port trunk permit vlan 100", 1)
        send_cmd("quit", 1)

        # 配置g1/0/1
        print("\n[STEP 4] 配置g1/0/1")
        send_cmd("interface GigabitEthernet 1/0/1", 1)
        send_cmd("port link-aggregation group 1", 1)
        send_cmd("quit", 1)

        # 配置g1/0/3
        print("\n[STEP 5] 配置g1/0/3")
        send_cmd("interface GigabitEthernet 1/0/3", 1)
        send_cmd("port link-aggregation group 1", 1)
        send_cmd("quit", 1)

        # 退出系统视图
        print("\n[STEP 6] 退出系统视图")
        send_cmd("quit", 1)

        # 验证配置
        print("\n" + "="*60)
        print("验证配置")
        print("="*60)

        print("\n[VERIFY] 查看vlan 100")
        send_cmd("display vlan 100", 2)

        print("\n[VERIFY] 查看聚合口状态")
        send_cmd("display link-aggregation summary", 2)

        print("\n[VERIFY] 查看接口状态")
        send_cmd("display interface brief", 2)

        # 保存配置
        print("\n" + "="*60)
        print("保存配置")
        print("="*60)
        send_cmd("save force", 5)

        print("\n" + "="*60)
        print("[SUCCESS] 配置完成！")
        print("="*60)
        print("\n配置摘要:")
        print("  - vlan 100: 已创建")
        print("  - Bridge-Aggregation1: 已创建，trunk模式，允许vlan100")
        print("  - g1/0/1: 已加入聚合口1")
        print("  - g1/0/3: 已加入聚合口1")

        # 关闭连接
        shell.close()
        ssh.close()
        print(f"\n[INFO] 已断开连接")

        return True

    except Exception as e:
        print(f"\n[ERROR] 配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    configure_switch()
