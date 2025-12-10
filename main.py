#!/usr/bin/env python3
# ANTI G.B for SSD – Bản tối giản
# Giám sát tiến trình nào ghi ổ đĩa quá mạnh (> 80 MB/s)
# Nếu --kill được bật thì kill luôn process nghi ngờ.

import psutil
import time
import argparse

WRITE_LIMIT = 80 * 1024 * 1024    # 80 MB/s
CHECK_INTERVAL = 5                # kiểm tra mỗi 5 giây
SUSPICIOUS_COUNT = 3              # vượt ngưỡng 3 lần liên tiếp => xác nhận

whitelist = {
    "systemd", "sshd", "bash", "python3",
    "dockerd", "containerd", "nginx", "mysql",
}

def format_size(b):
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


def main(kill_mode=False):
    print(f"[ANTI-GB] Đang chạy... Giới hạn {WRITE_LIMIT/1024/1024:.0f} MB/s")
    if kill_mode:
        print("[!] Kill mode: BẬT — Tiến trình nghi ngờ sẽ bị kill.\n")

    prev_io = {}
    suspicious = {}

    while True:
        time.sleep(CHECK_INTERVAL)
        for p in psutil.process_iter(["pid", "name"]):
            try:
                io = p.io_counters()
                pid = p.pid
                name = p.name()

                if name in whitelist:
                    continue

                if pid not in prev_io:
                    prev_io[pid] = io.write_bytes
                    continue

                diff = io.write_bytes - prev_io[pid]
                wps = diff / CHECK_INTERVAL  # bytes/sec

                if wps > WRITE_LIMIT:
                    suspicious[pid] = suspicious.get(pid, 0) + 1
                    print(
                        f"[!] PID {pid} ({name}) ghi {format_size(wps)}/s "
                        f"({suspicious[pid]}/{SUSPICIOUS_COUNT})"
                    )

                    # đủ số lần => kill
                    if suspicious[pid] >= SUSPICIOUS_COUNT and kill_mode:
                        print(f"[X] Kill PID {pid} ({name})…")
                        try:
                            p.kill()
                        except Exception as e:
                            print(f"Lỗi kill: {e}")

                # reset nếu an toàn
                elif pid in suspicious:
                    suspicious[pid] = 0

                prev_io[pid] = io.write_bytes

            except Exception:
                continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kill", action="store_true",
                        help="Kill tiến trình nghi đào GB")
    args = parser.parse_args()
    main(kill_mode=args.kill)
