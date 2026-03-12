#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思科设备专属执行器
支持Cisco IOS/NX-OS设备的命令执行
集成经验库，自动处理已知问题，支持命令帮助查询
"""

import sys
import json
import time
import re
import argparse
import getpass
import paramiko
from pathlib import Path
from typing import Dict, List, Any, Optional

# 导入基类、经验管理器和资产管理器
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_executor import BaseExecutor
from experience_manager import ExperienceManager
from asset_manager import AssetManager


class CiscoExecutor(BaseExecutor):
    """思科设备执行器"""

    def __init__(self, host: str, username: str, password: str,
                 port: int = 22, timeout: int = 30, enable_password: str = None, auto_help: bool = False):
        """
        初始化思科执行器

        Args:
            host: 设备IP地址
            username: 用户名
            password: 密码
            port: SSH端口
            timeout: 连接超时时间
            enable_password: Enable密码（可选）
            auto_help: 命令失败时自动查询帮助
        """
        super().__init__(host, username, password, port, timeout, auto_help)
        self.device_type = "Cisco"
        self.enable_password = enable_password

        # 经验管理器
        self.exp_manager = ExperienceManager()
        self.results = []

    def connect(self) -> bool:
        """建立SSH连接"""
        self.log(f"正在连接到思科设备 {self.host}...", "INFO")

        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )

            self.shell = self.ssh_client.invoke_shell()
            time.sleep(2)

            if self.shell.recv_ready():
                self.shell.recv(65535)

            # 如果有enable密码，进入特权模式
            if self.enable_password:
                self.shell.send("enable\n")
                time.sleep(1)
                self.shell.send(self.enable_password + "\n")
                time.sleep(1)
                if self.shell.recv_ready():
                    self.shell.recv(65535)

            self.log(f"已连接", "OK")
            return True

        except paramiko.AuthenticationException:
            self.log(f"连接失败: 认证失败", "ERROR")
            return False
        except Exception as e:
            self.log(f"连接失败: {str(e)}", "ERROR")
            return False

    def _handle_pagination(self, timeout: int = 60) -> str:
        """处理分页（思科使用 "--More--"）"""
        output = ""
        start_time = time.time()
        last_data_time = time.time()

        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                last_data_time = time.time()

                if "--More--" in chunk:
                    self.shell.send(" ")
                    time.sleep(0.3)
                    continue

                if (re.search(r'^\w+[#>]', chunk, re.MULTILINE) and len(output) > 50):
                    time.sleep(0.5)
                    if not self.shell.recv_ready():
                        break

            if time.time() - last_data_time > 3 and len(output) > 50:
                break

            time.sleep(0.2)

        return output

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行单条命令"""
        result = {
            "command": command,
            "success": False,
            "output": "",
            "error": None,
            "help": None
        }

        if not self.shell:
            result["error"] = "未建立连接"
            return result

        try:
            self.shell.send(command + '\n')
            output = self._handle_pagination(timeout)

            result["output"] = output
            result["success"] = True

            error_patterns = [r"% Error", r"% Incomplete", r"% Ambiguous", r"% Invalid", r"Error:"]
            for pattern in error_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    result["success"] = False
                    result["error"] = f"命令执行错误: {pattern}"

                    if self.auto_help:
                        self.log(f"命令失败，自动查询帮助...", "INFO")
                        result["help"] = self.query_help(command)
                    break

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False

        return result

    def execute_commands(self, commands: List[str], stop_on_error: bool = True) -> Dict[str, Any]:
        """批量执行命令"""
        self.log(f"开始执行 {len(commands)} 条命令", "INFO")

        summary = {
            "success": True,
            "total": len(commands),
            "executed": 0,
            "failed_at": None,
            "results": []
        }

        for idx, cmd in enumerate(commands, 1):
            self.log(f"[{idx}/{len(commands)}] {cmd}", "INFO")
            result = self.execute_command(cmd)
            summary["executed"] += 1
            summary["results"].append(result)

            if not result["success"]:
                summary["success"] = False
                summary["failed_at"] = idx
                self.log(f"命令执行失败，位置: {idx}", "ERROR")
                if stop_on_error:
                    break

        if summary["success"]:
            self.log(f"所有命令执行成功", "OK")

        return summary


