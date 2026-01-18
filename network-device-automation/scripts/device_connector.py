#!/usr/bin/env python3
"""
网络设备连接管理器
支持SSH、Telnet、串口连接方式
支持华为、H3C、思科、锐捷等主流厂商
集成资产台账查询，优先从台账获取设备信息
"""

import getpass
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from netmiko import ConnectHandler, NetmikoTimeoutError, NetmikoAuthenticationException
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

# 导入资产管理器
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

try:
    from asset_manager import AssetManager
    ASSET_MANAGER_AVAILABLE = True
except ImportError:
    ASSET_MANAGER_AVAILABLE = False

# 设备类型映射表
DEVICE_TYPES = {
    'huawei': 'huawei',
    'huaweivrp': 'huawei',
    'h3c': 'hp_comware',
    'hp': 'hp_comware',
    'comware': 'hp_comware',
    'cisco': 'cisco_ios',
    'cisco_ios': 'cisco_ios',
    'cisco_nxos': 'cisco_nxos',
    'ruijie': 'ruijie_os',
    'ruijie_os': 'ruijie_os',
    'juniper': 'juniper_junos',
    'juniper_junos': 'juniper_junos',
}


def search_inventory(query: str) -> Optional[Dict[str, Any]]:
    """
    从资产台账中搜索设备

    支持通过IP、主机名、设备名称查找
    返回连接信息字典，未找到返回None
    """
    if not ASSET_MANAGER_AVAILABLE:
        return None

    try:
        manager = AssetManager()
        device = manager.find_device(query)
        if device:
            console.print(f"[green]从资产台账找到设备: {device.get('name')} ({device.get('host')})[/green]")
            return manager.get_connection_info(query)
        return None
    except Exception as e:
        console.print(f"[dim]资产台账查询失败: {e}[/dim]")
        return None


def prompt_or_find_device(initial_query: str = "") -> Tuple[Dict[str, Any], str]:
    """
    智能获取设备连接信息
    优先从资产台账查找，未找到则交互式输入

    Returns:
        (连接信息字典, 设备标识符)
    """
    connection_info = {}
    device_identifier = initial_query or ""

    # 如果有初始查询，先尝试从台账查找
    if device_identifier:
        console.print(f"[cyan]正在查找设备: {device_identifier}[/cyan]")
        connection_info = search_inventory(device_identifier)

        if connection_info:
            # 检查密码是否存在
            if "password" not in connection_info or not connection_info["password"]:
                console.print("[yellow]资产中未存储密码，需要交互式输入[/yellow]")
                connection_info["password"] = getpass.getpass("[bold yellow]密码:[/bold yellow] ")
            else:
                console.print("[green]密码已从资产台账获取[/green]")

            return connection_info, device_identifier

        console.print(f"[yellow]资产台账中未找到 '{device_identifier}'[/yellow]")

        if not Confirm.ask("[yellow]是否要交互式输入连接信息?[/yellow]", default=True):
            if Confirm.ask("[yellow]是否要将此设备添加到资产台账?[/yellow]", default=False):
                return add_device_to_inventory(device_identifier), device_identifier
            return None, device_identifier

    # 交互式获取连接信息
    if not device_identifier:
        device_identifier = console.input("[bold yellow]设备IP、主机名或设备名称 (留空跳过台账查询):[/bold yellow] ").strip()
        if device_identifier:
            # 再次尝试台账查询
            connection_info = search_inventory(device_identifier)
            if connection_info:
                if "password" not in connection_info or not connection_info["password"]:
                    connection_info["password"] = getpass.getpass("[bold yellow]密码:[/bold yellow] ")
                return connection_info, device_identifier

            console.print(f"[yellow]资产台账中未找到 '{device_identifier}'[/yellow]")

    # 进入交互式输入模式
    console.print(Panel.fit("[bold cyan]设备连接信息 (交互式输入)[/bold cyan]"))
    connection_info = get_connection_info()
    return connection_info, device_identifier or connection_info.get('host', '')


