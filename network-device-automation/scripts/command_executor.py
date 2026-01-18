#!/usr/bin/env python3
"""
命令执行和输出解析器
支持跨厂商命令执行和结果格式化
"""

import json
import re
from typing import List, Dict, Any, Optional
from netmiko import ConnectHandler
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.json import JSON

console = Console()


# 厂商命令映射表
COMMAND_MAP = {
    'huawei': {
        'show_version': 'display version',
        'show_running_config': 'display current-configuration',
        'show_startup_config': 'display saved-configuration',
        'show_interfaces': 'display interface',
        'show_interface_status': 'display interface brief',
        'show_ip_route': 'display ip routing-table',
        'show_arp': 'display arp',
        'show_mac_table': 'display mac-address',
        'show_vlan': 'display vlan',
        'show_cpu': 'display cpu-usage',
        'show_memory': 'display memory-usage',
        'show_log': 'display logbuffer',
    },
    'hp_comware': {
        'show_version': 'display version',
        'show_running_config': 'display current-configuration',
        'show_startup_config': 'display saved-configuration',
        'show_interfaces': 'display interface',
        'show_interface_status': 'display interface brief',
        'show_ip_route': 'display ip routing-table',
        'show_arp': 'display arp',
        'show_mac_table': 'display mac-address',
        'show_vlan': 'display vlan',
        'show_cpu': 'display cpu-usage',
        'show_memory': 'display memory',
        'show_log': 'display logbuffer',
    },
    'cisco_ios': {
        'show_version': 'show version',
        'show_running_config': 'show running-config',
        'show_startup_config': 'show startup-config',
        'show_interfaces': 'show interfaces',
        'show_interface_status': 'show ip interface brief',
        'show_ip_route': 'show ip route',
        'show_arp': 'show ip arp',
        'show_mac_table': 'show mac address-table',
        'show_vlan': 'show vlan brief',
        'show_cpu': 'show processes cpu',
        'show_memory': 'show memory statistics',
        'show_log': 'show logging',
    },
    'cisco_nxos': {
        'show_version': 'show version',
        'show_running_config': 'show running-config',
        'show_startup_config': 'show startup-config',
        'show_interfaces': 'show interface',
        'show_interface_status': 'show interface brief',
        'show_ip_route': 'show ip route',
        'show_arp': 'show ip arp',
        'show_mac_table': 'show mac address-table',
        'show_vlan': 'show vlan',
        'show_cpu': 'show processes cpu',
        'show_memory': 'show system resources',
        'show_log': 'show logging last 100',
    },
    'ruijie_os': {
        'show_version': 'show version',
        'show_running_config': 'show running-config',
        'show_startup_config': 'show startup-config',
        'show_interfaces': 'show interface',
        'show_interface_status': 'show interface status',
        'show_ip_route': 'show ip route',
        'show_arp': 'show arp',
        'show_mac_table': 'show mac-address-table',
        'show_vlan': 'show vlan',
        'show_cpu': 'show cpu',
        'show_memory': 'show memory',
        'show_log': 'show logging',
    },
}


