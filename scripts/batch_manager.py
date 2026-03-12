#!/usr/bin/env python3
"""
批量设备操作管理器
支持对多台设备执行批量操作
"""

import yaml
import time
from pathlib import Path
from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.live import Live

console = Console()


class BatchManager:
    """批量设备操作管理器"""

    def __init__(self, inventory_file: str = None):
        self.inventory_file = inventory_file
        self.devices: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []

    def load_inventory(self, inventory_file: str = None) -> bool:
        """
        加载设备清单文件

        Args:
            inventory_file: YAML格式的设备清单文件

        Returns:
            是否成功加载
        """
        if inventory_file:
            self.inventory_file = inventory_file

        if not self.inventory_file:
            console.print("[bold red]✗ 未指定设备清单文件[/bold red]")
            return False

        try:
            with open(self.inventory_file, 'r', encoding='utf-8') as f:
                inventory = yaml.safe_load(f)

            # 解析设备列表
            if 'devices' in inventory:
                self.devices = inventory['devices']
            else:
                # 如果没有devices键，假设整个文件就是设备列表
                self.devices = inventory if isinstance(inventory, list) else [inventory]

            console.print(f"[bold green]✓ 成功加载 {len(self.devices)} 台设备[/bold green]")
            return True

        except FileNotFoundError:
            console.print(f"[bold red]✗ 文件不存在: {self.inventory_file}[/bold red]")
            return False
        except yaml.YAMLError as e:
            console.print(f"[bold red]✗ YAML解析错误: {str(e)}[/bold red]")
            return False
        except Exception as e:
            console.print(f"[bold red]✗ 加载失败: {str(e)}[/bold red]")
            return False

    def display_inventory(self):
        """显示设备清单"""
        if not self.devices:
            console.print("[yellow]设备列表为空[/yellow]")
            return

        table = Table(title="设备清单", show_header=True)
        table.add_column("序号", style="dim", width=6)
        table.add_column("主机名/IP")
        table.add_column("设备类型")
        table.add_column("用户名")
        table.add_column("分组")

        for idx, device in enumerate(self.devices, 1):
            table.add_row(
                str(idx),
                device.get('host', 'N/A'),
                device.get('device_type', 'N/A'),
                device.get('username', 'N/A'),
                device.get('group', 'default')
            )

        console.print(table)

    def connect_device(self, device_info: Dict[str, Any],
                     timeout: int = 10) -> ConnectHandler:
        """
        连接单个设备

        Args:
            device_info: 设备连接信息
            timeout: 连接超时时间

        Returns:
            ConnectHandler对象或None
        """
        try:
            connection = ConnectHandler(
                host=device_info['host'],
                device_type=device_info.get('device_type', 'cisco_ios'),
                username=device_info.get('username', 'admin'),
                password=device_info.get('password', ''),
                port=device_info.get('port', 22),
                secret=device_info.get('enable_password', ''),
                timeout=timeout,
                session_log=f"netmiko_{device_info['host']}.log"
            )

            return connection

        except Exception as e:
            console.print(f"[red]连接失败 {device_info['host']}: {str(e)}[/red]")
            return None

    def execute_on_device(self, device_info: Dict[str, Any],
                         operation: Callable,
                         operation_name: str = "操作") -> Dict[str, Any]:
        """
        在单个设备上执行操作

        Args:
            device_info: 设备信息
            operation: 要执行的操作函数
            operation_name: 操作名称

        Returns:
            操作结果字典
        """
        result = {
            'host': device_info.get('host', 'unknown'),
            'operation': operation_name,
            'status': 'unknown',
            'message': '',
            'data': None
        }

        try:
            # 建立连接
            console.print(f"[cyan]连接到 {result['host']}...[/cyan]")
            connection = self.connect_device(device_info)

            if not connection:
                result['status'] = 'failed'
                result['message'] = '连接失败'
                return result

            # 执行操作
            console.print(f"[green]✓ 已连接，执行{operation_name}...[/green]")
            output = operation(connection)

            # 关闭连接
            connection.disconnect()

            result['status'] = 'success'
            result['message'] = f'{operation_name}成功'
            result['data'] = output

            console.print(f"[green]✓ {result['host']} {operation_name}完成[/green]")

        except Exception as e:
            result['status'] = 'error'
            result['message'] = str(e)
            console.print(f"[red]✗ {result['host']} 执行失败: {str(e)}[/red]")

        return result

    def batch_execute(self, operation: Callable,
                     operation_name: str = "操作",
                     parallel: bool = True,
                     max_workers: int = 5) -> List[Dict[str, Any]]:
        """
        批量执行操作

        Args:
            operation: 要执行的操作函数（接受ConnectHandler参数）
            operation_name: 操作名称
            parallel: 是否并行执行
            max_workers: 最大并行数

        Returns:
            所有设备的结果列表
        """
        if not self.devices:
            console.print("[yellow]设备列表为空，请先加载设备清单[/yellow]")
            return []

        console.print(Panel(f"[bold cyan]批量{operation_name}[/bold cyan]"))
        console.print(f"[dim]设备数量: {len(self.devices)}[/dim]")
        console.print(f"[dim]执行模式: {'并行' if parallel else '串行'}[/dim]\n")

        self.results = []
        start_time = time.time()

        if parallel:
            # 并行执行
            with Progress() as progress:
                task = progress.add_task(f"[cyan]批量{operation_name}中...", total=len(self.devices))

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self.execute_on_device, device, operation, operation_name): device
                        for device in self.devices
                    }

                    for future in as_completed(futures):
                        result = future.result()
                        self.results.append(result)
                        progress.update(task, advance=1)

        else:
            # 串行执行
            for idx, device in enumerate(self.devices, 1):
                console.print(f"\n[dim][{idx}/{len(self.devices)}][/dim]")
                result = self.execute_on_device(device, operation, operation_name)
                self.results.append(result)

        # 统计结果
        end_time = time.time()
        duration = end_time - start_time

        self._display_summary(duration)

        return self.results

    def _display_summary(self, duration: float):
        """显示执行摘要"""
        total = len(self.results)
        success = sum(1 for r in self.results if r['status'] == 'success')
        failed = sum(1 for r in self.results if r['status'] in ['failed', 'error'])

        console.print(f"\n[bold]执行摘要:[/bold]")
        console.print(f"  总设备数: {total}")
        console.print(f"  成功: [green]{success}[/green]")
        console.print(f"  失败: [red]{failed}[/red]")
        console.print(f"  耗时: {duration:.2f}秒")

        # 详细结果表
        if self.results:
            table = Table(show_header=True)
            table.add_column("设备")
            table.add_column("状态")
            table.add_column("消息")

            for result in self.results:
                status = result['status']
                if status == 'success':
                    status_color = 'green'
                elif status == 'failed':
                    status_color = 'red'
                else:
                    status_color = 'yellow'

                table.add_row(
                    result['host'],
                    f"[{status_color}]{status}[/{status_color}]",
                    result['message'][:50]
                )

            console.print("\n")
            console.print(table)

    def save_results(self, output_file: str):
        """
        保存执行结果

        Args:
            output_file: 输出文件路径
        """
        import json

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)

            console.print(f"[bold green]✓ 结果已保存到: {output_file}[/bold green]")

        except Exception as e:
            console.print(f"[bold red]✗ 保存失败: {str(e)}[/bold red]")