def add_device_to_inventory(device_id: str = "") -> Dict[str, Any]:
    """
    添加设备到资产台账

    Returns:
        连接信息字典
    """
    if not ASSET_MANAGER_AVAILABLE:
        console.print("[yellow]资产管理器不可用，跳过添加到台账[/yellow]")
        return {}

    console.print(Panel.fit("[bold cyan]添加设备到资产台账[/bold cyan]"))

    # 交互式获取信息
    device_id = device_id or Prompt.ask("[bold yellow]设备ID[/bold yellow] (如: core-sw-01)")
    device_info = {
        "name": Prompt.ask("设备名称"),
        "host": Prompt.ask("IP地址或主机名"),
        "device_type": Prompt.ask("设备类型", choices=["huawei", "hp_comware", "cisco_ios", "cisco_nxos", "ruijie_os"]),
        "username": Prompt.ask("用户名"),
        "password": Prompt.ask("密码 (可选，留空则使用时输入)", password=True),
        "port": Prompt.ask("SSH端口", default="22"),
        "group": Prompt.ask("设备分组 (可选)"),
        "description": Prompt.ask("描述 (可选)"),
        "location": Prompt.ask("位置 (可选)"),
    }

    # 添加到台账
    try:
        manager = AssetManager()
        if manager.add_device(device_id, device_info):
            console.print(f"[green]设备已添加到资产台账: {device_id}[/green]")
            return manager.get_connection_info(device_id) or {}
    except Exception as e:
        console.print(f"[red]添加到资产台账失败: {e}[/red]")

    return {}


