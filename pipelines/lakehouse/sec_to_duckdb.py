# -*- coding: utf-8 -*-
"""
SEC 财务报表数据转换与 DuckDB 湖仓构建工具
将 2016-2026 跨 10 年完整的 42 个季度 zip 包转换为 ZSTD 压缩 Parquet 分区表，并挂载为 DuckDB 统一视图。
"""

import os
import sys
import glob
import time
import zipfile
import duckdb
import pandas as pd
from tqdm import tqdm

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 项目根目录绝对路径锚定
_LAKEHOUSE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_LAKEHOUSE_DIR))
DEFAULT_ZIPS_DIR = os.path.join(PROJECT_ROOT, "sec_zips")
DEFAULT_PARQUET_DIR = os.path.join(PROJECT_ROOT, "sec_parquet")
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "sec_financials.duckdb")


def is_zh() -> bool:
    return os.environ.get("FORENSIC_LANG", "en").lower().startswith("zh")


class SecToDuckDBPipeline:
    def __init__(self, zips_dir: str = "", parquet_dir: str = "", db_path: str = ""):
        self.zips_dir = os.path.abspath(zips_dir) if zips_dir else DEFAULT_ZIPS_DIR
        self.parquet_dir = os.path.abspath(parquet_dir) if parquet_dir else DEFAULT_PARQUET_DIR
        self.db_path = os.path.abspath(db_path) if db_path else DEFAULT_DB_PATH

        for table in ["sub", "num", "tag", "pre"]:
            os.makedirs(os.path.join(self.parquet_dir, table), exist_ok=True)

    def extract_and_convert_zip(self, zip_path: str):
        """将单季度 zip 解压转换为 Parquet 分区文件"""
        q_name = os.path.splitext(os.path.basename(zip_path))[0]
        
        # 检查是否已完成
        num_parquet = os.path.join(self.parquet_dir, "num", f"{q_name}.parquet")
        sub_parquet = os.path.join(self.parquet_dir, "sub", f"{q_name}.parquet")
        if os.path.exists(num_parquet) and os.path.exists(sub_parquet):
            return True, "已转换(跳过)"

        temp_extract = os.path.join(self.parquet_dir, f"_temp_{q_name}")
        os.makedirs(temp_extract, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_extract)

            con = duckdb.connect()

            # 1. sub.txt
            sub_txt = os.path.join(temp_extract, "sub.txt")
            if os.path.exists(sub_txt):
                con.execute(f"""
                    COPY (
                        SELECT *, '{q_name}' as quarter 
                        FROM read_csv('{sub_txt.replace(chr(92), '/')}', 
                                      delim='\t', header=true, all_varchar=false, ignore_errors=true)
                    ) TO '{sub_parquet.replace(chr(92), '/')}' (FORMAT PARQUET, COMPRESSION 'zstd');
                """)

            # 2. num.txt
            num_txt = os.path.join(temp_extract, "num.txt")
            if os.path.exists(num_txt):
                con.execute(f"""
                    COPY (
                        SELECT *, '{q_name}' as quarter 
                        FROM read_csv('{num_txt.replace(chr(92), '/')}', 
                                      delim='\t', header=true, all_varchar=false, ignore_errors=true)
                    ) TO '{num_parquet.replace(chr(92), '/')}' (FORMAT PARQUET, COMPRESSION 'zstd');
                """)

            # 3. tag.txt
            tag_txt = os.path.join(temp_extract, "tag.txt")
            tag_parquet = os.path.join(self.parquet_dir, "tag", f"{q_name}.parquet")
            if os.path.exists(tag_txt):
                con.execute(f"""
                    COPY (
                        SELECT *, '{q_name}' as quarter 
                        FROM read_csv('{tag_txt.replace(chr(92), '/')}', 
                                      delim='\t', header=true, all_varchar=false, ignore_errors=true)
                    ) TO '{tag_parquet.replace(chr(92), '/')}' (FORMAT PARQUET, COMPRESSION 'zstd');
                """)

            # 4. pre.txt
            pre_txt = os.path.join(temp_extract, "pre.txt")
            pre_parquet = os.path.join(self.parquet_dir, "pre", f"{q_name}.parquet")
            if os.path.exists(pre_txt):
                con.execute(f"""
                    COPY (
                        SELECT *, '{q_name}' as quarter 
                        FROM read_csv('{pre_txt.replace(chr(92), '/')}', 
                                      delim='\t', header=true, all_varchar=false, ignore_errors=true)
                    ) TO '{pre_parquet.replace(chr(92), '/')}' (FORMAT PARQUET, COMPRESSION 'zstd');
                """)

            con.close()
            return True, "转换成功"

        except Exception as e:
            return False, f"错误: {str(e)}"
        finally:
            import shutil
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract, ignore_errors=True)

    def create_unified_database(self):
        """在 DuckDB 中建立跨季度的全量视图与索引"""
        print(f"\n[*] 正在构建/挂载统一 DuckDB 数据库 ({self.db_path})...")
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

        con = duckdb.connect(self.db_path)
        
        sub_glob = os.path.join(self.parquet_dir, "sub", "*.parquet").replace("\\", "/")
        num_glob = os.path.join(self.parquet_dir, "num", "*.parquet").replace("\\", "/")
        tag_glob = os.path.join(self.parquet_dir, "tag", "*.parquet").replace("\\", "/")
        pre_glob = os.path.join(self.parquet_dir, "pre", "*.parquet").replace("\\", "/")

        con.execute(f"CREATE OR REPLACE VIEW sub AS SELECT * FROM '{sub_glob}';")
        con.execute(f"CREATE OR REPLACE VIEW num AS SELECT * FROM '{num_glob}';")
        con.execute(f"CREATE OR REPLACE VIEW tag AS SELECT * FROM '{tag_glob}';")
        con.execute(f"CREATE OR REPLACE VIEW pre AS SELECT * FROM '{pre_glob}';")

        # 统计数据体量
        sub_count = con.execute("SELECT count(*) FROM sub").fetchone()[0]
        num_count = con.execute("SELECT count(*) FROM num").fetchone()[0]
        cik_count = con.execute("SELECT count(distinct cik) FROM sub").fetchone()[0]
        
        con.close()

        zh = is_zh()
        print("\n" + "=" * 65)
        if zh:
            print("🎉 【DuckDB 湖仓构建完成！】")
            print("=" * 65)
            print(f"● 申报企业总数 (CIK) : {cik_count:,} 家公司")
            print(f"● 申报财报总数 (sub) : {sub_count:,} 份报表")
            print(f"● 财务数值事实 (num) : {num_count:,} 行数据 (全部挂载为高性能视图)")
            print(f"● 数据库存储文件     : {self.db_path}")
        else:
            print("🎉 [DuckDB Financial Lakehouse Built Successfully!]")
            print("=" * 65)
            print(f"● Unique Entities (CIK) : {cik_count:,} public companies")
            print(f"● Total Filings (sub)   : {sub_count:,} quarterly/annual reports")
            print(f"● Numeric Facts (num)   : {num_count:,} fact rows (mounted as high-speed views)")
            print(f"● Database File Path    : {self.db_path}")
        print("=" * 65)

    def run(self):
        zh = is_zh()
        zip_files = sorted(glob.glob(os.path.join(self.zips_dir, "*.zip")))
        if not zip_files:
            msg = f"[-] 在 {self.zips_dir} 未找到任何 zip 文件！请先运行 sec_downloader.py。" if zh else f"[-] No zip files found in {self.zips_dir}! Run sec_downloader.py first."
            print(msg)
            return

        print("\n" + "=" * 65)
        banner = f"[*] 开始转换 {len(zip_files)} 个季度的 SEC 数据为 Parquet 格式" if zh else f"[*] Converting {len(zip_files)} quarters of SEC datasets to Parquet format"
        print(banner)
        print("=" * 65)

        etl_desc = "ETL 转换进度" if zh else "ETL Conversion"
        etl_unit = "季度" if zh else "quarter"
        for zf in tqdm(zip_files, desc=etl_desc, unit=etl_unit):
            self.extract_and_convert_zip(zf)

        self.create_unified_database()


if __name__ == "__main__":
    pipeline = SecToDuckDBPipeline()
    pipeline.run()