# 预定义的批量操作
def backup_operation(connection: ConnectHandler) -> Dict[str, Any]:
    """备份配置操作"""
    from config_backup import ConfigBackup

    backup_mgr = ConfigBackup(connection)
    result = backup_mgr.backup_config()
    return result


def health_check_operation(connection: ConnectHandler) -> Dict[str, Any]:
    """健康检查操作"""
    from health_check import HealthChecker

    checker = HealthChecker(connection)
    result = checker.run_full_check()
    return result


def command_execute_operation(commands: List[str]) -> Callable:
    """
    命令执行操作工厂函数

    Args:
        commands: 要执行的命令列表

    Returns:
        操作函数
    """
    def _operation(connection: ConnectHandler) -> Dict[str, Any]:
        from command_executor import CommandExecutor

        executor = CommandExecutor(connection)
        results = executor.execute_commands(commands)
        return results

    return _operation


def main():
    """
    主函数演示
    """
    console.print(Panel("[bold cyan]批量设备操作管理器[/bold cyan]"))

    # 示例1: 批量配置备份
    # batch_mgr = BatchManager('inventory.yaml')
    # batch_mgr.load_inventory()
    # batch_mgr.display_inventory()
    # batch_mgr.batch_execute(backup_operation, "配置备份", parallel=True)
    # batch_mgr.save_results('backup_results.json')

    # 示例2: 批量健康检查
    # batch_mgr = BatchManager('inventory.yaml')
    # batch_mgr.load_inventory()
    # batch_mgr.batch_execute(health_check_operation, "健康检查", parallel=True)

    # 示例3: 批量执行命令
    # commands = ['show version', 'show interfaces']
    # batch_mgr = BatchManager('inventory.yaml')
    # batch_mgr.load_inventory()
    # batch_mgr.batch_execute(command_execute_operation(commands), "命令执行", parallel=False)

    console.print("\n[yellow]使用方法:[/yellow]")
    console.print("1. 准备设备清单文件 (YAML格式)")
    console.print("2. 创建BatchManager实例并加载清单")
    console.print("3. 调用batch_execute()执行批量操作")
    console.print("4. 查看结果并保存\n")


if __name__ == "__main__":
    main()
