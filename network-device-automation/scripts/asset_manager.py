#!/usr/bin/env python3
"""
网络设备资产台账管理器
提供设备资产的增删改查、导入导出等功能
支持通过IP、主机名、设备名称/别名查找设备
密码使用 base64 编码存储
"""

import os
import sys
import base64
import yaml
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

console = Console()

# 获取技能目录
SKILL_DIR = Path(__file__).parent.parent
INVENTORY_FILE = SKILL_DIR / "assets" / "inventory.yaml"


class AssetManager:
    """资产台账管理器"""

    def __init__(self, inventory_file: Path = INVENTORY_FILE):
        self.inventory_file = inventory_file
        self.data = self._load_inventory()

    def _load_inventory(self) -> Dict[str, Any]:
        """加载资产台账文件"""
        if not self.inventory_file.exists():
            console.print(f"[yellow]资产台账文件不存在，将创建新文件: {self.inventory_file}[/yellow]")
            return {"devices": {}, "groups": {}}

        try:
            with open(self.inventory_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {"devices": {}, "groups": {}}
        except Exception as e:
            console.print(f"[red]加载资产台账失败: {e}[/red]")
            return {"devices": {}, "groups": {}}

    def _save_inventory(self):
        """保存资产台账文件"""
        try:
            self.inventory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.inventory_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.data, f, allow_unicode=True, sort_keys=False, default_flow_style=None)
            return True
        except Exception as e:
            console.print(f"[red]保存资产台账失败: {e}[/red]")
            return False

    @staticmethod
    def encode_password(password: str) -> str:
        """编码密码（base64）"""
        if not password:
            return ""
        return base64.b64encode(password.encode('utf-8')).decode('ascii')

    @staticmethod
    def decode_password(encoded: str) -> str:
        """解码密码"""
        if not encoded:
            return ""
        try:
            return base64.b64decode(encoded.encode('ascii')).decode('utf-8')
        except Exception:
            return ""

    def find_device(self, query: str, return_all_matches: bool = False) -> Optional[Dict[str, Any]]:
        """
        查找设备（多字段匹配）

        支持匹配的字段：
        - 设备ID（devices字典的key）
        - host (IP地址/主机名)
        - name (设备名称)
        - description (描述)

        Args:
            query: 查询字符串（IP、主机名、设备名称等）
            return_all_matches: 是否返回所有匹配结果

        Returns:
            匹配的设备信息字典，如果 return_all_matches=True 返回列表
        """
        query = query.strip().lower()
        matches = []

        for device_id, device_info in self.data.get("devices", {}).items():
            # 匹配设备ID
            if query == device_id.lower():
                if return_all_matches:
                    matches.append((device_id, device_info))
                else:
                    return device_info

            # 匹配IP/主机名
            if device_info.get("host", "").lower() == query:
                if return_all_matches:
                    matches.append((device_id, device_info))
                else:
                    return device_info

            # 匹配设备名称
            if device_info.get("name", "").lower() == query:
                if return_all_matches:
                    matches.append((device_id, device_info))
                else:
                    return device_info

            # 模糊匹配名称/描述
            if query in device_info.get("name", "").lower() or query in device_info.get("description", "").lower():
                matches.append((device_id, device_info))

        if return_all_matches:
            return [{"id": k, **v} for k, v in matches]
        return matches[0][1] if matches else None

    def get_connection_info(self, query: str) -> Optional[Dict[str, Any]]:
        """
        获取设备连接信息（用于自动连接）

        返回适用于 Netmiko ConnectHandler 的参数字典
        密码为空时需要交互式输入
        """
        device = self.find_device(query)
        if not device:
            return None

        conn_info = {
            "host": device.get("host"),
            "device_type": device.get("device_type"),
            "username": device.get("username"),
            "port": device.get("port", 22),
        }

        # 解码密码（如果存在）
        encoded_pwd = device.get("password", "")
        if encoded_pwd:
            conn_info["password"] = self.decode_password(encoded_pwd)

        # 解码enable密码（如果存在）
        encoded_enable = device.get("enable_password", "")
        if encoded_enable:
            conn_info["secret"] = self.decode_password(encoded_enable)

        return conn_info

    def add_device(self, device_id: str, device_info: Dict[str, Any]) -> bool:
        """添加新设备"""
        if device_id in self.data.get("devices", {}):
            console.print(f"[red]设备ID '{device_id}' 已存在，请使用 update 命令更新[/red]")
            return False

        if "devices" not in self.data:
            self.data["devices"] = {}

        # 添加时间戳
        now = datetime.now().strftime("%Y-%m-%d")
        device_info["created_at"] = now
        device_info["updated_at"] = now

        # 编码密码
        if "password" in device_info and device_info["password"]:
            device_info["password"] = self.encode_password(device_info["password"])
        if "enable_password" in device_info and device_info["enable_password"]:
            device_info["enable_password"] = self.encode_password(device_info["enable_password"])

        self.data["devices"][device_id] = device_info
        return self._save_inventory()

    def update_device(self, device_id: str, updates: Dict[str, Any]) -> bool:
        """更新设备信息"""
        if device_id not in self.data.get("devices", {}):
            console.print(f"[red]设备ID '{device_id}' 不存在[/red]")
            return False

        # 更新时间戳
        updates["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        # 编码密码
        if "password" in updates and updates["password"]:
            updates["password"] = self.encode_password(updates["password"])
        if "enable_password" in updates and updates["enable_password"]:
            updates["enable_password"] = self.encode_password(updates["enable_password"])

        self.data["devices"][device_id].update(updates)
        return self._save_inventory()

    def delete_device(self, device_id: str) -> bool:
        """删除设备"""
        if device_id not in self.data.get("devices", {}):
            console.print(f"[red]设备ID '{device_id}' 不存在[/red]")
            return False

        if not Confirm.ask(f"[yellow]确认删除设备 '{device_id}'?[/yellow]"):
            return False

        del self.data["devices"][device_id]
        return self._save_inventory()

    def list_devices(self, group: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有设备（可选按分组或标签过滤）"""
        devices = []
        for device_id, device_info in self.data.get("devices", {}).items():
            # 分组过滤
            if group and device_info.get("group") != group:
                continue
            # 标签过滤
            if tag and tag not in device_info.get("tags", []):
                continue
            devices.append({"id": device_id, **device_info})
        return devices

    def list_groups(self) -> Dict[str, List[str]]:
        """列出所有分组"""
        return self.data.get("groups", {})

    def export_json(self, output_file: Path) -> bool:
        """导出为JSON格式"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            console.print(f"[green]已导出到: {output_file}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]导出失败: {e}[/red]")
            return False

    def import_json(self, input_file: Path) -> bool:
        """从JSON导入"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            self.data.update(imported_data)
            self._save_inventory()
            console.print(f"[green]已从 {input_file} 导入[/green]")
            return True
        except Exception as e:
            console.print(f"[red]导入失败: {e}[/red]")
            return False


# ==================== 命令行界面 ====================

def cmd_list(manager: AssetManager, args: List[str]):
    """列出所有设备"""
    group = args[0] if len(args) > 0 else None
    tag = args[1] if len(args) > 1 else None

    devices = manager.list_devices(group=group, tag=tag)

    if not devices:
        console.print("[yellow]没有找到设备[/yellow]")
        return

    table = Table(title="网络设备资产台账")
    table.add_column("ID", style="cyan", width=15)
    table.add_column("名称", style="green", width=20)
    table.add_column("IP/主机名", style="yellow", width=18)
    table.add_column("厂商", width=10)
    table.add_column("型号", width=12)
    table.add_column("分组", width=10)
    table.add_column("位置", width=15)
    table.add_column("密码", width=8)

    for device in devices:
        has_pwd = "[green]已存储[/green]" if device.get("password") else "[dim]未存储[/dim]"
        table.add_row(
            device.get("id", "")[:15],
            device.get("name", "")[:20],
            device.get("host", "")[:18],
            device.get("vendor", "")[:10],
            device.get("model", "")[:12],
            device.get("group", "")[:10],
            device.get("location", "")[:15],
            has_pwd
        )

    console.print(table)
    console.print(f"\n[dim]共 {len(devices)} 台设备[/dim]")


def cmd_find(manager: AssetManager, args: List[str]):
    """查找设备"""
    if not args:
        console.print("[red]请输入查询内容（IP/主机名/设备名称）[/red]")
        return

    query = args[0]
    matches = manager.find_device(query, return_all_matches=True)

    if not matches:
        console.print(f"[yellow]未找到匹配 '{query}' 的设备[/yellow]")
        return

    if len(matches) == 1:
        device = matches[0]
    else:
        console.print(f"[cyan]找到 {len(matches)} 个匹配设备:[/cyan]")
        for i, m in enumerate(matches, 1):
            console.print(f"  {i}. [green]{m.get('id')}[/green] - {m.get('name')} ({m.get('host')})")
        choice = Prompt.ask("请选择", choices=[str(i) for i in range(1, len(matches) + 1)])
        device = matches[int(choice) - 1]

    # 显示设备详情
    console.print(Panel.fit(f"[bold green]设备详情[/bold green]"))
    console.print(f"  [cyan]ID:[/cyan] {device.get('id')}")
    console.print(f"  [cyan]名称:[/cyan] {device.get('name')}")
    console.print(f"  [cyan]IP:[/cyan] {device.get('host')}")
    console.print(f"  [cyan]类型:[/cyan] {device.get('device_type')}")
    console.print(f"  [cyan]厂商:[/cyan] {device.get('vendor')}")
    console.print(f"  [cyan]型号:[/cyan] {device.get('model')}")
    console.print(f"  [cyan]用户名:[/cyan] {device.get('username')}")
    console.print(f"  [cyan]端口:[/cyan] {device.get('port', 22)}")
    console.print(f"  [cyan]分组:[/cyan] {device.get('group')}")
    console.print(f"  [cyan]位置:[/cyan] {device.get('location')}")
    console.print(f"  [cyan]联系人:[/cyan] {device.get('contact')}")
    console.print(f"  [cyan]标签:[/cyan] {', '.join(device.get('tags', []))}")
    console.print(f"  [cyan]描述:[/cyan] {device.get('description')}")

    # 显示连接命令
    console.print(f"\n[dim]连接命令: python scripts/device_connector.py --find {device.get('host')}[/dim]")


def cmd_add(manager: AssetManager, args: List[str]):
    """添加新设备"""
    console.print(Panel.fit("[bold cyan]添加新设备[/bold cyan]"))

    device_id = Prompt.ask("[bold yellow]设备ID[/bold yellow] (如: core-sw-01)")
    if not device_id:
        console.print("[red]设备ID不能为空[/red]")
        return

    device_info = {
        "name": Prompt.ask("设备名称"),
        "host": Prompt.ask("IP地址或主机名"),
        "device_type": Prompt.ask("设备类型", choices=["huawei", "hp_comware", "cisco_ios", "cisco_nxos", "ruijie_os"]),
        "vendor": Prompt.ask("厂商 (可选)"),
        "model": Prompt.ask("型号 (可选)"),
        "username": Prompt.ask("用户名"),
        "password": Prompt.ask("密码 (可选，留空则使用时输入)", password=True),
        "port": Prompt.ask("SSH端口", default="22"),
        "enable_password": Prompt.ask("Enable密码 (可选，留空跳过)", password=True),
        "group": Prompt.ask("设备分组 (可选)"),
        "description": Prompt.ask("描述 (可选)"),
        "location": Prompt.ask("位置 (可选)"),
        "contact": Prompt.ask("联系人 (可选)"),
        "tags": Prompt.ask("标签 (可选，逗号分隔)").split(",") if Prompt.ask("标签 (可选，逗号分隔)", default="") else [],
    }

    if manager.add_device(device_id, device_info):
        console.print(f"[green]设备 '{device_id}' 添加成功[/green]")


def cmd_update(manager: AssetManager, args: List[str]):
    """更新设备信息"""
    if not args:
        console.print("[red]请指定要更新的设备ID[/red]")
        return

    device_id = args[0]
    device = manager.data.get("devices", {}).get(device_id)

    if not device:
        console.print(f"[red]设备 '{device_id}' 不存在[/red]")
        return

    console.print(Panel.fit(f"[bold cyan]更新设备: {device_id}[/bold cyan]"))
    console.print(f"[dim]当前值: {device.get('name')} ({device.get('host')})[/dim]\n")

    updates = {}

    # 交互式更新每个字段
    fields = {
        "name": "设备名称",
        "host": "IP地址",
        "device_type": "设备类型",
        "username": "用户名",
        "port": "端口",
        "group": "分组",
        "description": "描述",
        "location": "位置",
        "contact": "联系人",
    }

    for field, label in fields.items():
        current = device.get(field, "")
        new_value = Prompt.ask(f"{label} [dim]({current})[/dim]", default=current)
        if new_value != current:
            updates[field] = new_value

    # 密码更新（需要确认）
    if Confirm.ask("是否更新密码?", default=False):
        updates["password"] = Prompt.ask("新密码", password=True)

    if manager.update_device(device_id, updates):
        console.print(f"[green]设备 '{device_id}' 更新成功[/green]")


def cmd_delete(manager: AssetManager, args: List[str]):
    """删除设备"""
    if not args:
        console.print("[red]请指定要删除的设备ID[/red]")
        return

    device_id = args[0]
    if manager.delete_device(device_id):
        console.print(f"[green]设备 '{device_id}' 已删除[/green]")


def cmd_export(manager: AssetManager, args: List[str]):
    """导出资产台账"""
    output_file = Path(args[0]) if len(args) > 0 else Path("inventory_export.json")
    manager.export_json(output_file)


def cmd_import(manager: AssetManager, args: List[str]):
    """导入资产台账"""
    if not args:
        console.print("[red]请指定要导入的JSON文件[/red]")
        return

    input_file = Path(args[0])
    manager.import_json(input_file)


def cmd_groups(manager: AssetManager, args: List[str]):
    """列出所有分组"""
    groups = manager.list_groups()

    if not groups:
        console.print("[yellow]没有定义分组[/yellow]")
        return

    for group_name, group_desc in groups.items():
        console.print(f"  [cyan]{group_name}:[/cyan] {group_desc}")


def print_usage():
    """打印帮助信息"""
    console.print(Panel.fit("[bold cyan]网络设备资产台账管理器[/bold cyan]"))
    console.print("\n[bold]用法:[/bold]")
    console.print("  python scripts/asset_manager.py <命令> [参数...]")
    console.print("\n[bold]命令:[/bold]")
    console.print("  [cyan]list[/cyan] [分组] [标签]          - 列出所有设备（可选过滤）")
    console.print("  [cyan]find[/cyan] <IP|名称>              - 查找设备")
    console.print("  [cyan]add[/cyan]                        - 添加新设备（交互式）")
    console.print("  [cyan]update[/cyan] <设备ID>             - 更新设备信息")
    console.print("  [cyan]delete[/cyan] <设备ID>             - 删除设备")
    console.print("  [cyan]export[/cyan] [输出文件]           - 导出为JSON")
    console.print("  [cyan]import[/cyan] <JSON文件>           - 从JSON导入")
    console.print("  [cyan]groups[/cyan]                     - 列出所有分组")
    console.print("\n[bold]示例:[/bold]")
    console.print("  python scripts/asset_manager.py list")
    console.print("  python scripts/asset_manager.py find 192.168.1.1")
    console.print("  python scripts/asset_manager.py find 核心交换机")
    console.print("  python scripts/asset_manager.py add")
    console.print("  python scripts/asset_manager.py update core-sw-01")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    manager = AssetManager()

    commands = {
        "list": cmd_list,
        "find": cmd_find,
        "add": cmd_add,
        "update": cmd_update,
        "delete": cmd_delete,
        "export": cmd_export,
        "import": cmd_import,
        "groups": cmd_groups,
    }

    if command in commands:
        commands[command](manager, args)
    else:
        console.print(f"[red]未知命令: {command}[/red]")
        print_usage()


if __name__ == "__main__":
    main()
