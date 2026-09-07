#!/usr/bin/env python3

import os
import re
import random
import subprocess
from collections import OrderedDict


INPUT_FILE = "zubo_unicom.body"
OUTPUT_FILE = "zubo_unicom.filtered"

# 每个 IPTV 服务器最多测试两个频道
MAX_TESTS = 2

# 单个频道最多接收 5 秒
TIMEOUT = 5

# 至少收到 100 KB 数据才认为有效
MIN_BYTES = 100 * 1024


# ============================================================
# 读取 M3U
# ============================================================

def load_m3u(filename):

    groups = OrderedDict()
    entries = []

    with open(filename, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    i = 0

    while i < len(lines):

        if lines[i].startswith("#EXTINF"):

            extinf = lines[i]

            if i + 1 < len(lines):

                url = lines[i + 1]

                if url.startswith(("http://", "https://")):

                    # 提取服务器部分：
                    #
                    # http://1.58.66.11:4000
                    #
                    # 而不是：
                    #
                    # /rtp/229.58.190.176:5000

                    match = re.match(
                        r"^(https?://[^/]+)",
                        url
                    )

                    if match:

                        server = match.group(1)

                        if server not in groups:
                            groups[server] = []

                        channel = {
                            "extinf": extinf,
                            "url": url
                        }

                        groups[server].append(channel)

                        entries.append({
                            "extinf": extinf,
                            "url": url,
                            "server": server
                        })

                    i += 2
                    continue

        i += 1

    return groups, entries


# ============================================================
# 选择测试频道
# ============================================================

def choose_test_channels(channels):

    # --------------------------------------------------------
    # 优先 CCTV-1
    # --------------------------------------------------------

    cctv1 = [
        channel
        for channel in channels
        if re.search(
            r"CCTV[-_ ]?1(?:\b|[^0-9])",
            channel["extinf"],
            re.IGNORECASE
        )
    ]

    # --------------------------------------------------------
    # 其次 CCTV-5
    # --------------------------------------------------------

    cctv5 = [
        channel
        for channel in channels
        if re.search(
            r"CCTV[-_ ]?5(?:\b|[^0-9])",
            channel["extinf"],
            re.IGNORECASE
        )
    ]

    preferred = cctv1 + cctv5

    # --------------------------------------------------------
    # 第一次测试
    #
    # CCTV-1 / CCTV-5 中随机选择
    # 如果都没有，则全部频道随机选择
    # --------------------------------------------------------

    if preferred:
        first = random.choice(preferred)
    else:
        first = random.choice(channels)

    # --------------------------------------------------------
    # 第二次测试
    #
    # 从剩余频道中随机选择
    # --------------------------------------------------------

    remaining = [
        channel
        for channel in channels
        if channel["url"] != first["url"]
    ]

    if remaining:
        second = random.choice(remaining)
    else:
        second = None

    return [first, second]


# ============================================================
# 测试 IPTV 流
# ============================================================

def test_stream(url):

    tmp_file = "/tmp/iptv_test.ts"

    # 删除旧测试文件
    try:
        os.remove(tmp_file)
    except FileNotFoundError:
        pass

    try:

        print(f"        Testing: {url}")

        # ----------------------------------------------------
        # 使用 GET，而不是 HEAD
        #
        # IPTV 是持续视频流。
        #
        # curl 到 TIMEOUT 后退出是正常现象，
        # 所以不能简单根据 curl 返回值判断。
        # ----------------------------------------------------

        subprocess.run(
            [
                "curl",

                # IPv4
                "-4",

                # 跟随 HTTP 301/302
                "-L",

                # TCP 连接最多等待 3 秒
                "--connect-timeout",
                "3",

                # 总共最多测试 5 秒
                "--max-time",
                str(TIMEOUT),

                # 静默
                "-s",

                # 输出到临时文件
                "-o",
                tmp_file,

                url
            ],

            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,

            # 防止 curl 自己异常卡死
            timeout=TIMEOUT + 3
        )

        # ----------------------------------------------------
        # 获取收到的数据大小
        # ----------------------------------------------------

        try:
            size = os.path.getsize(tmp_file)
        except OSError:
            size = 0

        print(f"        Received: {size:,} bytes")

        # ----------------------------------------------------
        # 判断
        # ----------------------------------------------------

        if size >= MIN_BYTES:

            print("        ✓ STREAM VALID")

            return True

        else:

            print("        ✗ STREAM INVALID")

            return False

    except Exception as e:

        print(f"        ✗ ERROR: {e}")

        return False

    finally:

        try:
            os.remove(tmp_file)
        except FileNotFoundError:
            pass


# ============================================================
# 主程序
# ============================================================

def main():

    random.seed()

    print()
    print("=" * 70)
    print("IPTV SERVER CHECK")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # 读取 M3U
    # --------------------------------------------------------

    groups, entries = load_m3u(INPUT_FILE)

    print(f"发现 IPTV 服务器: {len(groups)}")
    print(f"发现 IPTV 频道  : {len(entries)}")
    print()

    valid_servers = set()

    # --------------------------------------------------------
    # 逐个服务器检测
    # --------------------------------------------------------

    for server, channels in groups.items():

        print("-" * 70)
        print(f"[SERVER] {server}")
        print(f"         Channels: {len(channels)}")

        test_channels = choose_test_channels(channels)

        valid = False

        # ----------------------------------------------------
        # 最多测试两个频道
        # ----------------------------------------------------

        for index, channel in enumerate(test_channels, start=1):

            if channel is None:
                continue

            print()
            print(f"        Test #{index}")
            print(f"        Channel: {channel['extinf']}")

            if test_stream(channel["url"]):

                valid = True
                break

            # 第一次失败
            if index == 1 and test_channels[1] is not None:

                print()
                print("        First test failed.")
                print("        Trying another channel...")

        # ----------------------------------------------------
        # 最终服务器判断
        # ----------------------------------------------------

        print()

        if valid:

            print(f"        ✓ SERVER VALID: {server}")

            valid_servers.add(server)

        else:

            print(f"        ✗ SERVER INVALID: {server}")

    # --------------------------------------------------------
    # 检测结果
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CHECK RESULT")
    print("=" * 70)

    print(f"Total servers : {len(groups)}")
    print(f"Valid servers : {len(valid_servers)}")
    print(f"Invalid       : {len(groups) - len(valid_servers)}")

    print()
    print("Valid servers:")

    for server in sorted(valid_servers):
        print(f"  ✓ {server}")

    # --------------------------------------------------------
    # 根据服务器结果过滤 M3U
    # --------------------------------------------------------

    valid_count = 0
    removed_count = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        for entry in entries:

            if entry["server"] in valid_servers:

                out.write(entry["extinf"] + "\n")
                out.write(entry["url"] + "\n")

                valid_count += 1

            else:

                removed_count += 1

    # --------------------------------------------------------
    # 替换原文件
    # --------------------------------------------------------

    os.replace(OUTPUT_FILE, INPUT_FILE)

    print()
    print("=" * 70)
    print("FILTER RESULT")
    print("=" * 70)

    print(f"Channels kept   : {valid_count}")
    print(f"Channels removed: {removed_count}")
    print()


if __name__ == "__main__":
    main()