def load_from_asset_inventory(device_query: str) -> Optional[Dict[str, Any]]:
    """从资产台账加载设备信息"""
    try:
        manager = AssetManager()
        device = manager.find_device(device_query)
        if device:
            return {
                "host": device.get("host"),
                "username": device.get("username"),
                "password": manager.decode_password(device.get("password", "")),
                "port": device.get("port", 22),
                "enable_password": manager.decode_password(device.get("enable_password", ""))
            }
        return None
    except Exception as e:
        print(f"[WARNING] 资产台账查询失败: {e}")
        return None


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="思科设备专属执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cisco_executor.py --device 192.168.1.1 --commands "show version"
  python cisco_executor.py --host 192.168.1.1 --username admin --password xxx --query-help "no ip nat"
  python cisco_executor.py --device 192.168.1.1 --commands "show version" --auto-help
        """
    )

    parser.add_argument("--device", help="设备标识符(IP/名称/ID)")
    parser.add_argument("--host", help="设备IP地址")
    parser.add_argument("--username", help="用户名")
    parser.add_argument("--password", help="密码")
    parser.add_argument("--enable-password", help="Enable密码")
    parser.add_argument("--port", type=int, default=22, help="SSH端口")
    parser.add_argument("--commands", nargs="+", help="要执行的命令列表")
    parser.add_argument("--commands-json", help="从JSON读取命令")
    parser.add_argument("--query-help", help="查询指定命令的帮助信息")
    parser.add_argument("--auto-help", action="store_true", help="命令失败时自动查询帮助")
    parser.add_argument("--timeout", type=int, default=30, help="超时时间")
    parser.add_argument("--continue-on-error", action="store_true", help="遇错继续")
    parser.add_argument("--output", help="输出到文件")

    args = parser.parse_args()

    conn_info = None
    if args.device:
        conn_info = load_from_asset_inventory(args.device)
        if not conn_info:
            print(f"[ERROR] 未找到设备: {args.device}")
            sys.exit(1)
        if not conn_info["password"]:
            conn_info["password"] = getpass.getpass("密码: ")
    elif args.host and args.username:
        if not args.password:
            args.password = getpass.getpass("密码: ")
        conn_info = {"host": args.host, "username": args.username, "password": args.password,
                     "port": args.port, "enable_password": getattr(args, 'enable_password', None)}
    else:
        parser.error("必须指定 --device 或 --host/--username")

    executor = CiscoExecutor(
        host=conn_info["host"],
        username=conn_info["username"],
        password=conn_info["password"],
        port=conn_info.get("port", 22),
        enable_password=conn_info.get("enable_password"),
        timeout=args.timeout,
        auto_help=args.auto_help
    )

    try:
        if not executor.connect():
            sys.exit(1)

        if args.query_help:
            help_output = executor.query_help(args.query_help)
            print("\n" + "="*50)
            print(f"命令帮助: {args.query_help} ?")
            print("="*50)
            print(help_output)
            sys.exit(0)

        commands = None
        if args.commands_json:
            if args.commands_json == "-":
                import fileinput
                commands = json.loads("".join(fileinput.input(files=("-"))))
            else:
                try:
                    with open(args.commands_json, 'r') as f:
                        commands = json.load(f)
                except:
                    commands = json.loads(args.commands_json)
        elif args.commands:
            commands = args.commands
        else:
            parser.error("必须指定 --commands 或 --query-help")

        result = executor.execute_commands(commands, not args.continue_on_error)

        output_result = {
            "success": result["success"],
            "executed": result["executed"],
            "total": result["total"],
            "failed_at": result["failed_at"],
            "results": [{"command": r["command"], "success": r["success"],
                        "output": r["output"][:500] if r["output"] else "",
                        "error": r.get("error"), "help": r.get("help")}
                       for r in result["results"]]
        }

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_result, f, indent=2, ensure_ascii=False)
            print(f"[OK] 结果已保存到: {args.output}")
        else:
            print("\n" + "="*50)
            print(json.dumps(output_result, indent=2, ensure_ascii=False))

        sys.exit(0 if result["success"] else 1)

    except KeyboardInterrupt:
        print("\n[WARNING] 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        executor.disconnect()


if __name__ == "__main__":
    main()
