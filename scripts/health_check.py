#!/usr/bin/env python3
"""
设备健康检查和巡检工具
支持自动化巡检、健康评分和报告生成
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from netmiko import ConnectHandler
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

console = Console()


class HealthChecker:
    """设备健康检查器"""

    def __init__(self, connection: ConnectHandler):
        self.connection = connection
        self.device_type = connection.device_type
        self.hostname = self._get_hostname()
        self.check_results: Dict[str, Any] = {}
        self.score = 100
        self.issues: List[Dict[str, str]] = []

    def _get_hostname(self) -> str:
        """获取设备主机名"""
        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                output = self.connection.send_command('display current-configuration | include hostname')
            elif 'cisco' in self.device_type:
                output = self.connection.send_command('show running-config | include hostname')
            else:
                output = self.connection.send_command('show running-config')

            for line in output.split('\n'):
                if 'hostname' in line.lower():
                    return line.split()[-1].strip()

            return self.connection.host

        except Exception:
            return self.connection.host

    def _parse_cpu_usage(self, output: str) -> float:
        """解析CPU使用率"""
        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                # 华为/H3C格式
                match = re.search(r'CPU utilization.*?(\d+)%', output)
            elif 'cisco' in self.device_type:
                # Cisco格式
                match = re.search(r'CPU utilization.*?(\d+)%', output)
            else:
                match = re.search(r'(\d+)%', output)

            if match:
                return float(match.group(1))
            return 0.0

        except Exception:
            return 0.0

    def _parse_memory_usage(self, output: str) -> Dict[str, Any]:
        """解析内存使用情况"""
        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                # 华为/H3C: 查找 "Total Size: xxx KB" 和 "Used: xxx KB"
                total_match = re.search(r'Total.*?(\d+)', output)
                used_match = re.search(r'Used.*?(\d+)', output)

                if total_match and used_match:
                    total = int(total_match.group(1))
                    used = int(used_match.group(1))
                    usage_percent = (used / total) * 100 if total > 0 else 0

                    return {
                        'total': total,
                        'used': used,
                        'free': total - used,
                        'usage_percent': usage_percent
                    }

            elif 'cisco' in self.device_type:
                # Cisco格式
                match = re.search(r'Processor.*?(\d+).*?(\d+).*?(\d+)', output)
                if match:
                    total = int(match.group(1))
                    used = int(match.group(2))
                    free = int(match.group(3))
                    usage_percent = (used / total) * 100 if total > 0 else 0

                    return {
                        'total': total,
                        'used': used,
                        'free': free,
                        'usage_percent': usage_percent
                    }

            return {'total': 0, 'used': 0, 'free': 0, 'usage_percent': 0}

        except Exception:
            return {'total': 0, 'used': 0, 'free': 0, 'usage_percent': 0}

    def _parse_interface_errors(self, output: str) -> List[Dict[str, Any]]:
        """解析接口错误统计"""
        interfaces = []
        try:
            lines = output.split('\n')
            for line in lines:
                # 查找包含错误的接口
                if 'error' in line.lower() or 'crc' in line.lower():
                    interfaces.append({
                        'line': line.strip()
                    })

        except Exception:
            pass

        return interfaces

    def _check_log_errors(self, output: str) -> List[Dict[str, str]]:
        """检查日志中的错误和告警"""
        errors = []
        error_keywords = ['error', 'failed', 'down', 'loss', 'timeout',
                         'critical', 'emergency', 'alert']

        try:
            lines = output.split('\n')
            for line in lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in error_keywords):
                    errors.append({
                        'message': line.strip(),
                        'level': 'high' if 'error' in line_lower or 'critical' in line_lower else 'medium'
                    })

        except Exception:
            pass

        return errors

    def check_system_info(self) -> Dict[str, str]:
        """检查系统基本信息"""
        console.print("[cyan]检查系统信息...[/cyan]")

        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                output = self.connection.send_command('display version')
            else:
                output = self.connection.send_command('show version')

            # 提取关键信息
            info = {
                'hostname': self.hostname,
                'device_type': self.device_type,
                'raw_output': output[:500]  # 保存部分输出用于参考
            }

            # 尝试提取型号、版本等
            for line in output.split('\n'):
                if 'Huawei' in line or 'H3C' in line or 'Cisco' in line:
                    info['model'] = line.strip()
                    break
                if 'Software' in line or 'Version' in line:
                    info['version'] = line.strip()

            self.check_results['system_info'] = info
            return info

        except Exception as e:
            self.check_results['system_info'] = {'error': str(e)}
            return {'error': str(e)}

    def check_cpu_memory(self) -> Dict[str, Any]:
        """检查CPU和内存使用率"""
        console.print("[cyan]检查CPU和内存使用率...[/cyan]")

        cpu_result = {'usage': 0, 'status': 'unknown'}
        memory_result = {'usage_percent': 0, 'status': 'unknown'}

        try:
            # 检查CPU
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                cpu_cmd = 'display cpu-usage'
            else:
                cpu_cmd = 'show processes cpu'

            cpu_output = self.connection.send_command(cpu_cmd)
            cpu_usage = self._parse_cpu_usage(cpu_output)
            cpu_result['usage'] = cpu_usage

            if cpu_usage > 90:
                cpu_result['status'] = 'critical'
                cpu_result['message'] = f'CPU使用率过高: {cpu_usage}%'
                self.score -= 20
                self.issues.append({
                    'category': 'CPU',
                    'severity': 'critical',
                    'message': cpu_result['message']
                })
            elif cpu_usage > 70:
                cpu_result['status'] = 'warning'
                cpu_result['message'] = f'CPU使用率较高: {cpu_usage}%'
                self.score -= 10
                self.issues.append({
                    'category': 'CPU',
                    'severity': 'warning',
                    'message': cpu_result['message']
                })
            else:
                cpu_result['status'] = 'ok'
                cpu_result['message'] = f'CPU使用率正常: {cpu_usage}%'

            # 检查内存
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                mem_cmd = 'display memory-usage'
            else:
                mem_cmd = 'show memory statistics'

            mem_output = self.connection.send_command(mem_cmd)
            memory_info = self._parse_memory_usage(mem_output)
            memory_result = memory_info
            mem_usage = memory_info.get('usage_percent', 0)

            if mem_usage > 90:
                memory_result['status'] = 'critical'
                memory_result['message'] = f'内存使用率过高: {mem_usage:.1f}%'
                self.score -= 20
                self.issues.append({
                    'category': 'Memory',
                    'severity': 'critical',
                    'message': memory_result['message']
                })
            elif mem_usage > 80:
                memory_result['status'] = 'warning'
                memory_result['message'] = f'内存使用率较高: {mem_usage:.1f}%'
                self.score -= 10
                self.issues.append({
                    'category': 'Memory',
                    'severity': 'warning',
                    'message': memory_result['message']
                })
            else:
                memory_result['status'] = 'ok'
                memory_result['message'] = f'内存使用率正常: {mem_usage:.1f}%'

            self.check_results['cpu'] = cpu_result
            self.check_results['memory'] = memory_result

            return {'cpu': cpu_result, 'memory': memory_result}

        except Exception as e:
            self.check_results['cpu'] = {'error': str(e)}
            self.check_results['memory'] = {'error': str(e)}
            return {'cpu': {'error': str(e)}, 'memory': {'error': str(e)}}

    def check_interfaces(self) -> List[Dict[str, Any]]:
        """检查接口状态"""
        console.print("[cyan]检查接口状态...[/cyan]")

        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                cmd = 'display interface brief'
            else:
                cmd = 'show ip interface brief'

            output = self.connection.send_command(cmd)

            # 简单统计
            lines = output.split('\n')
            up_count = 0
            down_count = 0

            for line in lines:
                if 'up' in line.lower():
                    up_count += 1
                elif 'down' in line.lower() and 'administratively' not in line.lower():
                    down_count += 1

            result = {
                'up_count': up_count,
                'down_count': down_count,
                'total_count': up_count + down_count
            }

            if down_count > 0:
                result['status'] = 'warning'
                result['message'] = f'有 {down_count} 个接口处于down状态'
                self.score -= 5 * min(down_count, 5)
                self.issues.append({
                    'category': 'Interface',
                    'severity': 'warning',
                    'message': result['message']
                })
            else:
                result['status'] = 'ok'
                result['message'] = '所有接口状态正常'

            self.check_results['interfaces'] = result
            return [result]

        except Exception as e:
            self.check_results['interfaces'] = {'error': str(e)}
            return [{'error': str(e)}]

    def check_logs(self) -> List[Dict[str, str]]:
        """检查日志中的错误和告警"""
        console.print("[cyan]检查系统日志...[/cyan]")

        try:
            if 'huawei' in self.device_type or 'comware' in self.device_type:
                cmd = 'display logbuffer'
            else:
                cmd = 'show logging'

            output = self.connection.send_command(cmd, read_timeout=30)
            errors = self._check_log_errors(output)

            if errors:
                critical_count = sum(1 for e in errors if e['level'] == 'high')
                if critical_count > 5:
                    self.score -= 15
                    status = 'critical'
                elif critical_count > 0:
                    self.score -= 5
                    status = 'warning'
                else:
                    self.score -= 2
                    status = 'info'

                self.issues.extend([
                    {
                        'category': 'Log',
                        'severity': e['level'],
                        'message': e['message'][:100]
                    }
                    for e in errors[:10]  # 只记录前10条
                ])

                result = {
                    'status': status,
                    'error_count': len(errors),
                    'errors': errors[:10]
                }
            else:
                result = {
                    'status': 'ok',
                    'message': '日志中无明显错误',
                    'error_count': 0
                }

            self.check_results['logs'] = result
            return errors[:10]

        except Exception as e:
            self.check_results['logs'] = {'error': str(e)}
            return []

    def run_full_check(self) -> Dict[str, Any]:
        """运行完整的健康检查"""
        console.print(Panel(f"[bold cyan]设备健康检查: {self.hostname}[/bold cyan]"))

        start_time = datetime.now()

        # 运行各项检查
        self.check_system_info()
        self.check_cpu_memory()
        self.check_interfaces()
        self.check_logs()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 汇总结果
        self.check_results['summary'] = {
            'hostname': self.hostname,
            'score': max(0, self.score),  # 确保不低于0
            'issue_count': len(self.issues),
            'duration': f'{duration:.2f}s',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 确定总体状态
        if self.score >= 90:
            overall_status = 'excellent'
        elif self.score >= 70:
            overall_status = 'good'
        elif self.score >= 50:
            overall_status = 'warning'
        else:
            overall_status = 'critical'

        self.check_results['summary']['status'] = overall_status

        return self.check_results

    def display_results(self):
        """显示检查结果"""
        console.print("\n")

        # 健康评分
        score = self.check_results['summary']['score']
        status = self.check_results['summary']['status']

        if status == 'excellent':
            score_color = 'green'
        elif status == 'good':
            score_color = 'yellow'
        elif status == 'warning':
            score_color = 'orange3'
        else:
            score_color = 'red'

        console.print(Panel(f"[bold {score_color}]健康评分: {score}/100 ({status.upper()})[/bold {score_color}]"))

        # 系统信息表
        if 'system_info' in self.check_results:
            info = self.check_results['system_info']
            table = Table(title="系统信息", show_header=True)
            table.add_column("项目")
            table.add_column("值")

            table.add_row("主机名", info.get('hostname', 'N/A'))
            table.add_row("设备类型", info.get('device_type', 'N/A'))
            if 'model' in info:
                table.add_row("设备型号", info.get('model', 'N/A'))
            if 'version' in info:
                table.add_row("软件版本", info.get('version', 'N/A'))

            console.print(table)

        # CPU和内存状态
        if 'cpu' in self.check_results and 'memory' in self.check_results:
            cpu = self.check_results['cpu']
            memory = self.check_results['memory']

            table = Table(title="资源使用", show_header=True)
            table.add_column("资源")
            table.add_column("使用率")
            table.add_column("状态")

            cpu_usage = cpu.get('usage', 0)
            mem_usage = memory.get('usage_percent', 0)

            cpu_status = cpu.get('status', 'unknown')
            mem_status = memory.get('status', 'unknown')

            # 根据状态设置颜色
            cpu_color = 'green' if cpu_status == 'ok' else ('yellow' if cpu_status == 'warning' else 'red')
            mem_color = 'green' if mem_status == 'ok' else ('yellow' if mem_status == 'warning' else 'red')

            table.add_row("CPU", f"{cpu_usage}%", f"[{cpu_color}]{cpu_status}[/{cpu_color}]")
            table.add_row("内存", f"{mem_usage:.1f}%", f"[{mem_color}]{mem_status}[/{mem_color}]")

            console.print(table)

        # 问题列表
        if self.issues:
            console.print("\n[bold yellow]发现的问题:[/bold yellow]\n")

            issue_table = Table(show_header=True)
            issue_table.add_column("类别")
            issue_table.add_column("严重性")
            issue_table.add_column("描述")

            for issue in self.issues[:20]:  # 最多显示20个问题
                severity = issue['severity']
                color = 'red' if severity == 'critical' else ('yellow' if severity == 'warning' else 'dim')
                issue_table.add_row(
                    issue['category'],
                    f"[{color}]{severity}[/{color}]",
                    issue['message']
                )

            console.print(issue_table)

    def save_report(self, output_file: str, format: str = 'json'):
        """
        保存检查报告

        Args:
            output_file: 输出文件路径
            format: 报告格式 (json, md)
        """
        try:
            if format == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.check_results, f, indent=2, ensure_ascii=False)

            elif format == 'md':
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 设备健康检查报告\n\n")
                    f.write(f"**设备**: {self.hostname}\n")
                    f.write(f"**时间**: {self.check_results['summary']['timestamp']}\n")
                    f.write(f"**评分**: {self.check_results['summary']['score']}/100\n")
                    f.write(f"**状态**: {self.check_results['summary']['status']}\n\n")

                    if self.issues:
                        f.write(f"## 发现的问题 ({len(self.issues)})\n\n")
                        for issue in self.issues:
                            f.write(f"- [{issue['severity'].upper()}] {issue['category']}: {issue['message']}\n")

            console.print(f"[bold green]✓ 报告已保存到: {output_file}[/bold green]")

        except Exception as e:
            console.print(f"[bold red]✗ 保存报告失败: {str(e)}[/bold red]")


def main():
    """
    主函数演示
    """
    console.print(Panel("[bold cyan]设备健康检查工具[/bold cyan]"))
    console.print("[yellow]请先使用 device_connector.py 建立连接[/yellow]")

    # 示例用法
    # from device_connector import connect_ssh
    #
    # # 建立连接
    # connection = connect_ssh(conn_info)
    #
    # # 创建健康检查器
    # checker = HealthChecker(connection)
    #
    # # 运行完整检查
    # results = checker.run_full_check()
    #
    # # 显示结果
    # checker.display_results()
    #
    # # 保存报告
    # checker.save_report('health_check_report.json')
    # checker.save_report('health_check_report.md', format='md')


if __name__ == "__main__":
    main()
