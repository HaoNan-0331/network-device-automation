#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C交换机配置脚本
用于自动化配置H3C交换机的VLAN、DHCP和接口
"""

import sys
import paramiko
import time
import re
import os
from typing import List, Dict, Any, Optional


class H3CConfigurator:
    """H3C交换机配置器"""

    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssh = None
        self.shell = None

        # 平台检测
        self.is_windows = os.name == 'nt'

    def log(self, message: str, level: str = "INFO"):
        """日志输出（兼容Windows编码）"""
        if self.is_windows:
            markers = {
                "INFO": "[INFO]",
                "OK": "[OK]",
                "ERROR": "[ERROR]",
                "WARNING": "[WARNING]"
            }
            print(f"{markers.get(level, '['+level+']')} {message}")
        else:
            markers = {
                "INFO": "[INFO]",
                "OK": "[OK]",
                "ERROR": "[ERROR]",
                "WARNING": "[WARNING]"
            }
            print(f"{markers.get(level, '['+level+']')} {message}")

    def connect(self) -> bool:
        """连接H3C设备"""
        self.log(f"正在连接到 {self.host}...", "INFO")

        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=30,
                auth_timeout=30,
                banner_timeout=30,
                allow_agent=False,
                look_for_keys=False
            )

            # 使用invoke_shell（H3C必须使用此方法）
            self.shell = self.ssh.invoke_shell()
            time.sleep(2)

            # 清空初始输出
            if self.shell.recv_ready():
                self.shell.recv(65535)

            self.log("已连接 (使用shell模式)", "OK")
            return True

        except Exception as e:
            self.log(f"连接失败: {str(e)}", "ERROR")
            return False

    def _handle_pagination(self, timeout: int = 60) -> str:
        """处理分页并返回完整输出"""
        output = ""
        start_time = time.time()
        last_data_time = time.time()

        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                last_data_time = time.time()

                # 处理分页提示符
                if "---- More ----" in chunk:
                    self.shell.send(" ")
                    time.sleep(0.3)
                    continue

                # 检测命令完成（检测到用户视图提示符）
                if re.search(r'<\w+>', chunk) and len(output) > 100:
                    time.sleep(0.5)
                    if not self.shell.recv_ready():
                        break

            # 超过5秒无数据，认为完成
            if time.time() - last_data_time > 5 and len(output) > 100:
                break

            time.sleep(0.2)

        return output

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行单条命令"""
        result = {
            "command": command,
            "success": False,
            "output": "",
            "error": None
        }

        try:
            self.shell.send(command + '\n')
            output = self._handle_pagination(timeout)
            result["output"] = output
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            self.log(f"命令执行失败: {command} - {str(e)}", "ERROR")

        return result

    def execute_commands(self, commands: List[str], timeout: int = 30,
                        stop_on_error: bool = True) -> List[Dict[str, Any]]:
        """批量执行命令"""
        results = []

        self.log(f"开始执行 {len(commands)} 条命令", "INFO")

        for idx, cmd in enumerate(commands, 1):
            self.log(f"[{idx}/{len(commands)}] {cmd}", "INFO")

            result = self.execute_command(cmd, timeout=timeout)
            results.append(result)

            if not result["success"] and stop_on_error:
                self.log("命令执行失败，停止后续操作", "ERROR")
                break

        return results

    def configure_vlan_dhcp(self, vlan_id: int, vlan_ip: str, vlan_mask: str,
                           dhcp_start: str, dhcp_end: str,
                           gateway: str = None, dns_servers: List[str] = None) -> bool:
        """配置VLAN和DHCP服务

        Args:
            vlan_id: VLAN ID
            vlan_ip: VLAN接口IP地址
            vlan_mask: 子网掩码
            dhcp_start: DHCP起始IP地址
            dhcp_end: DHCP结束IP地址
            gateway: 网关地址（默认使用vlan_ip）
            dns_servers: DNS服务器列表

        Returns:
            配置是否成功
        """
        if gateway is None:
            gateway = vlan_ip

        # 构建配置命令序列
        commands = [
            # 进入系统视图
            "system-view",

            # 创建VLAN
            f"vlan {vlan_id}",
            "quit",

            # 配置VLAN接口IP
            f"interface Vlan-interface{vlan_id}",
            f"ip address {vlan_ip} {vlan_mask}",
            "quit",

            # 启用DHCP服务
            "dhcp enable",

            # 创建DHCP地址池
            f"dhcp server ip-pool vlan{vlan_id}",
            f"network {vlan_ip} mask {vlan_mask}",
            f"address range {dhcp_start} {dhcp_end}",
            f"gateway-list {gateway}",
        ]

        # 添加DNS服务器（如果提供）
        if dns_servers:
            for dns in dns_servers:
                commands.append(f"dns-list {dns}")

        # 退出地址池配置
        commands.extend([
            "quit",
            # 退出系统视图
            "quit"
        ])

        # 执行配置
        results = self.execute_commands(commands, timeout=60)

        # 检查是否所有命令都成功
        success = all(r.get("success", False) for r in results)

        if success:
            self.log(f"VLAN {vlan_id} 和 DHCP 配置成功", "OK")
        else:
            self.log(f"VLAN {vlan_id} 和 DHCP 配置失败", "ERROR")

        return success

    def configure_port_vlan(self, interface: str, vlan_id: int,
                           link_type: str = "access") -> bool:
        """配置接口加入VLAN

        Args:
            interface: 接口名称（如 GigabitEthernet1/0/2）
            vlan_id: VLAN ID
            link_type: 链路类型（access 或 trunk）

        Returns:
            配置是否成功
        """
        # 标准化接口名称（处理可能的格式差异）
        interface = interface.replace("GigabitEthernet", "GigabitEthernet ")

        # 构建配置命令序列
        commands = [
            "system-view",
            f"interface {interface}",
            f"port link-type {link_type}",
        ]

        if link_type == "access":
            commands.append(f"port access vlan {vlan_id}")
        elif link_type == "trunk":
            commands.append(f"port trunk permit vlan {vlan_id}")

        commands.extend([
            "quit",
            "quit"
        ])

        # 执行配置
        results = self.execute_commands(commands, timeout=30)

        # 检查是否所有命令都成功
        success = all(r.get("success", False) for r in results)

        if success:
            self.log(f"接口 {interface} 已加入 VLAN {vlan_id}", "OK")
        else:
            self.log(f"接口 {interface} 配置失败", "ERROR")

        return success

    def save_config(self) -> bool:
        """保存配置"""
        self.log("正在保存配置...", "INFO")
        result = self.execute_command("save force", timeout=60)

        if result["success"]:
            self.log("配置已保存", "OK")
            return True
        else:
            self.log("配置保存失败", "ERROR")
            return False

    def verify_vlan(self, vlan_id: int) -> Dict[str, Any]:
        """验证VLAN配置"""
        self.log(f"正在验证 VLAN {vlan_id} 配置...", "INFO")

        # 查看VLAN信息
        result = self.execute_command(f"display vlan {vlan_id}", timeout=10)

        # 查看接口VLAN配置
        interface_result = self.execute_command(
            "display port vlan", timeout=10
        )

        return {
            "vlan_info": result,
            "port_vlan": interface_result
        }

    def verify_dhcp(self) -> Dict[str, Any]:
        """验证DHCP配置"""
        self.log("正在验证 DHCP 配置...", "INFO")

        # 查看DHCP地址池
        result = self.execute_command("display dhcp server pool", timeout=10)

        return {
            "dhcp_pools": result
        }

    def disconnect(self):
        """断开连接"""
        try:
            if self.shell:
                self.shell.close()
            if self.ssh:
                self.ssh.close()
            self.log("已断开连接", "INFO")
        except:
            pass


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="H3C交换机配置工具")
    parser.add_argument("--host", required=True, help="交换机IP地址")
    parser.add_argument("--username", default="admin", help="用户名")
    parser.add_argument("--password", required=True, help="密码")
    parser.add_argument("--port", type=int, default=22, help="SSH端口")
    parser.add_argument("--vlan-id", type=int, required=True, help="VLAN ID")
    parser.add_argument("--vlan-ip", required=True, help="VLAN接口IP地址")
    parser.add_argument("--vlan-mask", default="255.255.255.0", help="子网掩码")
    parser.add_argument("--dhcp-start", required=True, help="DHCP起始IP")
    parser.add_argument("--dhcp-end", required=True, help="DHCP结束IP")
    parser.add_argument("--interface", help="要加入VLAN的接口")
    parser.add_argument("--gateway", help="网关地址（默认使用VLAN IP）")
    parser.add_argument("--dns", nargs="+", help="DNS服务器地址")
    parser.add_argument("--no-save", action="store_true", help="不保存配置")

    args = parser.parse_args()

    configurator = H3CConfigurator(args.host, args.username, args.password, args.port)

    try:
        # 连接设备
        if not configurator.connect():
            sys.exit(1)

        # 配置VLAN和DHCP
        if not configurator.configure_vlan_dhcp(
            vlan_id=args.vlan_id,
            vlan_ip=args.vlan_ip,
            vlan_mask=args.vlan_mask,
            dhcp_start=args.dhcp_start,
            dhcp_end=args.dhcp_end,
            gateway=args.gateway,
            dns_servers=args.dns
        ):
            sys.exit(1)

        # 配置接口（如果指定）
        if args.interface:
            if not configurator.configure_port_vlan(args.interface, args.vlan_id):
                sys.exit(1)

        # 验证配置
        configurator.verify_vlan(args.vlan_id)
        configurator.verify_dhcp()

        # 保存配置
        if not args.no_save:
            configurator.save_config()

        print("\n[OK] 配置完成")

    except KeyboardInterrupt:
        print("\n[WARNING] 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        configurator.disconnect()


if __name__ == "__main__":
    main()
