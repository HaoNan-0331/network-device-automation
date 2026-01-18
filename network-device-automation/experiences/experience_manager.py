#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
经验管理器
用于管理网络设备自动化的经验教训
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class ExperienceManager:
    """经验管理器"""

    def __init__(self, experience_dir: str = None):
        """初始化经验管理器"""
        if experience_dir is None:
            experience_dir = Path(__file__).parent
        else:
            experience_dir = Path(experience_dir)

        self.experience_dir = experience_dir
        self.index_file = experience_dir / "index.json"
        self.load_index()

    def load_index(self):
        """加载经验索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_experiences": 0,
                "categories": {},
                "experiences": []
            }

    def save_index(self):
        """保存经验索引"""
        self.index["last_updated"] = datetime.now().isoformat()
        self.index["total_experiences"] = len(self.index["experiences"])

        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def add_experience(self, experience: Dict[str, Any]) -> str:
        """添加新经验"""
        # 生成ID
        existing_ids = [exp["id"] for exp in self.index["experiences"]]
        new_id = len(existing_ids) + 1
        experience["id"] = f"{new_id:03d}"
        experience["timestamp"] = datetime.now().isoformat()
        experience["verified"] = False

        # 保存到单独文件
        exp_file = self.experience_dir / f"{experience['id']}_{experience.get('category', 'general')}.json"
        with open(exp_file, 'w', encoding='utf-8') as f:
            json.dump(experience, f, indent=2, ensure_ascii=False)

        # 更新索引
        self.index["experiences"].append({
            "id": experience["id"],
            "category": experience.get("category", "general"),
            "title": experience.get("title", "Untitled"),
            "timestamp": experience["timestamp"],
            "tags": experience.get("tags", []),
            "file": str(exp_file.name)
        })

        # 更新分类统计
        category = experience.get("category", "general")
        if category not in self.index["categories"]:
            self.index["categories"][category] = 0
        self.index["categories"][category] += 1

        self.save_index()

        print(f"[OK] 经验已保存: {experience['id']} - {experience.get('title', 'Untitled')}")
        return experience["id"]

    def search(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """搜索经验"""
        query_lower = query.lower()
        results = []

        for exp_info in self.index["experiences"]:
            # 分类过滤
            if category and exp_info["category"] != category:
                continue

            # 加载完整经验
            exp_file = self.experience_dir / exp_info["file"]
            if not exp_file.exists():
                continue

            with open(exp_file, 'r', encoding='utf-8') as f:
                experience = json.load(f)

            # 搜索匹配
            text = json.dumps(experience).lower()
            if query_lower in text:
                results.append(experience)

        return results

    def get_relevant_experiences(self, device_type: str, operation: str) -> List[Dict[str, Any]]:
        """获取相关经验"""
        relevant = []

        for exp_info in self.index["experiences"]:
            exp_file = self.experience_dir / exp_info["file"]
            if not exp_file.exists():
                continue

            with open(exp_file, 'r', encoding='utf-8') as f:
                experience = json.load(f)

            # 检查设备类型
            if device_type and "device_type" in experience:
                if device_type not in experience["device_type"]:
                    continue

            # 检查操作类型
            if operation and "tags" in experience:
                if operation not in experience["tags"]:
                    continue

            relevant.append(experience)

        return relevant

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有经验"""
        all_exp = []
        for exp_info in self.index["experiences"]:
            exp_file = self.experience_dir / exp_info["file"]
            if exp_file.exists():
                with open(exp_file, 'r', encoding='utf-8') as f:
                    all_exp.append(json.load(f))
        return all_exp

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total": self.index["total_experiences"],
            "categories": self.index["categories"],
            "last_updated": self.index["last_updated"]
        }

    def export_markdown(self, output_file: str):
        """导出为Markdown文档"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 经验教训总结\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总经验数: {self.index['total_experiences']}\n\n")

            for category in self.index["categories"]:
                f.write(f"## {category.upper()}\n\n")

                for exp_info in self.index["experiences"]:
                    if exp_info["category"] != category:
                        continue

                    exp_file = self.experience_dir / exp_info["file"]
                    if not exp_file.exists():
                        continue

                    with open(exp_file, 'r', encoding='utf-8') as f2:
                        exp = json.load(f2)

                    f.write(f"### {exp['id']}: {exp.get('title', 'Untitled')}\n\n")
                    f.write(f"**问题**: {exp.get('problem', 'N/A')}\n\n")
                    f.write(f"**症状**: {', '.join(exp.get('symptoms', []))}\n\n")
                    f.write(f"**原因**: {exp.get('root_cause', 'N/A')}\n\n")
                    f.write(f"**解决方案**: {exp.get('solution', 'N/A')}\n\n")

                    if "code_example" in exp:
                        f.write(f"**代码示例**:\n```python\n{exp['code_example']}\n```\n\n")

                    if "prevention" in exp:
                        f.write(f"**预防**: {exp['prevention']}\n\n")

                    f.write("---\n\n")

        print(f"[OK] 已导出到: {output_file}")

# 便捷函数
def add_experience(problem: str, solution: str, category: str = "general",
                   symptoms: List[str] = None, device_type: List[str] = None):
    """快速添加经验"""
    em = ExperienceManager()
    experience = {
        "category": category,
        "title": problem[:50],
        "problem": problem,
        "solution": solution,
        "symptoms": symptoms or [],
        "device_type": device_type or [],
        "tags": []
    }
    return em.add_experience(experience)

if __name__ == "__main__":
    # 测试
    em = ExperienceManager()
    stats = em.get_statistics()
    print(f"经验统计: {stats}")
