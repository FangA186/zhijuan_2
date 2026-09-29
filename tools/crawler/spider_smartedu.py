"""SmartEdu catalog crawler. Run from the repository root with python -m."""
import json
import os
import urllib.parse

from tools.crawler.smartedu_client import OUTPUT_DIR, fetch_json
from tools.crawler.smartedu_details import step3_and_4_fetch_details_and_trees

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
def main():
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

if __name__ == "__main__":
    main()
