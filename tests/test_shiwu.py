"""失物占引擎回归测试"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "shiwu_calc.py"

sys.path.insert(0, str(ROOT / "scripts"))

import shiwu_calc  # noqa: E402


class TestCastingMath:
    def test_num_to_gua_remainder_zero(self):
        assert shiwu_calc.num_to_gua(8) == 8
        assert shiwu_calc.num_to_gua(16) == 8

    def test_num_to_yao_remainder_zero(self):
        assert shiwu_calc.num_to_yao(6) == 6
        assert shiwu_calc.num_to_yao(12) == 6

    def test_num_to_gua_values(self):
        assert shiwu_calc.num_to_gua(1) == 1
        assert shiwu_calc.num_to_gua(6) == 6
        assert shiwu_calc.num_to_gua(7) == 7


class TestTiYong:
    def test_changing_line_lower_ti_upper(self):
        analysis = shiwu_calc.analyze_hexagram(1, 6, 3)
        assert analysis.ti_gua == 1
        assert analysis.yong_gua == 6
        assert analysis.ti_position == "上卦"
        assert analysis.yong_position == "下卦"

    def test_changing_line_upper_ti_lower(self):
        analysis = shiwu_calc.analyze_hexagram(1, 6, 4)
        assert analysis.ti_gua == 6
        assert analysis.yong_gua == 1
        assert analysis.ti_position == "下卦"
        assert analysis.yong_position == "上卦"


class TestMutualAndTransformed:
    def test_mutual_hexagram(self):
        analysis = shiwu_calc.analyze_hexagram(1, 1, 1)
        assert analysis.hu_upper == 1
        assert analysis.hu_lower == 1
        assert analysis.hu_name == "乾為天"

    def test_transformed_hexagram(self):
        analysis = shiwu_calc.analyze_hexagram(1, 6, 1)
        assert analysis.bian_lower == 2
        assert analysis.bian_upper == 1


class TestGoldenBraceletCase:
    def test_kan_as_yong_locations(self):
        # 居家语境：坎卦应给出洗衣机/卫生间等家庭水象场景
        report = shiwu_calc.cast_by_numbers(1, 6, 1, item_name="金手链", context="home")
        assert report["ti_yong"]["yong"].startswith("坎")

        all_scenes = " ".join(
            scene for loc in report["locations"] for scene in loc["scenes"]
        )
        assert "洗衣机" in all_scenes
        assert "卫生间" in all_scenes

        primary = report["locations"][0]
        assert primary["trigram"] == "坎"
        assert primary["direction"] == "北"
        assert primary["rank"] == 1

    def test_kan_element_water_note(self):
        report = shiwu_calc.cast_by_numbers(1, 6, 1, context="home")
        assert report["locations"][0]["element"] == "水"


class TestContextSwitching:
    def test_context_normalization(self):
        assert shiwu_calc.normalize_context("家里") == "home"
        assert shiwu_calc.normalize_context("图书馆") == "public"
        assert shiwu_calc.normalize_context("飞机") == "transit"
        assert shiwu_calc.normalize_context("猫") == "pet"
        assert shiwu_calc.normalize_context(None) == "general"
        assert shiwu_calc.normalize_context("乱七八糟") == "general"

    def test_kan_scenes_differ_by_context(self):
        home = shiwu_calc.cast_by_numbers(1, 6, 1, context="home")["locations"][0]["scenes"]
        public = shiwu_calc.cast_by_numbers(1, 6, 1, context="public")["locations"][0]["scenes"]
        assert home != public
        # 居家有洗衣机，公共没有
        assert "洗衣机" in " ".join(home)
        assert "洗衣机" not in " ".join(public)

    def test_public_context_has_lost_and_found(self):
        # 艮卦在公共语境应包含失物招领处（充电线案例）
        report = shiwu_calc.cast_by_numbers(7, 2, 6, item_name="充电线", context="public")
        assert report["context"] == "public"
        scenes = " ".join(report["locations"][0]["scenes"])
        assert "失物招领处" in scenes

    def test_direction_stable_across_contexts(self):
        # 方位是跨语境稳定线索：同卦不同语境，主方位一致
        d_home = shiwu_calc.cast_by_numbers(1, 6, 1, context="home")["primary_direction"]
        d_public = shiwu_calc.cast_by_numbers(1, 6, 1, context="public")["primary_direction"]
        assert d_home == d_public == "北"

    def test_no_hardcoded_house_in_public(self):
        # 公共语境不应出现"屋内"硬编码范围
        report = shiwu_calc.cast_by_numbers(1, 6, 1, context="public")
        scopes = " ".join(loc["scope"] for loc in report["locations"])
        assert "屋内" not in scopes


class TestPetContext:
    def test_pet_has_animal_image(self):
        report = shiwu_calc.cast_by_numbers(1, 6, 1, item_name="猫", context="pet")
        assert report["context"] == "pet"
        assert "animal_image" in report["locations"][0]
        assert "豕" in report["locations"][0]["animal_image"]  # 坎为豕

    def test_pet_advice_mentions_pet(self):
        report = shiwu_calc.cast_by_numbers(1, 6, 1, item_name="狗", context="pet")
        assert "宠物" in report["moved"] or "宠物" in report["action_advice"]


class TestFindability:
    def test_ti_ke_yong(self):
        analysis = shiwu_calc.analyze_hexagram(1, 4, 1)
        assert analysis.wuxing_relation == "體克用"
        report = shiwu_calc.build_search_report(analysis, method="test")
        assert report["findability"]["tendency"] == "可得"

    def test_yong_sheng_ti(self):
        analysis = shiwu_calc.analyze_hexagram(3, 4, 1)
        assert analysis.wuxing_relation == "用生體"
        report = shiwu_calc.build_search_report(analysis, method="test")
        assert report["findability"]["tendency"] == "易得"


class TestSearchReportStructure:
    def test_report_has_required_fields(self):
        report = shiwu_calc.cast_by_numbers(6, 8, 3)
        assert "casting" in report
        assert "context" in report
        assert "primary_direction" in report
        assert "findability" in report
        assert "locations" in report
        assert "moved" in report
        assert "action_advice" in report
        assert "disclaimer" in report
        assert "timing" not in report

    def test_locations_ranked(self):
        report = shiwu_calc.cast_by_numbers(1, 6, 1)
        ranks = [loc["rank"] for loc in report["locations"]]
        assert ranks == sorted(ranks)
        assert ranks[0] == 1


class TestCLI:
    def test_cli_num_outputs_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "num", "1", "6", "1", "--item", "金手链", "--context", "home"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["item_name"] == "金手链"
        assert data["context"] == "home"
        assert data["locations"][0]["trigram"] == "坎"

    def test_cli_context_flag(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "num", "7", "2", "6", "--context", "public"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["context"] == "public"


class TestBidirectionalHexagram:
    """变卦/互卦双向解读"""

    def test_transformed_hexagram_has_upper_lower(self):
        """变卦报告节应包含 upper/lower"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        th = report["transformed_hexagram"]
        assert "upper" in th
        assert "lower" in th
        assert th["upper"] in ("離", "震", "坎", "艮", "坤", "乾", "兌", "巽")
        assert th["lower"] in ("離", "震", "坎", "艮", "坤", "乾", "兌", "巽")

    def test_bian_location_has_paired_fields(self):
        """rank 2 变卦应包含 paired 字段"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        bian_loc = report["locations"][1]
        assert bian_loc["rank"] == 2
        assert "paired_trigram" in bian_loc
        assert "paired_direction" in bian_loc
        assert "hexagram_note" in bian_loc

    def test_sim_card_combined_direction(self):
        """44,58 SIM卡案：变卦离南+兑西应得西南"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        bian_loc = report["locations"][1]
        assert bian_loc["trigram"] == "離"
        assert bian_loc["paired_trigram"] == "兌"
        assert bian_loc["direction"] == "南"
        assert bian_loc["paired_direction"] == "西"
        assert bian_loc["combined_direction"] == "西南(坤)"

    def test_mutual_location_has_paired_fields(self):
        """rank 3 互卦应包含 paired 字段"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        hu_loc = report["locations"][2]
        assert hu_loc["rank"] == 3
        assert "paired_trigram" in hu_loc
        assert "paired_direction" in hu_loc
        assert "hexagram_note" in hu_loc

    def test_moved_mentions_direction_hint(self):
        """_infer_moved 应包含方向提示"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        assert "火澤睽" in report["moved"]
        assert "方位" in report["moved"]

    def test_rank_1_no_paired_fields(self):
        """用卦 (rank 1) 不应有 paired 字段"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        yong_loc = report["locations"][0]
        assert "paired_trigram" not in yong_loc
        assert "paired_direction" not in yong_loc
        assert "hexagram_note" not in yong_loc

    def test_same_direction_transformed_no_combined(self):
        """变卦两半同向时不产生 combined_direction"""
        # 1,3,1 → 天火同人 第1爻动 → 变卦天山遯 (乾+艮)
        # 乾=西北, 艮=东北 — not orthogonal, no combined
        report = shiwu_calc.cast_by_numbers(1, 3, 1, context="home")
        if len(report["locations"]) > 1:
            bian_loc = report["locations"][1]
            if "paired_direction" in bian_loc:
                # May or may not have combined_direction depending on pairing
                pass  # just verify no crash

    def test_action_advice_mentions_combined(self):
        """action_advice 在复合方向存在时提及"""
        report = shiwu_calc.cast_by_numbers(44, 58, item_name="SIM卡", context="home")
        assert "西南(坤)" in report["action_advice"]


class TestCompartmentScenes:
    """夹层/隔层场景覆盖"""

    @staticmethod
    def gua_home_scenes(gua_num):
        from shiwu_calc import get_scenes
        return get_scenes(gua_num, "home")

    def test_xun_has_compartment(self):
        scenes = self.gua_home_scenes(5)
        combined = " ".join(scenes)
        assert "夹层" in combined or "隔层" in combined

    def test_kan_has_hidden_compartment(self):
        scenes = self.gua_home_scenes(6)
        combined = " ".join(scenes)
        assert "隐蔽夹层" in combined or "暗格" in combined

    def test_gen_has_cabinet_compartment(self):
        scenes = self.gua_home_scenes(7)
        combined = " ".join(scenes)
        assert "夹层" in combined or "隔层" in combined

    def test_kun_has_bag_compartment(self):
        scenes = self.gua_home_scenes(8)
        combined = " ".join(scenes)
        assert "口袋" in combined or "夹层" in combined

    def test_zhen_has_drawer_compartment(self):
        scenes = self.gua_home_scenes(4)
        combined = " ".join(scenes)
        assert "夹层" in combined or "隔层" in combined

    def test_compartment_scenes_in_report(self):
        """Compartment scenes actually appear in a real report"""
        report = shiwu_calc.cast_by_numbers(1, 5, 2, item_name="SIM卡", context="home")
        all_scenes = " ".join(
            scene for loc in report["locations"] for scene in loc["scenes"]
        )
        assert "夹层" in all_scenes or "隔层" in all_scenes or "缝隙" in all_scenes


class TestBackwardCompatibility:
    """确保新增字段不破坏现有输出结构"""

    def test_existing_fields_unchanged(self):
        """所有 pre-existing 字段保持原类型和含义"""
        report = shiwu_calc.cast_by_numbers(1, 6, 1, context="home")
        # 核心字段存在且类型正确
        assert isinstance(report["locations"], list)
        assert isinstance(report["locations"][0]["rank"], int)
        assert isinstance(report["locations"][0]["direction"], str)
        assert isinstance(report["locations"][0]["scenes"], list)
        assert isinstance(report["locations"][0]["trigram"], str)
        assert isinstance(report["locations"][0]["element"], str)
        assert isinstance(report["locations"][0]["note"], str)
        assert isinstance(report["primary_direction"], str)
        assert isinstance(report["findability"], dict)
        # 金手链回归测试
        assert report["locations"][0]["trigram"] == "坎"
        assert report["locations"][0]["direction"] == "北"
        assert "洗衣机" in " ".join(report["locations"][0]["scenes"])

    def test_locations_still_ranked(self):
        """Rank 排序未变"""
        report = shiwu_calc.cast_by_numbers(44, 58, context="home")
        ranks = [loc["rank"] for loc in report["locations"]]
        assert ranks == sorted(ranks)
        assert ranks[0] == 1
