#!/usr/bin/env python3
"""
配置备份和恢复工具
支持配置备份、恢复、对比和版本管理
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from netmiko import ConnectHandler
from difflib import unified_diff
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


class ConfigBackup:
    """配置备份管理器"""

    def __init__(self, connection: ConnectHandler, backup_dir: str = "./backups"):
        self.connection = connection
        self.device_type = connection.device_type
        self.hostname = self._get_hostname()
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 创建设备专用目录
        self.device_backup_dir = self.backup_dir / self.hostname
        self.device_backup_dir.mkdir(exist_ok=True)

    def _get_hostname(self) -> str:
        """获取设备主机名"""
        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                output = self.connection.send_command('display current-configuration | include hostname')
            elif 'cisco' in self.device_type:
                output = self.connection.send_command('show running-config | include hostname')
            else:
                output = self.connection.send_command('show running-config')

            # 简单提取主机名
            for line in output.split('\n'):
                if 'hostname' in line.lower():
                    return line.split()[-1].strip()

            # 如果无法获取，使用IP
            return self.connection.host.replace('.', '-')

        except Exception:
            return self.connection.host.replace('.', '-')

    def _get_config_command(self) -> str:
        """获取显示配置的命令"""
        if 'huawei' in self.device_type or 'comware' in self.device_type:
            return 'display current-configuration'
        elif 'cisco' in self.device_type:
            return 'show running-config'
        else:
            return 'show running-config'

    def _calculate_hash(self, content: str) -> str:
        """计算配置文件的哈希值"""
        return hashlib.md5(content.encode()).hexdigest()

    def backup_config(self, config_type: str = 'running',
                     description: str = "") -> Dict[str, str]:
        """
        备份设备配置

        Args:
            config_type: 配置类型 (running, startup)
            description: 备份描述

        Returns:
            备份结果信息字典
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        config_type_label = 'running' if config_type == 'running' else 'startup'

        console.print(f"\n[bold cyan]备份设备配置: {self.hostname}[/bold cyan]")
        console.print(f"[dim]配置类型: {config_type_label}[/dim]")
        console.print(f"[dim]备份时间: {timestamp}[/dim]")

        try:
            # 获取配置
            if config_type == 'startup':
                if 'huawei' in self.device_type or 'comware' in self.device_type:
                    command = 'display saved-configuration'
                else:
                    command = 'show startup-config'
            else:
                command = self._get_config_command()

            output = self.connection.send_command(command, read_timeout=60)

            # 生成文件名
            filename = f"{self.hostname}_{config_type_label}_{timestamp}.cfg"
            filepath = self.device_backup_dir / filename

            # 保存配置
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(output)

            # 计算哈希值
            file_hash = self._calculate_hash(output)

            # 保存元数据
            metadata = {
                'hostname': self.hostname,
                'device_type': self.device_type,
                'config_type': config_type_label,
                'timestamp': timestamp,
                'file_hash': file_hash,
                'description': description,
                'file_size': len(output)
            }

            metadata_file = filepath.with_suffix('.meta')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")

            result = {
                'status': 'success',
                'filename': str(filepath),
                'hash': file_hash,
                'size': len(output),
                'timestamp': timestamp
            }

            console.print(f"[bold green]✓ 配置备份成功[/bold green]")
            console.print(f"[dim]文件路径: {filepath}[/dim]")
            console.print(f"[dim]文件大小: {len(output)} 字节[/dim]")

            return result

        except Exception as e:
            error_result = {
                'status': 'error',
                'error': str(e)
            }
            console.print(f"[bold red]✗ 备份失败: {str(e)}[/bold red]")
            return error_result

    def list_backups(self) -> List[Dict[str, str]]:
        """
        列出所有备份文件
        """
        backups = []

        for meta_file in self.device_backup_dir.glob('*.meta'):
            try:
                metadata = {}
                with open(meta_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()

                config_file = meta_file.with_suffix('.cfg')
                metadata['filepath'] = str(config_file)
                metadata['exists'] = config_file.exists()

                backups.append(metadata)
            except Exception:
                continue

        # 按时间排序
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return backups

    def display_backups(self):
        """显示备份列表"""
        backups = self.list_backups()

        if not backups:
            console.print("[yellow]未找到备份文件[/yellow]")
            return

        console.print(f"\n[bold cyan]设备 {self.hostname} 的配置备份列表:[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("序号", style="dim", width=6)
        table.add_column("备份时间")
        table.add_column("配置类型")
        table.add_column("文件大小")
        table.add_column("哈希值")
        table.add_column("描述")

        for idx, backup in enumerate(backups, 1):
            size = backup.get('file_size', '0')
            size_kb = int(size) / 1024 if size.isdigit() else 0
            table.add_row(
                str(idx),
                backup.get('timestamp', 'N/A'),
                backup.get('config_type', 'N/A'),
                f"{size_kb:.1f} KB",
                backup.get('file_hash', 'N/A')[:8] + '...',
                backup.get('description', '')[:20]
            )

        console.print(table)

    def restore_config(self, backup_file: str, save: bool = True) -> bool:
        """
        恢复配置

        Args:
            backup_file: 备份文件路径
            save: 是否保存配置到启动配置

        Returns:
            是否成功
        """
        console.print(f"\n[bold yellow]⚠ 警告: 即将恢复配置[/bold yellow]")
        console.print(f"[dim]备份文件: {backup_file}[/dim]")

        try:
            # 读取备份文件
            with open(backup_file, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()

            console.print(f"[bold cyan]开始配置恢复...[/bold cyan]")

            # 进入配置模式
            if 'cisco' in self.device_type:
                self.connection.send_command('configure terminal')
            elif 'huawei' in self.device_type or 'comware' in self.device_type:
                self.connection.send_command('system-view')

            # 逐行发送配置
            for line in config_lines:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('!') or line.startswith('#'):
                    continue

                try:
                    self.connection.send_command(line, read_timeout=5)
                except Exception:
                    pass  # 某些命令可能失败，继续执行

            # 退出配置模式
            if 'cisco' in self.device_type:
                self.connection.send_command('end')
            elif 'huawei' in self.device_type or 'comware' in self.device_type:
                self.connection.send_command('return')

            # 保存配置
            if save:
                console.print("[cyan]保存配置...[/cyan]")
                if 'cisco' in self.device_type:
                    self.connection.send_command('write memory')
                elif 'huawei' in self.device_type or 'comware' in self.device_type:
                    self.connection.send_command('save')
                    self.connection.send_command('y')  # 确认保存

            console.print("[bold green]✓ 配置恢复成功[/bold green]")
            return True

        except Exception as e:
            console.print(f"[bold red]✗ 恢复失败: {str(e)}[/bold red]")
            return False

    def compare_configs(self, file1: str, file2: Optional[str] = None) -> bool:
        """
        对比两个配置文件

        Args:
            file1: 第一个配置文件路径
            file2: 第二个配置文件路径（如果为None，则对比当前运行配置）

        Returns:
            是否相同
        """
        try:
            # 读取第一个文件
            with open(file1, 'r', encoding='utf-8') as f:
                config1 = f.readlines()

            # 读取第二个文件或当前配置
            if file2:
                with open(file2, 'r', encoding='utf-8') as f:
                    config2 = f.readlines()
            else:
                # 获取当前运行配置
                command = self._get_config_command()
                output = self.connection.send_command(command, read_timeout=60)
                config2 = output.split('\n')

            # 计算差异
            diff = unified_diff(config1, config2, fromfile=file1,
                               tofile=file2 or 'running-config', lineterm='')

            console.print(f"\n[bold cyan]配置对比:[/bold cyan]\n")

            diff_lines = list(diff)
            if not diff_lines:
                console.print("[green]配置完全相同[/green]")
                return True
            else:
                console.print("[yellow]发现差异:[/yellow]\n")
                for line in diff_lines[:100]:  # 限制显示行数
                    if line.startswith('+'):
                        console.print(f"[green]{line}[/green]")
                    elif line.startswith('-'):
                        console.print(f"[red]{line}[/red]")
                    else:
                        console.print(f"[dim]{line}[/dim]")

                if len(diff_lines) > 100:
                    console.print(f"\n[dim]... 还有 {len(diff_lines) - 100} 行差异[/dim]")

                return False

        except Exception as e:
            console.print(f"[bold red]✗ 对比失败: {str(e)}[/bold red]")
            return False


def main():
    """
    主函数演示
    """
    console.print(Panel("[bold cyan]配置备份和恢复工具[/bold cyan]"))
    console.print("[yellow]请先使用 device_connector.py 建立连接[/yellow]")

    # 示例用法
    # from device_connector import connect_ssh
    #
    # # 建立连接
    # conn_info = {...}
    # connection = connect_ssh(conn_info)
    #
    # # 创建备份管理器
    # backup_mgr = ConfigBackup(connection)
    #
    # # 执行备份
    # result = backup_mgr.backup_config(description='变更前备份')
    #
    # # 列出备份
    # backup_mgr.display_backups()
    #
    # # 对比配置
    # backup_mgr.compare_configs(result['filename'])
    #
    # # 恢复配置（谨慎使用）
    # # backup_mgr.restore_config(result['filename'])


if __name__ == "__main__":
    main()
