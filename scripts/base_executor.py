#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络设备执行器基类
提供通用的命令执行、帮助查询等功能
"""

import sys
import time
import re
import paramiko
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    """网络设备执行器基类"""

    def __init__(self, host: str, username: str, password: str,
                 port: int = 22, timeout: int = 30, auto_help: bool = False):
        """
        初始化执行器

        Args:
            host: 设备IP地址
            username: 用户名
            password: 密码
            port: SSH端口
            timeout: 连接超时时间
            auto_help: 命令失败时自动查询帮助
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.auto_help = auto_help
        self.device_type = "Unknown"

        # SSH连接对象
        self.ssh_client = None
        self.shell = None

        # 平台检测
        self.is_windows = sys.platform == 'win32'

    def log(self, message: str, level: str = "INFO"):
        """日志输出（兼容Windows编码）"""
        if self.is_windows:
            markers = {
                "INFO": "[INFO]",
                "OK": "[OK]",
                "ERROR": "[ERROR]",
                "WARNING": "[WARNING]",
                "HELP": "[HELP]"
            }
        else:
            markers = {
                "INFO": "[INFO]",
                "OK": "[OK]",
                "ERROR": "[ERROR]",
                "WARNING": "[WARNING]",
                "HELP": "[HELP]"
            }
        print(f"{markers.get(level, '['+level+']')} {message}")

    def connect(self) -> bool:
        """
        建立SSH连接

        Returns:
            是否连接成功
        """
        self.log(f"正在连接到 {self.device_type} 设备 {self.host}...", "INFO")

        try:
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

            # 使用invoke_shell
            self.shell = self.ssh_client.invoke_shell()
            time.sleep(2)

            # 清空初始输出
            if self.shell.recv_ready():
                self.shell.recv(65535)

            self.log(f"已连接", "OK")
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

    def query_help(self, command_prefix: str, timeout: int = 10) -> str:
        """
        查询命令帮助信息

        Args:
            command_prefix: 命令前缀（查询该命令的帮助）
            timeout: 查询超时时间

        Returns:
            帮助信息输出
        """
        if not self.shell:
            return ""

        self.log(f"查询命令帮助: {command_prefix} ?", "HELP")

        try:
            # 发送命令+空格+?
            self.shell.send(command_prefix + ' ?\n')
            time.sleep(0.5)

            # 获取帮助输出
            output = ""
            start_time = time.time()

            while time.time() - start_time < timeout:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                    output += chunk

                    # 检测是否完成（通常帮助以提示符结束）
                    if re.search(r'<\w+>|\[\S+\]', chunk):
                        time.sleep(0.3)
                        if not self.shell.recv_ready():
                            break

                time.sleep(0.1)

            return output

        except Exception as e:
            self.log(f"查询帮助失败: {str(e)}", "ERROR")
            return ""

    def query_tab_complete(self, command_prefix: str, timeout: int = 5) -> List[str]:
        """
        使用Tab补全获取命令选项

        Args:
            command_prefix: 命令前缀
            timeout: 查询超时时间

        Returns:
            可能的补全选项列表
        """
        if not self.shell:
            return []

        try:
            # 发送命令前缀
            self.shell.send(command_prefix)
            time.sleep(0.2)

            # 发送Tab
            self.shell.send('\t')
            time.sleep(0.5)

            # 获取补全输出
            output = ""
            start_time = time.time()

            while time.time() - start_time < timeout:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                    output += chunk
                    break
                time.sleep(0.1)

            # 解析补全选项
            options = []
            for line in output.split('\n'):
                line = line.strip()
                if line and not line.startswith('<') and not line.startswith('['):
                    options.append(line)

            return options

        except Exception as e:
            return []

    def disconnect(self):
        """断开连接"""
        try:
            if self.shell:
                self.shell.close()
            if self.ssh_client:
                self.ssh_client.close()
            self.log("已断开连接", "INFO")
        except:
            pass

    @abstractmethod
    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行单条命令（子类实现）"""
        pass

    @abstractmethod
    def execute_commands(self, commands: List[str],
                        stop_on_error: bool = True) -> Dict[str, Any]:
        """批量执行命令（子类实现）"""
        pass
