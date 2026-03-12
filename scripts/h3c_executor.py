#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H3C设备专属执行器
支持H3C/HP Comware设备的命令执行
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


class H3CExecutor(BaseExecutor):
    """H3C设备执行器"""

    def __init__(self, host: str, username: str, password: str,
                 port: int = 22, timeout: int = 30, auto_help: bool = False):
        """
        初始化H3C执行器

        Args:
            host: 设备IP地址
            username: 用户名
            password: 密码
            port: SSH端口
            timeout: 连接超时时间
            auto_help: 命令失败时自动查询帮助
        """
        super().__init__(host, username, password, port, timeout, auto_help)
        self.device_type = "H3C"

        # 经验管理器
        self.exp_manager = ExperienceManager()

        # 执行结果
        self.results = []

    def connect(self) -> bool:
        """
        建立SSH连接

        Returns:
            是否连接成功
        """
        self.log(f"正在连接到 H3C 设备 {self.host}...", "INFO")

        try:
            # 应用经验库：检查H3C连接相关经验
            experiences = self.exp_manager.get_relevant_experiences("H3C", "connection")
            if experiences:
                self.log(f"找到 {len(experiences)} 条连接相关经验", "INFO")
                for exp in experiences:
                    self.log(f"  - {exp.get('title', 'N/A')}", "INFO")

            # 创建SSH客户端
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 连接设备
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                auth_timeout=self.timeout,
                banner_timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )

            # 应用经验001：使用invoke_shell而非exec_command
            self.shell = self.ssh_client.invoke_shell()
            time.sleep(2)  # 等待shell初始化

            # 清空初始输出
            if self.shell.recv_ready():
                self.shell.recv(65535)

            self.log(f"已连接 (使用shell模式)", "OK")
            return True

        except paramiko.AuthenticationException:
            self.log(f"连接失败: 认证失败，用户名或密码错误", "ERROR")
            return False
        except paramiko.SSHException as e:
            self.log(f"连接失败: SSH错误 - {str(e)}", "ERROR")
            return False
        except Exception as e:
            self.log(f"连接失败: {str(e)}", "ERROR")
            return False

    def _handle_pagination(self, timeout: int = 60) -> str:
        """
        处理分页并返回完整输出

        应用经验002：自动处理"---- More ----"分页提示符
        """
        output = ""
        start_time = time.time()
        last_data_time = time.time()

        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                last_data_time = time.time()

                # 检测分页提示符（经验002）
                if "---- More ----" in chunk:
                    self.shell.send(" ")
                    time.sleep(0.3)
                    continue

                # 检测命令完成（用户视图 <H3C> 或系统视图 [H3C-xxx]）
                if (re.search(r'<\w+>|\[\S+\]', chunk) and len(output) > 50):
                    time.sleep(0.5)
                    if not self.shell.recv_ready():
                        break

            # 超过3秒无数据，认为完成
            if time.time() - last_data_time > 3 and len(output) > 50:
                break

            time.sleep(0.2)

        return output

    def _apply_experience_fix(self, command: str) -> str:
        """
        应用经验库修复命令

        Returns:
            修复后的命令
        """
        # 查找相关经验
        experiences = self.exp_manager.get_relevant_experiences("H3C", "command")

        for exp in experiences:
            # 应用经验004：save命令自动添加force
            if "save" in command.lower() and "force" in exp.get("solution", ""):
                if command.strip().lower() == "save":
                    self.log("应用经验004: save → save force", "INFO")
                    return "save force"

        return command

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        执行单条命令

        Args:
            command: 要执行的命令
            timeout: 命令超时时间

        Returns:
            执行结果字典
        """
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
            # 应用经验库修复命令
            fixed_command = self._apply_experience_fix(command)

            # 发送命令
            self.shell.send(fixed_command + '\n')

            # 获取输出（自动处理分页）
            output = self._handle_pagination(timeout)

            result["output"] = output
            result["success"] = True

            # 检查输出中的错误
            error_patterns = [
                r"% Error",
                r"% Incomplete command",
                r"% Ambiguous command",
                r"Unrecognized command",
                r"Error:",
                r"Failed"
            ]

            for pattern in error_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    result["success"] = False
                    result["error"] = f"命令执行错误: 匹配到错误模式 '{pattern}'"

                    # 自动查询帮助
                    if self.auto_help:
                        self.log(f"命令失败，自动查询帮助...", "INFO")
                        help_output = self.query_help(fixed_command)
                        result["help"] = help_output

                    break

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False

        return result

    def execute_commands(self, commands: List[str],
                        stop_on_error: bool = True) -> Dict[str, Any]:
        """
        批量执行命令

        Args:
            commands: 命令列表
            stop_on_error: 遇错是否停止

        Returns:
            执行结果字典
        """
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
                if result["error"]:
                    self.log(f"错误: {result['error']}", "ERROR")

                if stop_on_error:
                    self.log("遇到错误，停止后续操作", "WARNING")
                    break

        if summary["success"]:
            self.log(f"所有命令执行成功 ({summary['executed']}/{summary['total']})", "OK")

        return summary


def load_from_asset_inventory(device_query: str) -> Optional[Dict[str, Any]]:
    """
    从资产台账加载设备信息

    Args:
        device_query: 设备查询字符串（IP/名称/ID）

    Returns:
        设备连接信息字典，未找到返回None
    """
    try:
        manager = AssetManager()
        device = manager.find_device(device_query)

        if device:
            return {
                "host": device.get("host"),
                "username": device.get("username"),
                "password": manager.decode_password(device.get("password", "")),
                "port": device.get("port", 22),
                "device_type": device.get("device_type")
            }

        return None
    except Exception as e:
        print(f"[WARNING] 资产台账查询失败: {e}")
        return None


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="H3C设备专属执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 从资产台账查找设备
  python h3c_executor.py --device 192.168.56.3 --commands "display version" "display vlan"

  # 显式指定连接参数
  python h3c_executor.py --host 192.168.56.3 --username admin --password xxx --commands "display version"

  # 从标准读取命令（JSON格式）
  echo '["display version", "display vlan"]' | python h3c_executor.py --device 192.168.56.3 --commands-json -

  # 命令失败时自动查询帮助
  python h3c_executor.py --device 192.168.56.3 --commands "display version" --auto-help

  # 单独查询命令帮助
  python h3c_executor.py --device 192.168.56.3 --query-help "undo nat server protocol tcp global current-interface"
        """
    )

    # 设备查找方式（优先）
    parser.add_argument("--device", help="设备标识符(IP/名称/ID)，从资产台账查找")

    # 显式连接参数（降级）
    parser.add_argument("--host", help="设备IP地址")
    parser.add_argument("--username", help="用户名")
    parser.add_argument("--password", help="密码")
    parser.add_argument("--port", type=int, default=22, help="SSH端口（默认22）")

    # 命令参数
    parser.add_argument("--commands", nargs="+", help="要执行的命令列表")
    parser.add_argument("--commands-json", help="从JSON字符串或文件读取命令（-表示标准输入）")

    # 帮助查询参数
    parser.add_argument("--query-help", help="查询指定命令的帮助信息")
    parser.add_argument("--auto-help", action="store_true", help="命令失败时自动查询帮助")

    # 执行选项
    parser.add_argument("--timeout", type=int, default=30, help="命令超时时间（秒，默认30）")
    parser.add_argument("--continue-on-error", action="store_true", help="遇到错误继续执行")
    parser.add_argument("--output", help="输出结果到文件（JSON格式）")

    args = parser.parse_args()

    # 获取连接信息
    conn_info = None

    if args.device:
        # 优先从资产台账查找
        conn_info = load_from_asset_inventory(args.device)

        if conn_info:
            print(f"[OK] 从资产台账找到设备: {args.device}")
            if not conn_info["password"]:
                # 密码未存储，交互式输入
                conn_info["password"] = getpass.getpass("密码: ")
        else:
            print(f"[ERROR] 资产台账中未找到设备: {args.device}")
            print(f"[INFO] 请使用 --host/--username/--password 显式指定连接参数，或先添加设备到资产台账")
            sys.exit(1)

    elif args.host and args.username:
        # 降级使用显式参数
        if not args.password:
            args.password = getpass.getpass("密码: ")

        conn_info = {
            "host": args.host,
            "username": args.username,
            "password": args.password,
            "port": args.port
        }
    else:
        parser.error("必须指定 --device 或 --host/--username")

    # 创建执行器
    executor = H3CExecutor(
        host=conn_info["host"],
        username=conn_info["username"],
        password=conn_info["password"],
        port=conn_info.get("port", 22),
        timeout=args.timeout,
        auto_help=args.auto_help
    )

    try:
        # 建立连接
        if not executor.connect():
            sys.exit(1)

        # 如果只是查询帮助
        if args.query_help:
            help_output = executor.query_help(args.query_help)
            print("\n" + "="*50)
            print(f"命令帮助: {args.query_help} ?")
            print("="*50)
            print(help_output)
            sys.exit(0)

        # 解析命令
        commands = None
        if args.commands_json:
            if args.commands_json == "-":
                # 从标准输入读取
                import fileinput
                json_str = "".join(fileinput.input(files=("-")))
                commands = json.loads(json_str)
            else:
                # 从JSON字符串或文件读取
                try:
                    with open(args.commands_json, 'r') as f:
                        commands = json.load(f)
                except FileNotFoundError:
                    commands = json.loads(args.commands_json)
        elif args.commands:
            commands = args.commands
        else:
            parser.error("必须指定 --commands 或 --commands-json（或使用 --query-help 查询帮助）")

        # 执行命令
        result = executor.execute_commands(
            commands=commands,
            stop_on_error=not args.continue_on_error
        )

        # 输出结果
        output_result = {
            "success": result["success"],
            "executed": result["executed"],
            "total": result["total"],
            "failed_at": result["failed_at"],
            "results": []
        }

        for r in result["results"]:
            output_result["results"].append({
                "command": r["command"],
                "success": r["success"],
                "output": r["output"][:500] if r["output"] else "",  # 限制输出长度
                "error": r.get("error"),
                "help": r.get("help")  # 包含帮助信息（如果有）
            })

        # 保存到文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_result, f, indent=2, ensure_ascii=False)
            print(f"[OK] 结果已保存到: {args.output}")
        else:
            # 输出到标准输出
            print("\n" + "="*50)
            print(json.dumps(output_result, indent=2, ensure_ascii=False))

        # 返回码
        sys.exit(0 if result["success"] else 1)

    except KeyboardInterrupt:
        print("\n[WARNING] 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        executor.disconnect()


if __name__ == "__main__":
    main()
