#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用网络设备执行器
支持多厂商、多任务的自动化执行
"""

import sys
import json
import yaml
import paramiko
import time
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import argparse

# 添加experiences目录到路径
SCRIPT_DIR = Path(__file__).parent
EXPERIENCES_DIR = SCRIPT_DIR.parent / "experiences"
sys.path.insert(0, str(EXPERIENCES_DIR))

from experience_manager import ExperienceManager

class UniversalNetworkExecutor:
    """通用网络设备执行器"""

    # 设备类型映射
    DEVICE_TYPE_MAP = {
        'h3c': 'hp_comware',
        'hp': 'hp_comware',
        'huawei': 'huawei',
        'cisco': 'cisco_ios',
        'cisco_ios': 'cisco_ios',
        'cisco_nxos': 'cisco_nxos',
        'ruijie': 'ruijie_os',
    }

    # 需要使用invoke_shell的设备类型（根据经验）
    INVOKE_SHELL_DEVICES = ['h3c', 'hp', 'hp_comware', 'huawei']

    def __init__(self, config: Dict[str, Any] = None):
        """初始化执行器"""
        self.config = config or {}
        self.experience_manager = ExperienceManager()
        self.connection = None
        self.shell = None
        self.results = []
        self.rollback_actions = []

        # 平台检测
        self.is_windows = os.name == 'nt'

    def log(self, message: str, level: str = "INFO"):
        """日志输出（兼容Windows编码）"""
        if self.is_windows:
            # Windows使用简单标记
            markers = {
                "INFO": "[INFO]",
                "OK": "[OK]",
                "ERROR": "[ERROR]",
                "WARNING": "[WARNING]"
            }
            print(f"{markers.get(level, '['+level+']')} {message}")
        else:
            # Linux/Mac可以使用特殊字符
            markers = {
                "INFO": "[INFO]",
                "OK": "✓",
                "ERROR": "✗",
                "WARNING": "⚠"
            }
            print(f"{markers.get(level, '['+level+']')} {message}")

    def apply_experiences(self, device_type: str, operation: str):
        """应用相关经验"""
        experiences = self.experience_manager.get_relevant_experiences(
            device_type.lower(), operation.lower()
        )

        if experiences:
            self.log(f"找到 {len(experiences)} 条相关经验", "INFO")
            for exp in experiences:
                self.log(f"- {exp.get('title', 'N/A')}: {exp.get('solution', 'N/A')}", "INFO")

                # 应用经验中的修复
                if "script_fix" in exp:
                    self.log(f"  应用修复: {exp['script_fix'][:80]}...", "INFO")

        return experiences

    def connect(self, host: str, username: str, password: str,
                device_type: str = None, port: int = 22, timeout: int = 30) -> bool:
        """连接设备"""
        self.log(f"正在连接到 {host}...", "INFO")

        # 检测设备类型并应用经验
        if device_type:
            self.apply_experiences(device_type, "connection")

        # 标准化设备类型
        normalized_type = self._normalize_device_type(device_type)

        try:
            self.connection = paramiko.SSHClient()
            self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.connection.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                auth_timeout=timeout,
                banner_timeout=timeout,
                allow_agent=False,
                look_for_keys=False
            )

            # 根据设备类型和经验选择执行方式
            if normalized_type in self.INVOKE_SHELL_DEVICES:
                # H3C等设备使用invoke_shell
                self.shell = self.connection.invoke_shell()
                time.sleep(2)  # 等待shell初始化

                # 清空初始输出
                if self.shell.recv_ready():
                    self.shell.recv(65535)

                self.log(f"已连接 (使用shell模式)", "OK")
            else:
                # 其他设备可以尝试exec_command
                self.log(f"已连接 (使用exec模式)", "OK")

            return True

        except Exception as e:
            self.log(f"连接失败: {str(e)}", "ERROR")
            return False

    def _normalize_device_type(self, device_type: str) -> str:
        """标准化设备类型"""
        if not device_type:
            return 'cisco_ios'  # 默认

        dt_lower = device_type.lower()
        return self.DEVICE_TYPE_MAP.get(dt_lower, dt_lower)

    def _handle_pagination(self, shell, timeout: int = 60) -> str:
        """处理分页并返回完整输出"""
        output = ""
        start_time = time.time()
        last_data_time = time.time()

        while time.time() - start_time < timeout:
            if shell.recv_ready():
                chunk = shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                last_data_time = time.time()

                # 检测分页提示符（根据经验002）
                if "---- More ----" in chunk:
                    shell.send(" ")
                    time.sleep(0.3)
                    continue

                # 检测命令完成（修复：同时识别用户视图和系统视图提示符）
                # 用户视图: <H3C>, 系统视图: [H3C-xxx]
                if (re.search(r'<\w+>|\[\S+\]', chunk) and len(output) > 50):
                    time.sleep(0.5)
                    if not shell.recv_ready():
                        break

            # 超过3秒无数据，认为完成（修复：降低超时时间和最小输出长度）
            if time.time() - last_data_time > 3 and len(output) > 50:
                break

            time.sleep(0.2)

        return output

    def execute_command(self, command: str, timeout: int = 30,
                       use_shell: bool = None) -> Dict[str, Any]:
        """执行单条命令"""
        result = {
            "command": command,
            "success": False,
            "output": "",
            "error": None
        }

        try:
            # 自动判断是否使用shell模式
            if use_shell is None:
                use_shell = self.shell is not None

            if use_shell and self.shell:
                # 使用invoke_shell模式
                self.shell.send(command + '\n')
                output = self._handle_pagination(self.shell, timeout)
                result["output"] = output
                result["success"] = True

            elif self.connection:
                # 使用exec_command模式
                stdin, stdout, stderr = self.connection.exec_command(command, timeout=timeout)
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')

                result["output"] = output
                result["success"] = True

                if error:
                    result["error"] = error

        except Exception as e:
            result["error"] = str(e)
            self.log(f"命令执行失败: {command} - {str(e)}", "ERROR")

            # 记录到经验
            self._record_error(command, str(e))

        return result

    def execute_commands(self, commands: List[str],
                        timeout: int = 30,
                        stop_on_error: bool = True,
                        save_config: bool = False,
                        confirm: bool = False) -> List[Dict[str, Any]]:
        """批量执行命令"""
        results = []

        # 安全确认
        if confirm:
            self.log(f"准备执行 {len(commands)} 条命令", "WARNING")
            print("\n命令列表:")
            for i, cmd in enumerate(commands, 1):
                print(f"  {i}. {cmd}")

            response = input("\n确认执行? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                self.log("操作已取消", "INFO")
                return results

        self.log(f"开始执行 {len(commands)} 条命令", "INFO")

        for idx, cmd in enumerate(commands, 1):
            self.log(f"[{idx}/{len(commands)}] {cmd}", "INFO")

            # 自动处理save命令（根据经验004）
            if 'save' in cmd.lower() and 'force' not in cmd.lower():
                cmd = 'save force'

            result = self.execute_command(cmd, timeout=timeout)
            results.append(result)

            if not result["success"] and stop_on_error:
                self.log(f"命令执行失败，停止后续操作", "ERROR")
                break

        # 保存配置
        if save_config:
            self.log("保存配置...", "INFO")
            self.execute_command("save force", timeout=60)

        return results

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行复杂任务（支持变量、条件、循环、回滚）"""
        result = {
            "task_name": task.get("name", "Unnamed Task"),
            "success": False,
            "steps_completed": 0,
            "steps_total": len(task.get("steps", [])),
            "results": []
        }

        try:
            # 解析变量
            variables = task.get("variables", {})

            # 执行步骤
            for step in task.get("steps", []):
                step_result = self._execute_step(step, variables)
                result["results"].append(step_result)

                if not step_result.get("success", False):
                    # 执行回滚
                    if "rollback" in step:
                        self.log("执行失败，开始回滚...", "WARNING")
                        self._execute_rollback(step.get("rollback", []), variables)
                    break

                result["steps_completed"] += 1

            result["success"] = result["steps_completed"] == result["steps_total"]

        except Exception as e:
            result["error"] = str(e)
            self.log(f"任务执行失败: {str(e)}", "ERROR")

        return result

    def _execute_step(self, step: Dict[str, Any],
                      variables: Dict[str, str]) -> Dict[str, Any]:
        """执行单个步骤"""
        result = {"success": False, "output": ""}

        # 条件判断
        if "condition" in step:
            if not self._evaluate_condition(step["condition"], variables):
                result["skipped"] = True
                result["success"] = True
                return result

        # 循环
        if "loop" in step:
            loop_config = step["loop"]
            items = self._resolve_variable(loop_config.get("items", []), variables)

            for item in items:
                variables[loop_config.get("item_var", "item")] = item
                sub_result = self._execute_commands_in_step(step, variables)
                if not sub_result["success"]:
                    return sub_result

            result["success"] = True
            return result

        # 普通命令执行
        return self._execute_commands_in_step(step, variables)

    def _execute_commands_in_step(self, step: Dict[str, Any],
                                  variables: Dict[str, str]) -> Dict[str, Any]:
        """在步骤中执行命令"""
        commands = step.get("commands", [])

        # 变量替换
        resolved_commands = []
        for cmd in commands:
            resolved = self._resolve_variables(cmd, variables)
            resolved_commands.append(resolved)

        # 执行命令
        results = self.execute_commands(
            resolved_commands,
            timeout=step.get("timeout", 30),
            stop_on_error=step.get("stop_on_error", True),
            confirm=step.get("confirm", False)
        )

        success = all(r.get("success", False) for r in results)
        return {"success": success, "results": results}

    def _resolve_variables(self, text: str, variables: Dict[str, str]) -> str:
        """解析变量"""
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def _resolve_variable(self, value: Any, variables: Dict[str, str]) -> Any:
        """解析变量值"""
        if isinstance(value, str):
            return self._resolve_variables(value, variables)
        elif isinstance(value, list):
            return [self._resolve_variable(v, variables) for v in value]
        else:
            return value

    def _evaluate_condition(self, condition: Dict[str, Any],
                           variables: Dict[str, str]) -> bool:
        """评估条件"""
        # 简化版条件评估
        if "equals" in condition:
            left = self._resolve_variables(condition["equals"][0], variables)
            right = self._resolve_variables(condition["equals"][1], variables)
            return left == right
        elif "exists" in condition:
            var_name = condition["exists"]
            return var_name in variables and variables[var_name]
        return True

    def _execute_rollback(self, rollback_steps: List[Dict[str, Any]],
                         variables: Dict[str, str]):
        """执行回滚"""
        for step in reversed(rollback_steps):
            self._execute_step(step, variables)

    def _record_error(self, command: str, error: str):
        """记录错误到经验"""
        # 检查是否是已知问题
        known_issues = self.experience_manager.search(error)

        if not known_issues:
            # 新问题，记录
            self.log("发现新问题，建议记录到经验库", "WARNING")
            # 可以选择自动记录或提示用户记录

    def disconnect(self):
        """断开连接"""
        try:
            if self.shell:
                self.shell.close()
            if self.connection:
                self.connection.close()
            self.log("已断开连接", "INFO")
        except:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="通用网络设备执行器")
    parser.add_argument("--host", required=True, help="设备IP地址")
    parser.add_argument("--username", required=True, help="用户名")
    parser.add_argument("--password", required=True, help="密码")
    parser.add_argument("--device-type", default="cisco_ios", help="设备类型")
    parser.add_argument("--port", type=int, default=22, help="SSH端口")
    parser.add_argument("--commands", nargs="+", help="要执行的命令列表")
    parser.add_argument("--task", help="任务定义文件(JSON/YAML)")
    parser.add_argument("--timeout", type=int, default=30, help="命令超时时间")
    parser.add_argument("--confirm", action="store_true", help="执行前确认")
    parser.add_argument("--no-save", action="store_true", help="不保存配置")

    args = parser.parse_args()

    executor = UniversalNetworkExecutor()

    try:
        # 连接设备
        if not executor.connect(args.host, args.username, args.password,
                                args.device_type, args.port):
            sys.exit(1)

        # 执行任务或命令
        if args.task:
            # 从文件加载任务
            with open(args.task, 'r', encoding='utf-8') as f:
                if args.task.endswith('.json'):
                    task = json.load(f)
                else:
                    task = yaml.safe_load(f)

            result = executor.execute_task(task)

            if result["success"]:
                executor.log(f"任务 '{result['task_name']}' 完成", "OK")
                print(f"\n完成步骤: {result['steps_completed']}/{result['steps_total']}")
            else:
                executor.log(f"任务 '{result['task_name']}' 失败", "ERROR")
                sys.exit(1)

        elif args.commands:
            # 直接执行命令列表
            results = executor.execute_commands(
                args.commands,
                timeout=args.timeout,
                confirm=args.confirm,
                save_config=not args.no_save
            )

            # 显示结果
            print("\n执行结果:")
            for i, result in enumerate(results, 1):
                status = "OK" if result["success"] else "ERROR"
                print(f"{i}. [{status}] {result['command']}")
                if result["error"]:
                    print(f"   错误: {result['error']}")
                elif result["output"]:
                    # 只显示前500字符
                    output_preview = result["output"][:500]
                    if len(result["output"]) > 500:
                        output_preview += "\n...(输出已截断)"
                    print(f"   输出:\n{output_preview}")

        else:
            executor.log("未指定任务或命令", "ERROR")
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        executor.log("\n操作已取消", "WARNING")
        sys.exit(1)
    except Exception as e:
        executor.log(f"发生错误: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        executor.disconnect()

if __name__ == "__main__":
    main()
