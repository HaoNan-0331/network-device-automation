#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 串口执行器：通过 console 串口对网络设备执行命令
# 与 SSH 执行器（huawei/h3c/cisco_executor.py）统一接口：--device/--commands，返回 JSON
# 支持华为/H3C/思科分页、Y/N 自动确认、多行命令
#
# 用法：
#   python serial_executor.py --port COM3 --commands "display version" "display interface brief"
#   python serial_executor.py --device <台账设备> --commands "show running-config"
#   python serial_executor.py --port COM3 --baud 9600 --commands "show ip route"
#
# 资产台账登记串口设备（assets/inventory.yaml）：
#   devices:
#     sw-console:
#       name: "S220-console"
#       device_type: serial
#       port: COM3
#       baud_rate: 9600
#       vendor: huawei
import serial, sys, time, json, argparse, re
from pathlib import Path

MORE_MARKS = [b"---- More ----", b"--More--", b"  ---- More ----"]
ANSI_RE = re.compile(rb'\x1b\[[0-9;?]*[A-Za-z]')
YN_RE = re.compile(rb'\[Y/N\]', re.IGNORECASE)
# 常见错误关键词（跨厂商）
ERR_RE = re.compile(r'(\bError\b|%\s*(Invalid|Incomplete|Unrecognized|Wrong)\b|Unrecognized command)', re.IGNORECASE)


def clean(buf: bytes) -> str:
    b = buf.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    b = ANSI_RE.sub(b'', b)
    b = b.replace(b'\x08', b'')
    b = re.sub(rb'[-]{4} More [-]{4}', b'', b)
    b = re.sub(rb'-{2,}More-{2,}', b'', b)
    b = re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]', b'', b)
    return b.decode("utf-8", "ignore")


def send_and_recv(s, cmd: str, idle: float = 2.0, max_wait: float = 40.0) -> str:
    """发送一条（可多行）命令，采集回显直到静默 idle 秒"""
    s.reset_input_buffer()
    s.reset_output_buffer()
    payload = (cmd.replace("\n", "\r\n") + "\r\n").encode("utf-8", "ignore")
    s.write(payload)
    s.flush()
    buf = bytearray()
    last = time.time()
    start = time.time()
    while True:
        n = s.in_waiting
        if n:
            buf += s.read(n)
            last = time.time()
        else:
            time.sleep(0.05)
        elapsed = time.time() - last
        tail = bytes(buf[-48:])
        if any(m in tail for m in MORE_MARKS) and elapsed > 0.4:
            s.write(b" "); s.flush(); last = time.time(); continue
        if YN_RE.search(tail) and elapsed > 0.4:
            s.write(b"Y\r\n"); s.flush(); buf.clear(); last = time.time(); continue
        if elapsed > idle:
            break
        if time.time() - start > max_wait:
            break
    return clean(bytes(buf))


def find_device(device_id: str):
    """从资产台账查找串口设备"""
    inv = Path(__file__).parent.parent / "assets" / "inventory.yaml"
    if not inv.exists():
        return None
    try:
        import yaml
        data = yaml.safe_load(inv.read_text(encoding="utf-8")) or {}
        devices = data.get("devices", {})
        for k, v in devices.items():
            if k == device_id or v.get("name") == device_id or v.get("host") == device_id:
                if v.get("device_type") == "serial" or v.get("port"):
                    return v
    except Exception:
        return None
    return None


def main():
    ap = argparse.ArgumentParser(description="串口执行器（console 口运维）")
    ap.add_argument("--device", help="设备标识（资产台账中的 ID/名称/IP）")
    ap.add_argument("--port", help="串口号，如 COM3（未指定则从台账查）")
    ap.add_argument("--baud", type=int, default=9600, help="波特率，默认 9600")
    ap.add_argument("--commands", nargs="+", required=True, help="要执行的命令（每条一次采集）")
    ap.add_argument("--idle", type=float, default=2.0, help="静默多少秒认为输出结束")
    ap.add_argument("--max", type=float, default=40.0, help="单条命令兜底超时(秒)")
    ap.add_argument("--stop-on-error", action="store_true", help="遇错中断（默认每条都执行）")
    args = ap.parse_args()

    port, baud = args.port, args.baud
    if args.device and not port:
        dev = find_device(args.device)
        if dev:
            port = dev.get("port")
            baud = dev.get("baud_rate", baud)
    if not port:
        print(json.dumps({"success": False, "error": "未指定串口（用 --port 或在台账登记 port）"},
                         ensure_ascii=False))
        sys.exit(1)

    try:
        s = serial.Serial(port, baud, bytesize=8, parity='N', stopbits=1,
                          timeout=0.2, write_timeout=3, exclusive=True)
    except Exception as e:
        print(json.dumps({"success": False, "error": "打开串口失败: {}".format(e)},
                         ensure_ascii=False))
        sys.exit(1)

    results, executed, failed_at = [], 0, None
    try:
        for cmd in args.commands:
            try:
                out = send_and_recv(s, cmd, args.idle, args.max)
                err = None
                if ERR_RE.search(out):
                    err = "命令执行可能有错误"
                results.append({"command": cmd, "success": err is None,
                                "output": out, "error": err})
                executed += 1
                if err and args.stop_on_error:
                    failed_at = cmd
                    break
            except Exception as e:
                results.append({"command": cmd, "success": False, "output": "", "error": str(e)})
                failed_at = cmd
                if args.stop_on_error:
                    break
    finally:
        s.close()

    print(json.dumps({
        "success": failed_at is None,
        "executed": executed,
        "total": len(args.commands),
        "failed_at": failed_at,
        "results": results
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
