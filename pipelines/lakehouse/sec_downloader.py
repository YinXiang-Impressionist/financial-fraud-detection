# -*- coding: utf-8 -*-
"""
SEC DERA 财务报表数据集 (2016Q1 ~ 2026Q2 跨10年完整历史数据集) 批量自动化下载工具
"""

import os
import sys
import time
import requests
from tqdm import tqdm

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# SEC 合规 User-Agent
SEC_HEADERS = {
    "User-Agent": "SecDerADataScraper/2.0 (Academic Research; contact: research_sec@quant.org)",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}


class SecDeraDownloader:
    def __init__(self, download_dir="./sec_zips", start_year=2016, end_year=2026):
        self.download_dir = os.path.abspath(download_dir)
        self.start_year = start_year
        self.end_year = end_year
        os.makedirs(self.download_dir, exist_ok=True)
        self.base_url = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"

    def get_quarter_list(self):
        """生成 2016Q1 到 2026Q2 的季度清单 (跨10年完整历史区间)"""
        quarters = []
        for y in range(self.start_year, self.end_year + 1):
            max_q = 2 if y == 2026 else 4
            for q in range(1, max_q + 1):
                quarters.append(f"{y}q{q}")
        return quarters

    def download_file(self, quarter_tag, max_retries=5):
        """流式下载单个季度的 zip 压缩包"""
        file_name = f"{quarter_tag}.zip"
        target_path = os.path.join(self.download_dir, file_name)
        url = f"{self.base_url}/{file_name}"

        # 断点续传检查
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1024 * 1024:
            try:
                import zipfile
                with zipfile.ZipFile(target_path, 'r') as zf:
                    if 'sub.txt' in zf.namelist() and 'num.txt' in zf.namelist():
                        return True, "已完整下载(跳过)"
            except Exception:
                pass

        for attempt in range(max_retries):
            try:
                time.sleep(0.3)
                resp = requests.get(url, headers=SEC_HEADERS, stream=True, timeout=30)
                
                if resp.status_code == 200:
                    total_size = int(resp.headers.get('content-length', 0))
                    
                    with open(target_path, 'wb') as f:
                        with tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name, leave=False) as pbar:
                            for chunk in resp.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                    
                    # 验证 zip 完整性
                    import zipfile
                    with zipfile.ZipFile(target_path, 'r') as zf:
                        names = zf.namelist()
                        if 'sub.txt' not in names or 'num.txt' not in names:
                            raise ValueError("Zip 文件缺失关键报表文件")
                            
                    return True, "下载成功"
                    
                elif resp.status_code == 404:
                    return False, "404 Not Found"
                elif resp.status_code == 403:
                    time.sleep(3.0 * (attempt + 1))
                else:
                    time.sleep(2.0 * (attempt + 1))

            except Exception as e:
                if attempt == max_retries - 1:
                    return False, f"异常失败: {str(e)}"
                time.sleep(2.0 * (attempt + 1))

        return False, "重试耗尽"

    def run(self):
        quarters = self.get_quarter_list()
        print("\n" + "=" * 65)
        print(f"[*] 启动 SEC DERA 财务报表数据批量下载任务")
        print(f"[*] 目标范围: {quarters[0]} ~ {quarters[-1]} (共 {len(quarters)} 个季度)")
        print(f"[*] 保存路径: {self.download_dir}")
        print("=" * 65 + "\n")

        success_list = []
        failed_list = []

        for q in tqdm(quarters, desc="总体季度进度", unit="季度"):
            ok, msg = self.download_file(q)
            if ok:
                success_list.append(q)
            else:
                failed_list.append((q, msg))

        print("\n" + "=" * 65)
        print(f"[+] 下载任务汇总: 成功 {len(success_list)} 个 / 失败 {len(failed_list)} 个")
        print("=" * 65)


if __name__ == "__main__":
    downloader = SecDeraDownloader()
    downloader.run()
