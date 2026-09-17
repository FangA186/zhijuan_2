import csv
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# 基础配置
OUTPUT_DIR = "./smartedu_data"
MAX_WORKERS = 16  # 并发线程数（CDN速度极快，16线程约1~2分钟即可拉完3209本教材）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_json(url: str, retries: int = 3):
    """带重试机制的 JSON 请求工具函数"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                print(f"[错误] 请求失败 ({url}): {e}")
                return None
            time.sleep(1)


# ========================================================
# 阶段 1：获取维度分类树 (national_lesson_tag.json)
# ========================================================
def step1_fetch_tags():
    print("\n" + "=" * 50)
    print("【阶段 1】开始获取维度分类树...")
    save_dir = os.path.join(OUTPUT_DIR, "1_tags")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "national_lesson_tag.json")

    url = "https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/tags/national_lesson_tag.json"
    data = fetch_json(url)
    if data:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 阶段 1 完成：分类标签树已保存至 {save_path}")
    return data


# ========================================================
# 阶段 2：获取全量教材清单 (data_version.json & part_*.json)
# ========================================================
def step2_fetch_all_materials():
    print("\n" + "=" * 50)
    print("【阶段 2】开始获取全网教材清单与分包数据...")
    save_dir = os.path.join(OUTPUT_DIR, "2_materials_list")
    parts_dir = os.path.join(save_dir, "parts")
    os.makedirs(parts_dir, exist_ok=True)

    # 1. 获取版本索引
    version_url = "https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/national_lesson/teachingmaterials/version/data_version.json"
    v_data = fetch_json(version_url)
    with open(
        os.path.join(save_dir, "data_version.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(v_data, f, ensure_ascii=False, indent=2)

    # 2. 拉取所有分包并合并
    all_materials = []
    for part_url in v_data.get("urls", []):
        filename = part_url.split("/")[-1]
        part_save_path = os.path.join(parts_dir, filename)

        part_data = fetch_json(part_url)
        if part_data:
            with open(part_save_path, "w", encoding="utf-8") as f:
                json.dump(part_data, f, ensure_ascii=False, indent=2)
            all_materials.extend(part_data)
            print(f"  ✓ 已拉取分包: {filename} ({len(part_data)} 本教材)")

    # 3. 保存全量汇总
    summary_path = os.path.join(save_dir, "all_materials.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_materials, f, ensure_ascii=False, indent=2)

    print(
        f"✓ 阶段 2 完成：全网教材汇总共 {len(all_materials)} 本，保存至 {summary_path}"
    )
    return all_materials


# ========================================================
# 阶段 3 & 4：并发下载指定或全部教材的 Details 和 Trees
# ========================================================
def download_single_material(mat):
    """单个教材的任务单元：负责下载 details 和 trees"""
    mat_id = mat["id"]
    title = mat.get("title", "未知教材")

    details_path = os.path.join(OUTPUT_DIR, "3_details", f"{mat_id}.json")
    trees_path = os.path.join(OUTPUT_DIR, "4_trees", f"{mat_id}.json")

    # 1. 抓取 details (若已存在则跳过断点续传)
    details_data = None
    if not os.path.exists(details_path):
        d_url = f"https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/national_lesson/teachingmaterials/details/{mat_id}.json"
        details_data = fetch_json(d_url)
        if details_data:
            with open(details_path, "w", encoding="utf-8") as f:
                json.dump(details_data, f, ensure_ascii=False, indent=2)
    else:
        # 已存在直接读取
        try:
            with open(details_path, "r", encoding="utf-8") as f:
                details_data = json.load(f)
        except Exception:
            pass

    # 2. 抓取 trees
    trees_count = 0
    if not os.path.exists(trees_path):
        t_url = f"https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/national_lesson/trees/{mat_id}.json"
        trees_data = fetch_json(t_url)
        if trees_data is not None:
            with open(trees_path, "w", encoding="utf-8") as f:
                json.dump(trees_data, f, ensure_ascii=False, indent=2)
            trees_count = len(trees_data) if isinstance(trees_data, list) else 0
    else:
        try:
            with open(trees_path, "r", encoding="utf-8") as f:
                trees_data = json.load(f)
                trees_count = (
                    len(trees_data) if isinstance(trees_data, list) else 0
                )
        except Exception:
            pass

    # 提取标签维度
    dim_map = {
        "zxxxd": "学段",
        "zxxxk": "学科",
        "zxxbb": "版本",
        "zxxcc": "册次",
        "zxxnj": "年级",
    }
    tags_info = {}
    for t in mat.get("tag_list", []):
        dim = t.get("tag_dimension_id")
        if dim in dim_map:
            tags_info[dim_map[dim]] = t.get("tag_name")

    return {
        "id": mat_id,
        "title": title,
        "学段": tags_info.get("学段", ""),
        "学科": tags_info.get("学科", ""),
        "版本": tags_info.get("版本", ""),
        "年级": tags_info.get("年级", ""),
        "册次": tags_info.get("册次", ""),
        "章节数": trees_count,
    }


def step3_and_4_fetch_details_and_trees(materials: list):
    print("\n" + "=" * 50)
    print(
        f"【阶段 3 & 4】开始多线程爬取 {len(materials)} 本教材的 Details 和 Trees..."
    )
    os.makedirs(os.path.join(OUTPUT_DIR, "3_details"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "4_trees"), exist_ok=True)

    catalog_rows = []
    total = len(materials)
    completed = 0

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_single_material, m): m for m in materials
        }
        for future in as_completed(futures):
            res = future.result()
            if res:
                catalog_rows.append(res)
            completed += 1
            if completed % 100 == 0 or completed == total:
                elapsed = time.time() - t0
                speed = completed / elapsed if elapsed > 0 else 0
                print(
                    f"  进度: [{completed}/{total}] ({completed/total*100:.1f}%) - 速度: {speed:.1f} 本/秒"
                )

    # 导出汇总目录 catalog.csv
    csv_path = os.path.join(OUTPUT_DIR, "catalog.csv")
    if catalog_rows:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(catalog_rows[0].keys()))
            writer.writeheader()
            writer.writerows(catalog_rows)
        print(f"\n✓ 阶段 3 & 4 完成：已生成总索引清单 {csv_path}")


# ========================================================
# 辅助功能：根据页面 URL 的 defaultTag 只爬单本教材
# ========================================================
def filter_by_page_url(page_url: str, materials: list):
    parsed = urllib.parse.urlparse(page_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    default_tag = query_params.get("defaultTag", [""])[0]
    if not default_tag:
        return None
    tag_ids = set(default_tag.split("/"))
    for mat in materials:
        mat_tags = {t["tag_id"] for t in mat.get("tag_list", [])}
        if tag_ids.issubset(mat_tags):
            return [mat]
    return []


# ========================================================
# 主程序入口
# ========================================================
if __name__ == "__main__":
    # 1. 爬取阶段 1
    step1_fetch_tags()

    # 2. 爬取阶段 2
    all_materials = step2_fetch_all_materials()

    # ----------------------------------------------------
    # 选择模式：
    # 模式 A (推荐)：爬取全网所有 3209 本教材的 1、2、3、4 阶段
    target_materials = all_materials

    # 模式 B (如果你只测试你给的那个网址)：
    # test_url = "https://basic.smartedu.cn/syncClassroom?defaultTag=e7bbcefe-0590-11ed-9c79-92fc3b3249d5%2Fe7bbcfee-0590-11ed-9c79-92fc3b3249d5%2Fff8080814371757b01437c363a187b0a%2F5036342972"
    # target_materials = filter_by_page_url(test_url, all_materials)
    # ----------------------------------------------------

    # 3. 爬取阶段 3 和 4
    step3_and_4_fetch_details_and_trees(target_materials)

    print("\n" + "=" * 50)
    print(f"🎉 全部 1、2、3、4 阶段数据爬取完成！请查看目录：{OUTPUT_DIR}")