def get_connection_info() -> Dict[str, Any]:
    """
    交互式获取设备连接信息
    返回连接参数字典
    """
    console.print(Panel.fit("[bold cyan]网络设备连接管理器[/bold cyan]"))

    connection_info = {}

    # 获取设备IP或主机名
    connection_info['host'] = console.input("\n[bold yellow]设备IP或主机名:[/bold yellow] ")

    # 获取设备类型
    console.print("\n[bold]支持的设备厂商:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("编号", style="dim", width=6)
    table.add_column("厂商")
    table.add_column("设备类型")

    vendors = list(DEVICE_TYPES.keys())
    for idx, vendor in enumerate(vendors, 1):
        device_type = DEVICE_TYPES[vendor]
        # 只显示每个类型的一个代表
        if vendor == device_type or vendors.index(vendor) == vendors.index(device_type):
            table.add_row(str(idx), vendor, device_type)

    console.print(table)

    vendor_input = console.input("\n[bold yellow]设备类型 (如: huawei, cisco, h3c, ruijie):[/bold yellow] ").lower()

    # 标准化设备类型
    connection_info['device_type'] = DEVICE_TYPES.get(vendor_input, vendor_input)

    # 获取用户名
    connection_info['username'] = console.input("[bold yellow]用户名:[/bold yellow] ")

    # 获取密码（隐藏输入）
    connection_info['password'] = getpass.getpass("[bold yellow]密码:[/bold yellow] ")

    # 获取端口（可选）
    port_input = console.input("[bold yellow]端口 (默认SSH 22):[/bold yellow] ")
    connection_info['port'] = int(port_input) if port_input else 22

    # 获取enable密码（可选，主要是Cisco设备）
    enable_secret = console.input("[bold yellow]Enable密码 (如不需要请留空):[/bold yellow] ")
    if enable_secret:
        connection_info['secret'] = enable_secret

    # 连接超时设置
    connection_info['timeout'] = 10
    connection_info['session_log'] = 'netmiko_session.log'

    return connection_info


def connect_ssh(connection_info: Dict[str, Any]) -> Optional[ConnectHandler]:
    """
    建立SSH连接
    返回ConnectHandler对象或None
    """
    console.print(f"\n[bold green]正在连接到 {connection_info['host']}...[/bold green]")

    try:
        connection = ConnectHandler(**connection_info)
        console.print(f"[bold green]✓ 成功连接到 {connection_info['host']}[/bold green]")

        # 获取设备提示符和基本信息
        prompt = connection.find_prompt()
        console.print(f"[dim]设备提示符: {prompt}[/dim]")

        return connection

    except NetmikoTimeoutError:
        console.print(f"[bold red]✗ 连接超时: 无法到达 {connection_info['host']}:{connection_info.get('port', 22)}[/bold red]")
        console.print("[yellow]请检查:[/yellow]")
        console.print("  1. 设备IP地址是否正确")
        console.print("  2. 网络连通性 (ping测试)")
        console.print("  3. SSH服务是否启用")
        console.print("  4. 防火墙规则")
        return None

    except NetmikoAuthenticationException:
        console.print(f"[bold red]✗ 认证失败: 用户名或密码错误[/bold red]")
        console.print("[yellow]请检查:[/yellow]")
        console.print("  1. 用户名是否正确")
        console.print("  2. 密码是否正确")
        console.print("  3. 账户是否有SSH登录权限")
        return None

    except Exception as e:
        console.print(f"[bold red]✗ 连接失败: {str(e)}[/bold red]")
        return None


def test_connection(connection: ConnectHandler) -> bool:
    """
    测试连接是否正常
    发送简单的测试命令验证连接可用性
    """
    try:
        # 根据设备类型选择测试命令
        device_type = connection.device_type

        if 'huawei' in device_type or 'comware' in device_type:
            test_command = 'display version'
        elif 'cisco' in device_type:
            test_command = 'show version'
        elif 'ruijie' in device_type:
            test_command = 'show version'
        else:
            test_command = 'display version'

        output = connection.send_command(test_command, read_timeout=10)

        if output:
            console.print("[bold green]✓ 连接测试成功[/bold green]")
            return True
        else:
            console.print("[bold yellow]⚠ 连接异常: 无响应[/bold yellow]")
            return False

    except Exception as e:
        console.print(f"[bold yellow]⚠ 连接测试失败: {str(e)}[/bold yellow]")
        return False


def disconnect(connection: ConnectHandler):
    """
    断开设备连接
    """
    try:
        connection.disconnect()
        console.print("[bold green]✓ 已断开连接[/bold green]")
    except Exception as e:
        console.print(f"[bold yellow]⚠ 断开连接时出现警告: {str(e)}[/bold yellow]")


def main():
    """
    主函数：演示完整的连接流程

    支持命令行参数:
        python device_connector.py              # 交互式输入
        python device_connector.py <IP|名称>    # 从资产台账查找
        python device_connector.py --find <IP>  # 从资产台账查找
        python device_connector.py --add        # 添加设备到台账
        python device_connector.py --list       # 列出所有设备
    """
    try:
        # 解析命令行参数
        if len(sys.argv) > 1:
            arg = sys.argv[1]

            # 列出所有设备
            if arg in ["--list", "list", "ls"]:
                if ASSET_MANAGER_AVAILABLE:
                    from asset_manager import cmd_list
                    cmd_list(AssetManager(), sys.argv[2:])
                else:
                    console.print("[red]资产管理器不可用[/red]")
                return

            # 添加设备
            if arg in ["--add", "add"]:
                add_device_to_inventory()
                return

            # 查找设备
            if arg in ["--find", "find"]:
                query = sys.argv[2] if len(sys.argv) > 2 else ""
                if not query:
                    console.print("[red]请指定要查找的设备 (IP/名称)[/red]")
                    return
                if ASSET_MANAGER_AVAILABLE:
                    from asset_manager import cmd_find
                    cmd_find(AssetManager(), [query])
                else:
                    console.print("[red]资产管理器不可用[/red]")
                return

            # 直接使用参数作为查询词
            if arg.startswith("-"):
                console.print(f"[red]未知选项: {arg}[/red]")
                console.print("使用 --help 查看帮助")
                return

            # 使用第一个参数作为设备标识符
            conn_info, device_id = prompt_or_find_device(arg)
        else:
            # 无参数：交互式输入
            conn_info, device_id = prompt_or_find_device()

        # 检查是否获取到连接信息
        if not conn_info:
            console.print("[yellow]未获取连接信息，操作取消[/yellow]")
            return

        # 建立连接
        connection = connect_ssh(conn_info)

        if connection:
            # 测试连接
            test_connection(connection)

            # 保持连接等待用户命令
            console.print("\n[bold cyan]连接已建立，可以执行命令[/bold cyan]")
            console.print("[dim]使用 command_executor.py 执行具体命令[/dim]")

            # 断开连接
            user_input = console.input("\n[bold yellow]按Enter键断开连接...[/bold yellow]")
            disconnect(connection)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]操作已取消[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]发生错误: {str(e)}[/bold red]")


if __name__ == "__main__":
    main()