class CommandExecutor:
    """命令执行器类"""

    def __init__(self, connection: ConnectHandler):
        self.connection = connection
        self.device_type = connection.device_type
        self.command_history: List[Dict[str, str]] = []

    def translate_command(self, generic_cmd: str) -> str:
        """
        将通用命令翻译为设备特定命令
        如果命令不在映射表中，直接返回原命令
        """
        device_commands = COMMAND_MAP.get(self.device_type, {})
        return device_commands.get(generic_cmd, generic_cmd)

    def execute_command(self, command: str,
                       enable_mode: bool = False,
                       read_timeout: int = 30,
                       expect_string: str = None) -> str:
        """
        执行单条命令

        Args:
            command: 要执行的命令（可以是通用命令或设备特定命令）
            enable_mode: 是否需要进入特权模式
            read_timeout: 读取超时时间（秒）
            expect_string: 期望的提示符字符串

        Returns:
            命令输出字符串
        """
        try:
            # 翻译通用命令
            actual_command = self.translate_command(command)

            console.print(f"\n[bold cyan]执行命令:[/bold cyan] {actual_command}")

            # 执行命令
            if enable_mode:
                output = self.connection.send_command(actual_command,
                                                      read_timeout=read_timeout,
                                                      expect_string=expect_string)
            else:
                output = self.connection.send_command(actual_command,
                                                      read_timeout=read_timeout)

            # 记录到历史
            self.command_history.append({
                'command': actual_command,
                'timestamp': str(console.record_datetime),
                'output_length': len(output)
            })

            return output

        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            console.print(f"[bold red]{error_msg}[/bold red]")
            return error_msg

    def execute_commands(self, commands: List[str],
                        enable_mode: bool = False) -> Dict[str, str]:
        """
        批量执行命令

        Args:
            commands: 命令列表
            enable_mode: 是否需要特权模式

        Returns:
            命令与输出结果的映射字典
        """
        results = {}

        console.print(Panel(f"[bold yellow]批量执行 {len(commands)} 条命令[/bold yellow]"))

        for idx, cmd in enumerate(commands, 1):
            console.print(f"\n[dim][{idx}/{len(commands)}][/dim]")

            # 配置命令可能需要进入配置模式
            if cmd.startswith('conf') or cmd.startswith('config'):
                # 进入配置模式
                self.execute_command('configure terminal', enable_mode=True)
                output = self.execute_command(cmd, enable_mode=True)
                # 退出配置模式
                self.execute_command('end', enable_mode=True)
            else:
                output = self.execute_command(cmd, enable_mode=enable_mode)

            results[cmd] = output

        return results

    def parse_interface_status(self, output: str) -> List[Dict[str, Any]]:
        """
        解析接口状态输出
        返回结构化的接口信息列表
        """
        interfaces = []
        lines = output.split('\n')

        # 根据不同厂商使用不同的正则表达式
        if 'huawei' in self.device_type or 'comware' in self.device_type:
            # 华为/H3C格式
            pattern = r'(\S+)\s+(\S+)\s+(\d+)\s+([\w-]+)\s+([\w-]+)'

        elif 'cisco' in self.device_type:
            # Cisco格式
            pattern = r'(\S+)\s+(\S+)\s+([\w.]+)\s+(\w+)\s+\w+\s+(\w+)'

        elif 'ruijie' in self.device_type:
            # 锐捷格式
            pattern = r'(\S+)\s+(\S+)\s+([\d]+)\s+(\w+)\s+(\w+)'

        else:
            return interfaces

        for line in lines:
            match = re.search(pattern, line)
            if match:
                interfaces.append({
                    'interface': match.group(1),
                    'status': match.group(2),
                    'ip_address': match.group(3) if len(match.groups()) > 2 else 'N/A',
                    'protocol': match.group(4) if len(match.groups()) > 3 else 'N/A',
                })

        return interfaces

    def display_output(self, output: str, format_type: str = 'raw'):
        """
        格式化显示命令输出

        Args:
            output: 命令输出
            format_type: 显示格式 (raw, table, json)
        """
        if format_type == 'raw':
            # 原始输出带语法高亮
            console.print("\n")
            console.print(Syntax(output, "text", line_numbers=True))

        elif format_type == 'table':
            # 表格显示（适用于结构化输出）
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("属性")
            table.add_column("值")

            for line in output.split('\n')[:20]:  # 只显示前20行
                if ':' in line:
                    parts = line.split(':', 1)
                    table.add_row(parts[0].strip(), parts[1].strip())

            console.print("\n")
            console.print(table)

        elif format_type == 'json':
            # JSON格式显示
            console.print("\n")
            console.print(JSON({'output': output}))

    def get_command_history(self) -> List[Dict[str, str]]:
        """
        获取命令执行历史
        """
        return self.command_history

    def save_output(self, output: str, filename: str):
        """
        保存命令输出到文件
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(output)
            console.print(f"[bold green]✓ 输出已保存到: {filename}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]✗ 保存失败: {str(e)}[/bold red]")


def interactive_mode(executor: CommandExecutor):
    """
    交互式命令执行模式
    """
    console.print(Panel.fit("[bold cyan]命令执行交互模式[/bold cyan]"))
    console.print("[dim]输入命令执行，输入 'quit' 或 'exit' 退出[/dim]\n")

    while True:
        try:
            cmd = console.input("[bold yellow]Command>[/bold yellow] ")

            if not cmd:
                continue

            if cmd.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]退出交互模式[/yellow]")
                break

            # 特殊命令处理
            if cmd.lower() == 'history':
                # 显示命令历史
                history = executor.get_command_history()
                for idx, entry in enumerate(history, 1):
                    console.print(f"{idx}. {entry['command']}")
                continue

            if cmd.lower().startswith('save '):
                # 保存上次输出到文件
                filename = cmd.split(' ', 1)[1]
                if executor.command_history:
                    last_output = executor.execute_command(
                        executor.command_history[-1]['command']
                    )
                    executor.save_output(last_output, filename)
                continue

            # 执行命令
            output = executor.execute_command(cmd)

            # 显示输出
            if output and not output.startswith('命令执行失败'):
                executor.display_output(output[:1000])  # 限制输出长度

        except KeyboardInterrupt:
            console.print("\n[yellow]操作已取消[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]错误: {str(e)}[/bold red]")


def main():
    """
    主函数演示
    """
    from device_connector import get_connection_info, connect_ssh, disconnect

    console.print(Panel("[bold cyan]命令执行器[/bold cyan]"))

    # 获取连接（这里复用device_connector的函数）
    # 在实际使用中，连接对象应该是传入的
    console.print("[yellow]请先使用 device_connector.py 建立连接[/yellow]")

    # 示例：如果已有连接对象
    # connection = ...
    # executor = CommandExecutor(connection)
    #
    # # 执行单条命令
    # output = executor.execute_command('show_version')
    # executor.display_output(output)
    #
    # # 批量执行
    # commands = ['show_interfaces', 'show_vlan']
    # results = executor.execute_commands(commands)
    #
    # # 交互模式
    # interactive_mode(executor)


if __name__ == "__main__":
    main()
