#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C DHCP故障诊断脚本
用于排查DHCP地址分配问题
"""

import sys
import paramiko
import time
import re
import os
from typing import Dict, Any, List


class H3CDHCPTroubleshooter:
    """H3C DHCP故障诊断器"""

    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssh = None
        self.shell = None

        self.is_windows = os.name == 'nt'
        self.diagnostic_results = {}

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.is_windows:
            markers = {
                "INFO": "[INFO]",
                "OK": "[OK]",
                "ERROR": "[ERROR]",
                "WARNING": "[WARNING]"
            }
            print(f"{markers.get(level, '['+level+']')} {message}")
        else:
            print(f"[{level}] {message}")

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

            self.shell = self.ssh.invoke_shell()
            time.sleep(2)

            if self.shell.recv_ready():
                self.shell.recv(65535)

            self.log("已连接", "OK")
            return True

        except Exception as e:
            self.log(f"连接失败: {str(e)}", "ERROR")
            return False

    def _handle_pagination(self, timeout: int = 30) -> str:
        """处理分页并返回完整输出"""
        output = ""
        start_time = time.time()
        last_data_time = time.time()

        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                last_data_time = time.time()

                if "---- More ----" in chunk:
                    self.shell.send(" ")
                    time.sleep(0.3)
                    continue

                if re.search(r'<\w+>', chunk) and len(output) > 100:
                    time.sleep(0.5)
                    if not self.shell.recv_ready():
                        break

            if time.time() - last_data_time > 3 and len(output) > 100:
                break

            time.sleep(0.15)

        return output

    def execute_command(self, command: str, timeout: int = 15) -> str:
        """执行命令并返回输出"""
        self.log(f"执行: {command}", "INFO")
        try:
            self.shell.send(command + '\n')
            output = self._handle_pagination(timeout)
            return output
        except Exception as e:
            self.log(f"命令执行失败: {str(e)}", "ERROR")
            return ""

    def check_interface_status(self, interface: str) -> Dict[str, Any]:
        """检查接口状态"""
        self.log(f"\n=== 检查接口 {interface} 状态 ===", "INFO")

        result = {
            "interface": interface,
            "status": "unknown",
            "vlan": None,
            "link_type": None,
            "issues": []
        }

        # 检查接口简要状态
        output = self.execute_command("display interface brief", timeout=10)

        # 检查接口是否在输出中
        if interface in output or interface.replace("GigabitEthernet", "GigabitEthernet ") in output:
            # 解析接口状态
            lines = output.split('\n')
            for line in lines:
                if interface in line or "GigabitEthernet1/0/2" in line:
                    self.log(f"接口状态行: {line.strip()}", "INFO")
                    if "UP" in line.upper() or "up" in line:
                        result["status"] = "up"
                    elif "DOWN" in line.upper() or "down" in line:
                        result["status"] = "down"
                        result["issues"].append("接口状态为DOWN")
        else:
            result["issues"].append("接口未找到")

        # 检查接口详细配置
        output = self.execute_command(f"display interface {interface}", timeout=10)
        if output:
            self.log(f"接口详细信息已获取", "INFO")
            # 检查链路状态
            if "Line protocol state: UP" in output or "line protocol is up" in output:
                result["status"] = "up"
            if "Line protocol state: DOWN" in output:
                result["status"] = "down"
                result["issues"].append("线路协议状态DOWN")

        return result

    def check_interface_vlan_config(self, interface: str) -> Dict[str, Any]:
        """检查接口VLAN配置"""
        self.log(f"\n=== 检查接口 {interface} VLAN配置 ===", "INFO")

        result = {
            "interface": interface,
            "link_type": None,
            "pvid": None,
            "permitted_vlans": [],
            "issues": []
        }

        # 检查端口VLAN配置
        output = self.execute_command("display port vlan", timeout=10)
        self.log(f"端口VLAN配置:\n{output}", "INFO")

        # 解析VLAN配置
        lines = output.split('\n')
        found_interface = False
        for i, line in enumerate(lines):
            if interface in line or "GigabitEthernet1/0/2" in line:
                found_interface = True
                # 查找后续行的配置信息
                for j in range(i, min(i + 5, len(lines))):
                    if "link-type" in lines[j]:
                        if "access" in lines[j].lower():
                            result["link_type"] = "access"
                        elif "trunk" in lines[j].lower():
                            result["link_type"] = "trunk"
                    if "pvid" in lines[j].lower() or "vlan" in lines[j]:
                        # 尝试提取VLAN ID
                        vlan_match = re.search(r'(\d+)', lines[j])
                        if vlan_match:
                            pvid = int(vlan_match.group(1))
                            if result["pvid"] is None:
                                result["pvid"] = pvid

        if not found_interface:
            result["issues"].append("未找到接口VLAN配置信息")

        # 检查是否在VLAN 100中
        output = self.execute_command("display vlan 100", timeout=10)
        if interface in output or "GigabitEthernet1/0/2" in output:
            self.log(f"接口在VLAN 100中", "OK")
        else:
            result["issues"].append("接口未加入VLAN 100")
            self.log(f"接口未在VLAN 100中找到", "WARNING")

        return result

    def check_vlan_config(self, vlan_id: int) -> Dict[str, Any]:
        """检查VLAN配置"""
        self.log(f"\n=== 检查VLAN {vlan_id}配置 ===", "INFO")

        result = {
            "vlan_id": vlan_id,
            "exists": False,
            "interface_ip": None,
            "interface_status": None,
            "issues": []
        }

        # 检查VLAN是否存在
        output = self.execute_command(f"display vlan {vlan_id}", timeout=10)
        if f"VLAN ID: {vlan_id}" in output or f"VLAN interface name: Vlan-interface{vlan_id}" in output:
            result["exists"] = True
            self.log(f"VLAN {vlan_id} 存在", "OK")
        else:
            result["issues"].append(f"VLAN {vlan_id} 不存在")
            self.log(f"VLAN {vlan_id} 不存在", "ERROR")
            return result

        # 检查VLAN接口配置
        output = self.execute_command(f"display interface Vlan-interface{vlan_id}", timeout=10)
        if output:
            if "Line protocol state: UP" in output:
                result["interface_status"] = "up"
                self.log(f"VLAN接口{vlan_id}状态: UP", "OK")
            else:
                result["interface_status"] = "down"
                result["issues"].append(f"VLAN接口{vlan_id}状态为DOWN")

            # 提取IP地址
            ip_match = re.search(r'Internet Address is ([\d.]+)/(\d+)', output)
            if ip_match:
                result["interface_ip"] = f"{ip_match.group(1)}/{ip_match.group(2)}"
                self.log(f"VLAN接口IP: {result['interface_ip']}", "OK")
            else:
                result["issues"].append(f"VLAN接口{vlan_id}未配置IP地址")

        return result

    def check_dhcp_config(self, vlan_id: int) -> Dict[str, Any]:
        """检查DHCP配置"""
        self.log(f"\n=== 检查DHCP配置 ===", "INFO")

        result = {
            "dhcp_enabled": False,
            "dhcp_pools": [],
            "issues": []
        }

        # 检查DHCP是否启用
        output = self.execute_command("display dhcp server", timeout=10)
        if "DHCP is enabled" in output or "DHCP server status: Enabled" in output:
            result["dhcp_enabled"] = True
            self.log("DHCP服务已启用", "OK")
        else:
            result["issues"].append("DHCP服务未启用")
            self.log("DHCP服务未启用", "ERROR")

        # 检查DHCP地址池
        output = self.execute_command("display dhcp server pool", timeout=10)
        self.log(f"DHCP地址池:\n{output}", "INFO")

        # 解析地址池信息
        if f"vlan{vlan_id}" in output or f"VLAN{vlan_id}" in output:
            result["dhcp_pools"].append(f"vlan{vlan_id}")
            self.log(f"找到VLAN {vlan_id}的DHCP地址池", "OK")
        else:
            result["issues"].append(f"未找到VLAN {vlan_id}的DHCP地址池")
            self.log(f"未找到VLAN {vlan_id}的DHCP地址池", "WARNING")

        # 检查DHCP全局配置
        output = self.execute_command("display dhcp server global", timeout=10)
        if output:
            self.log("DHCP全局配置已获取", "INFO")

        return result

    def check_current_config(self) -> str:
        """获取当前配置"""
        self.log("\n=== 获取当前配置 ===", "INFO")
        output = self.execute_command("display current-configuration | include dhcp", timeout=20)
        return output

    def diagnose(self, interface: str = "GigabitEthernet1/0/2", vlan_id: int = 100) -> Dict[str, Any]:
        """执行完整诊断"""
        self.log(f"\n{'='*50}", "INFO")
        self.log(f"开始诊断 DHCP 问题", "INFO")
        self.log(f"交换机: {self.host}", "INFO")
        self.log(f"接口: {interface}", "INFO")
        self.log(f"VLAN: {vlan_id}", "INFO")
        self.log(f"{'='*50}\n", "INFO")

        results = {
            "host": self.host,
            "interface": interface,
            "vlan_id": vlan_id,
            "checks": {}
        }

        # 1. 检查接口状态
        results["checks"]["interface_status"] = self.check_interface_status(interface)

        # 2. 检查接口VLAN配置
        results["checks"]["interface_vlan"] = self.check_interface_vlan_config(interface)

        # 3. 检查VLAN配置
        results["checks"]["vlan_config"] = self.check_vlan_config(vlan_id)

        # 4. 检查DHCP配置
        results["checks"]["dhcp_config"] = self.check_dhcp_config(vlan_id)

        # 5. 获取相关配置
        results["checks"]["current_config"] = self.check_current_config()

        # 6. 生成诊断报告
        self.generate_report(results)

        return results

    def generate_report(self, results: Dict[str, Any]):
        """生成诊断报告"""
        self.log(f"\n{'='*50}", "INFO")
        self.log("诊断报告", "INFO")
        self.log(f"{'='*50}\n", "INFO")

        all_issues = []

        # 收集所有问题
        for check_name, check_result in results["checks"].items():
            if isinstance(check_result, dict) and "issues" in check_result:
                for issue in check_result["issues"]:
                    all_issues.append(f"[{check_name}] {issue}")

        if all_issues:
            self.log("发现的问题:", "WARNING")
            for i, issue in enumerate(all_issues, 1):
                self.log(f"  {i}. {issue}", "WARNING")
        else:
            self.log("未发现明显问题", "OK")

        self.log("\n建议检查项:", "INFO")
        self.log("  1. 终端设备网卡是否启用DHCP", "INFO")
        self.log("  2. 终端设备与交换机连接是否正常", "INFO")
        self.log("  3. 终端设备是否有防火墙阻止DHCP", "INFO")
        self.log("  4. 网络中是否有其他DHCP服务器干扰", "INFO")
        self.log("  5. 在终端上执行 ipconfig /release 和 /renew (Windows)", "INFO")

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

    parser = argparse.ArgumentParser(description="H3C DHCP故障诊断工具")
    parser.add_argument("--host", required=True, help="交换机IP地址")
    parser.add_argument("--username", default="admin", help="用户名")
    parser.add_argument("--password", required=True, help="密码")
    parser.add_argument("--port", type=int, default=22, help="SSH端口")
    parser.add_argument("--interface", default="GigabitEthernet1/0/2", help="接口名称")
    parser.add_argument("--vlan", type=int, default=100, help="VLAN ID")

    args = parser.parse_args()

    troubleshooter = H3CDHCPTroubleshooter(args.host, args.username, args.password, args.port)

    try:
        if not troubleshooter.connect():
            sys.exit(1)

        troubleshooter.diagnose(args.interface, args.vlan)

    except KeyboardInterrupt:
        print("\n[WARNING] 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        troubleshooter.disconnect()


if __name__ == "__main__":
    main()
