#!/usr/bin/env python3
"""
失物占起卦计算工具 (Lost Item Divination Calculator)

梅花易数失物占专用：确定性起卦、体用分析、后天方位定位、能否找回判断。
输出结构化 SearchReport JSON，供 AI Skill 渲染搜寻报告。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from lunardate import LunarDate
except ImportError:
    LunarDate = None  # type: ignore

# ---------------------------------------------------------------------------
# 八卦基础数据（先天数 + 后天方位 + 失物类象）
# ---------------------------------------------------------------------------

# 八卦失物类象（依语境取象，源自《说卦传》与万物类象）
# 方位为后天八卦方位，是跨语境最稳定的线索；场景随语境切换。
# 动物类象（说卦传）：乾马 坤牛 震龙 巽鸡 坎豕 离雉 艮狗 兑羊
BAGUA: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "乾",
        "symbol": "☰",
        "binary": "111",
        "element": "金",
        "direction": "西北",
        "distance_hint": "高处、远端",
        "object_traits": ["圆形", "金属色", "坚硬"],
        "animal": "马",
        "scenes_by_context": {
            "home": ["客厅高处", "书架顶层", "金属柜上", "贵重物品旁", "衣帽间"],
            "public": ["开阔广场", "大楼/银行/政府机构", "体育馆", "高处平台", "西北方建筑"],
            "transit": ["车头/前部", "行李架高处", "驾驶位附近", "金属部件处"],
            "pet": ["往西北方向", "开阔高地", "大路/主干道", "活动范围外缘"],
            "general": ["西北方位", "高处", "开阔或贵重物附近", "金属/圆形物旁"],
        },
    },
    2: {
        "name": "兌",
        "symbol": "☱",
        "binary": "011",
        "element": "金",
        "direction": "西",
        "distance_hint": "中距",
        "object_traits": ["缺口之物旁", "金属小器具"],
        "animal": "羊",
        "scenes_by_context": {
            "home": ["厨房", "餐桌", "杯碗碟旁", "破损物附近", "娱乐区"],
            "public": ["餐厅/咖啡馆", "娱乐场所", "水边洼地", "西方", "施工/破损处"],
            "transit": ["餐车/茶水处", "车门/出入口", "破损座椅处"],
            "pet": ["往西方向", "水边", "有食物处", "可能在叫(留意声音)"],
            "general": ["西方位", "近水或缺口处", "饮食/娱乐场所", "金属小器具旁"],
        },
    },
    3: {
        "name": "離",
        "symbol": "☲",
        "binary": "101",
        "element": "火",
        "direction": "南",
        "distance_hint": "中距",
        "object_traits": ["红色", "文书", "发光物旁"],
        "animal": "雉(禽鸟)",
        "scenes_by_context": {
            "home": ["窗边", "台灯旁", "灶台附近", "书本文件中", "电器旁"],
            "public": ["图书馆/书店/学校", "明亮处", "灯光/电器处", "南方", "文化场所"],
            "transit": ["显示屏/仪表附近", "灯光处", "窗边明亮处"],
            "pet": ["往南方向", "明亮温暖处", "人群聚集处", "向阳处"],
            "general": ["南方位", "明亮/发光处", "文书或电器旁", "温暖处"],
        },
    },
    4: {
        "name": "震",
        "symbol": "☳",
        "binary": "001",
        "element": "木",
        "direction": "东",
        "distance_hint": "近中",
        "object_traits": ["木器旁", "条状物"],
        "animal": "龙(蛇虫)",
        "scenes_by_context": {
            "home": ["木门边", "鞋柜", "常开关的抽屉", "抽屉夹层/隔层", "有声响处", "阳台"],
            "public": ["大路/马路", "车站", "树林/林荫道", "东方", "喧闹/运动场所"],
            "transit": ["车厢连接处", "发动机/引擎附近", "行进前方"],
            "pet": ["往东方向(动物易动)", "大路上", "喧闹或树林处", "快速移动中"],
            "general": ["东方位", "大路/动处", "树木旁", "有声响处"],
        },
    },
    5: {
        "name": "巽",
        "symbol": "☴",
        "binary": "110",
        "element": "木",
        "direction": "东南",
        "distance_hint": "近",
        "object_traits": ["柔软织物", "绳索", "缝隙"],
        "animal": "鸡",
        "scenes_by_context": {
            "home": ["夹层/隔层", "绳带衣物间", "床缝/沙发缝", "通风口", "草木盆栽旁", "长条物下"],
            "public": ["花园/草木处", "通风口", "东南方", "邮局/快递点", "林间小道"],
            "transit": ["通风/空调口", "座椅缝隙", "行李带/绑绳处"],
            "pet": ["往东南方向", "草丛/林间", "钻入缝隙或通道", "顺路远去"],
            "general": ["东南方位", "缝隙/草木间", "通风处", "绳带/长条物旁"],
        },
    },
    6: {
        "name": "坎",
        "symbol": "☵",
        "binary": "010",
        "element": "水",
        "direction": "北",
        "distance_hint": "近水",
        "object_traits": ["潮湿", "弯曲", "近水"],
        "animal": "豕(猪)",
        "scenes_by_context": {
            "home": ["卫生间", "厨房水槽", "洗衣机", "冰箱内", "隐蔽夹层/暗格", "水管旁"],
            "public": ["河流/池塘/水沟", "地下/低洼处", "卫生间", "北方", "隐蔽/停车场地下"],
            "transit": ["卫生间", "饮水/水箱处", "底部低处", "隐蔽夹层"],
            "pet": ["往北方向", "水边", "受惊躲藏的隐蔽处", "沟渠/桥下"],
            "general": ["北方位", "近水/低洼处", "隐蔽暗处", "暗格/夹层", "潮湿处"],
        },
    },
    7: {
        "name": "艮",
        "symbol": "☶",
        "binary": "100",
        "element": "土",
        "direction": "东北",
        "distance_hint": "近",
        "object_traits": ["石块旁", "静止角落"],
        "animal": "狗",
        "scenes_by_context": {
            "home": ["墙角", "门后", "台阶下", "储藏柜内", "柜子夹层/隔层", "床底/桌下"],
            "public": ["失物招领处", "建筑/门口", "山丘土坡", "东北方", "台阶/静止角落"],
            "transit": ["行李舱", "座位下", "角落", "出入口/门边"],
            "pet": ["往东北方向", "高地/土坡", "躲在角落不动", "建筑物附近"],
            "general": ["东北方位", "角落/静止处", "门径/台阶旁", "柜内/遮挡处"],
        },
    },
    8: {
        "name": "坤",
        "symbol": "☷",
        "binary": "000",
        "element": "土",
        "direction": "西南",
        "distance_hint": "低处",
        "object_traits": ["柔软", "方形", "土色"],
        "animal": "牛",
        "scenes_by_context": {
            "home": ["包内夹层/口袋", "地上", "床下", "布料旧物里", "储物间", "箱包内"],
            "public": ["平地/广场", "人群密集处", "旧楼/仓库", "西南方", "低处"],
            "transit": ["行李箱/货舱", "座椅下", "地板", "布袋/储物处"],
            "pet": ["往西南方向", "平地/田野", "人多处", "低洼隐蔽处"],
            "general": ["西南方位", "低处/地面", "布料/旧物中", "包内/口袋", "储物/包内"],
        },
    },
}

BINARY_TO_GUA = {info["binary"]: num for num, info in BAGUA.items()}

# 语境：失物所在环境决定取象方式
CONTEXTS = ("home", "public", "transit", "pet", "general")
DEFAULT_CONTEXT = "general"

CONTEXT_LABELS = {
    "home": "居家",
    "public": "公共场所/户外",
    "transit": "交通工具",
    "pet": "走失生物",
    "general": "通用",
}

# 语境别名归一化（接受中英文及常见说法）
CONTEXT_ALIASES = {
    "home": "home", "家": "home", "居家": "home", "家里": "home", "house": "home", "indoor": "home",
    "public": "public", "公共": "public", "公共场所": "public", "户外": "public",
    "outdoor": "public", "outside": "public", "图书馆": "public", "学校": "public", "办公室": "public",
    "transit": "transit", "交通": "transit", "交通工具": "transit", "车": "transit",
    "飞机": "transit", "大巴": "transit", "公交": "transit", "火车": "transit",
    "vehicle": "transit", "plane": "transit", "bus": "transit", "train": "transit", "car": "transit",
    "pet": "pet", "宠物": "pet", "动物": "pet", "猫": "pet", "狗": "pet",
    "走失": "pet", "animal": "pet", "cat": "pet", "dog": "pet",
    "general": "general", "通用": "general", "未知": "general", "auto": "general", "unknown": "general",
}


def normalize_context(value: Optional[str]) -> str:
    if not value:
        return DEFAULT_CONTEXT
    return CONTEXT_ALIASES.get(value.strip().lower(), CONTEXT_ALIASES.get(value.strip(), DEFAULT_CONTEXT))


def get_scenes(gua_num: int, context: str) -> List[str]:
    by_ctx = BAGUA[gua_num]["scenes_by_context"]
    return by_ctx.get(context, by_ctx[DEFAULT_CONTEXT])


def _combine_direction(d1: str, d2: str) -> Optional[str]:
    """两正交方向 → 复合方向；同向/对冲/无法合成 → None"""
    if d1 == d2:
        return None
    pairs = {
        frozenset(["南", "西"]): "西南(坤)",
        frozenset(["南", "东"]): "东南(巽)",
        frozenset(["北", "西"]): "西北(乾)",
        frozenset(["北", "东"]): "东北(艮)",
    }
    return pairs.get(frozenset([d1, d2]))


HEXAGRAMS: Dict[Tuple[int, int], Tuple[int, str]] = {
    (1, 1): (1, "乾為天"),
    (1, 2): (10, "天澤履"),
    (1, 3): (13, "天火同人"),
    (1, 4): (25, "天雷无妄"),
    (1, 5): (44, "天風姤"),
    (1, 6): (6, "天水訟"),
    (1, 7): (33, "天山遯"),
    (1, 8): (12, "天地否"),
    (2, 1): (43, "澤天夬"),
    (2, 2): (58, "兌為澤"),
    (2, 3): (49, "澤火革"),
    (2, 4): (17, "澤雷隨"),
    (2, 5): (28, "澤風大過"),
    (2, 6): (47, "澤水困"),
    (2, 7): (31, "澤山咸"),
    (2, 8): (45, "澤地萃"),
    (3, 1): (14, "火天大有"),
    (3, 2): (38, "火澤睽"),
    (3, 3): (30, "離為火"),
    (3, 4): (21, "火雷噬嗑"),
    (3, 5): (50, "火風鼎"),
    (3, 6): (64, "火水未濟"),
    (3, 7): (56, "火山旅"),
    (3, 8): (35, "火地晉"),
    (4, 1): (34, "雷天大壯"),
    (4, 2): (54, "雷澤歸妹"),
    (4, 3): (55, "雷火豐"),
    (4, 4): (51, "震為雷"),
    (4, 5): (32, "雷風恆"),
    (4, 6): (40, "雷水解"),
    (4, 7): (62, "雷山小過"),
    (4, 8): (16, "雷地豫"),
    (5, 1): (9, "風天小畜"),
    (5, 2): (61, "風澤中孚"),
    (5, 3): (37, "風火家人"),
    (5, 4): (42, "風雷益"),
    (5, 5): (57, "巽為風"),
    (5, 6): (59, "風水渙"),
    (5, 7): (53, "風山漸"),
    (5, 8): (20, "風地觀"),
    (6, 1): (5, "水天需"),
    (6, 2): (60, "水澤節"),
    (6, 3): (63, "水火既濟"),
    (6, 4): (3, "水雷屯"),
    (6, 5): (48, "水風井"),
    (6, 6): (29, "坎為水"),
    (6, 7): (39, "水山蹇"),
    (6, 8): (8, "水地比"),
    (7, 1): (26, "山天大畜"),
    (7, 2): (41, "山澤損"),
    (7, 3): (22, "山火賁"),
    (7, 4): (27, "山雷頤"),
    (7, 5): (18, "山風蠱"),
    (7, 6): (4, "山水蒙"),
    (7, 7): (52, "艮為山"),
    (7, 8): (23, "山地剝"),
    (8, 1): (11, "地天泰"),
    (8, 2): (19, "地澤臨"),
    (8, 3): (36, "地火明夷"),
    (8, 4): (24, "地雷復"),
    (8, 5): (46, "地風升"),
    (8, 6): (7, "地水師"),
    (8, 7): (15, "地山謙"),
    (8, 8): (2, "坤為地"),
}

DIZHI = {
    1: "子",
    2: "丑",
    3: "寅",
    4: "卯",
    5: "辰",
    6: "巳",
    7: "午",
    8: "未",
    9: "申",
    10: "酉",
    11: "戌",
    12: "亥",
}

SHICHEN = {
    0: (1, "子"),
    1: (2, "丑"),
    2: (2, "丑"),
    3: (3, "寅"),
    4: (3, "寅"),
    5: (4, "卯"),
    6: (4, "卯"),
    7: (5, "辰"),
    8: (5, "辰"),
    9: (6, "巳"),
    10: (6, "巳"),
    11: (7, "午"),
    12: (7, "午"),
    13: (8, "未"),
    14: (8, "未"),
    15: (9, "申"),
    16: (9, "申"),
    17: (10, "酉"),
    18: (10, "酉"),
    19: (11, "戌"),
    20: (11, "戌"),
    21: (12, "亥"),
    22: (12, "亥"),
    23: (1, "子"),
}

FINDABILITY_RULES: Dict[str, Dict[str, str]] = {
    "用生體": {
        "tendency": "易得",
        "distance": "近",
        "confidence": "高",
        "reason": "用生体，失物多在近处，容易发现",
    },
    "體用比和": {
        "tendency": "易得",
        "distance": "近",
        "confidence": "高",
        "reason": "体用比和，原处附近即可找到",
    },
    "體克用": {
        "tendency": "可得",
        "distance": "中",
        "confidence": "中",
        "reason": "体克用，需主动寻找，费力但能找回",
    },
    "用克體": {
        "tendency": "难寻",
        "distance": "远",
        "confidence": "中",
        "reason": "用克体，恐已离身或被他人取走",
    },
    "體生用": {
        "tendency": "难得",
        "distance": "远",
        "confidence": "低",
        "reason": "体生用，耗神费力，多半难以找回",
    },
}

DISCLAIMER = (
    "本结果是结构化搜索启发，用于打破搜寻盲区，仅供参考，"
    "不作绝对预言。最终决策请结合实际情况。"
)


# ---------------------------------------------------------------------------
# 农历与起卦
# ---------------------------------------------------------------------------


def gregorian_to_lunar(year: int, month: int, day: int) -> Tuple[int, int, int, bool]:
    if LunarDate is None:
        raise ImportError("需要安装 lunardate：pip install lunardate")
    lunar = LunarDate.fromSolarDate(year, month, day)
    is_leap = getattr(lunar, "isLeapMonth", False)
    return lunar.year, lunar.month, lunar.day, bool(is_leap)


def get_year_dizhi(lunar_year: int) -> Tuple[int, str]:
    dizhi_num = ((lunar_year - 4) % 12) + 1
    return dizhi_num, DIZHI[dizhi_num]


def get_shichen(hour: int) -> Tuple[int, str]:
    return SHICHEN[hour]


def num_to_gua(n: int) -> int:
    remainder = n % 8
    return 8 if remainder == 0 else remainder


def num_to_yao(n: int) -> int:
    remainder = n % 6
    return 6 if remainder == 0 else remainder


def get_hexagram_binary(upper: int, lower: int) -> str:
    return BAGUA[upper]["binary"] + BAGUA[lower]["binary"]


def apply_change(binary: str, yao_position: int) -> str:
    index = 6 - yao_position
    bits = list(binary)
    bits[index] = "0" if bits[index] == "1" else "1"
    return "".join(bits)


def binary_to_gua_pair(binary: str) -> Tuple[int, int]:
    return BINARY_TO_GUA[binary[:3]], BINARY_TO_GUA[binary[3:]]


def get_hu_gua(binary: str) -> Tuple[int, int]:
    return BINARY_TO_GUA[binary[1:4]], BINARY_TO_GUA[binary[2:5]]


def analyze_wuxing(ti_element: str, yong_element: str) -> str:
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    if ti_element == yong_element:
        return "體用比和"
    if sheng.get(yong_element) == ti_element:
        return "用生體"
    if sheng.get(ti_element) == yong_element:
        return "體生用"
    if ke.get(ti_element) == yong_element:
        return "體克用"
    if ke.get(yong_element) == ti_element:
        return "用克體"
    return "未知關係"


# ---------------------------------------------------------------------------
# 卦象分析
# ---------------------------------------------------------------------------


@dataclass
class HexagramAnalysis:
    upper_gua: int
    lower_gua: int
    changing_line: int
    binary: str
    hex_num: int
    hex_name: str
    ti_gua: int
    yong_gua: int
    ti_position: str
    yong_position: str
    wuxing_relation: str
    ti_element: str
    yong_element: str
    hu_upper: int
    hu_lower: int
    hu_name: str
    bian_upper: int
    bian_lower: int
    bian_name: str
    bian_binary: str


def analyze_hexagram(upper_gua: int, lower_gua: int, changing_line: int) -> HexagramAnalysis:
    binary = get_hexagram_binary(upper_gua, lower_gua)
    hex_num, hex_name = HEXAGRAMS.get((upper_gua, lower_gua), (0, "未知卦"))

    if changing_line > 3:
        ti_gua, yong_gua = lower_gua, upper_gua
        ti_position, yong_position = "下卦", "上卦"
    else:
        ti_gua, yong_gua = upper_gua, lower_gua
        ti_position, yong_position = "上卦", "下卦"

    bian_binary = apply_change(binary, changing_line)
    bian_upper, bian_lower = binary_to_gua_pair(bian_binary)
    _, bian_name = HEXAGRAMS.get((bian_upper, bian_lower), (0, "未知卦"))

    hu_upper, hu_lower = get_hu_gua(binary)
    _, hu_name = HEXAGRAMS.get((hu_upper, hu_lower), (0, "未知卦"))

    ti_element = BAGUA[ti_gua]["element"]
    yong_element = BAGUA[yong_gua]["element"]
    wuxing_relation = analyze_wuxing(ti_element, yong_element)

    return HexagramAnalysis(
        upper_gua=upper_gua,
        lower_gua=lower_gua,
        changing_line=changing_line,
        binary=binary,
        hex_num=hex_num,
        hex_name=hex_name,
        ti_gua=ti_gua,
        yong_gua=yong_gua,
        ti_position=ti_position,
        yong_position=yong_position,
        wuxing_relation=wuxing_relation,
        ti_element=ti_element,
        yong_element=yong_element,
        hu_upper=hu_upper,
        hu_lower=hu_lower,
        hu_name=hu_name,
        bian_upper=bian_upper,
        bian_lower=bian_lower,
        bian_name=bian_name,
        bian_binary=bian_binary,
    )


# ---------------------------------------------------------------------------
# 失物占断卦
# ---------------------------------------------------------------------------


def _scope_for_location(role: str, yong_is_outer: bool, context: str) -> str:
    """范围语言通用化：基于内/外卦判远近，不假设居家。"""
    if role == "用卦":
        if context == "pet":
            return "已走远，需扩大范围" if yong_is_outer else "应未走远，在附近活动"
        return "可能已离开原处或在外围" if yong_is_outer else "应在原处附近"
    if role == "变卦":
        return "可能去到的下一处" if context == "pet" else "可能被移动到的位置"
    # 互卦
    return "途中经过处" if context == "pet" else "中间经过/过渡处"


def _location_from_gua(
    gua_num: int,
    rank: int,
    role: str,
    yong_is_outer: bool,
    distance: str,
    context: str,
    *,
    paired_gua_num: Optional[int] = None,
    hexagram_name: Optional[str] = None,
) -> Dict[str, Any]:
    info = BAGUA[gua_num]
    scope = _scope_for_location(role, yong_is_outer, context)
    location: Dict[str, Any] = {
        "rank": rank,
        "direction": info["direction"],
        "scenes": get_scenes(gua_num, context)[:5],
        "scope": scope,
        "distance": distance,
        "note": f"{role}{info['name']}（{info['element']}）— {info['direction']}方",
        "trigram": info["name"],
        "element": info["element"],
    }

    if paired_gua_num is not None:
        paired_info = BAGUA[paired_gua_num]
        location["paired_trigram"] = paired_info["name"]
        location["paired_direction"] = paired_info["direction"]

        combined = _combine_direction(info["direction"], paired_info["direction"])
        if combined:
            location["combined_direction"] = combined

        if hexagram_name:
            location["hexagram_note"] = (
                f"{role}源自{hexagram_name}，"
                f"另半为{paired_info['name']}（{paired_info['direction']}），"
                f"两卦合参可获更完整方位线索"
            )

        location["note"] = (
            f"{role}{info['name']}（{info['element']}）— {info['direction']}方"
            f"（卦体另半：{paired_info['name']} {paired_info['direction']}）"
        )

    if context == "pet":
        location["animal_image"] = f"{info['name']}为{info['animal']}"
    return location


def _infer_moved(analysis: HexagramAnalysis, context: str) -> str:
    subject = "宠物" if context == "pet" else "物"
    yong = analysis.yong_gua
    bian_yong = analysis.bian_upper if analysis.yong_position == "上卦" else analysis.bian_lower
    bian_ti = analysis.bian_lower if analysis.yong_position == "上卦" else analysis.bian_upper

    if yong == bian_yong:
        if context == "pet":
            return "宠物可能仍在初始方位附近活动，未远离"
        return "物似仍在原类场景中，可能未远离初始方位"

    # 构建变卦双向方位提示
    bian_yong_dir = BAGUA[bian_yong]["direction"]
    bian_ti_dir = BAGUA[bian_ti]["direction"]
    combined = _combine_direction(bian_yong_dir, bian_ti_dir)
    dir_hint = f"变卦{analysis.bian_name}方位：{bian_yong_dir}（{BAGUA[bian_yong]['name']}）"
    if combined:
        dir_hint += f"合{combined}方"
    else:
        dir_hint += f"，另半{bian_ti_dir}（{BAGUA[bian_ti]['name']}）"

    relation = analyze_wuxing(
        BAGUA[analysis.ti_gua]["element"],
        BAGUA[bian_yong]["element"],
    )
    if relation in ("用克體", "體生用"):
        return f"{subject}可能已移动至远处，或经他人之手/已离开原场所。{dir_hint}"
    if relation in ("體克用", "用生體", "體用比和"):
        return f"{subject}可能有移动，但仍有机会在第二搜索区寻得。{dir_hint}"
    return f"{subject}可能有移动，建议同时搜索变卦所示方位。{dir_hint}"


def _build_action_advice(
    locations: List[Dict[str, Any]],
    findability: Dict[str, str],
    context: str,
) -> str:
    if not locations:
        return "请结合实际情况，从失物最后出现的地点向外系统搜寻。"

    first = locations[0]
    scenes = "、".join(first["scenes"][:3])
    direction = first["direction"]
    tendency = findability.get("tendency", "未知")
    # 方位是跨语境最稳定的线索，建议以「失物最后出现的地点」为原点判断方位
    verb = "前往" if context == "pet" else "搜索"

    parts = [f"以失物最后出现的位置为原点，优先朝{direction}方向{verb}（重点：{scenes}）。"]

    if len(locations) > 1:
        second = locations[1]
        second_scenes = "、".join(second["scenes"][:2])
        second_part = f"若未果，再查{second['direction']}方向（{second_scenes}）"
        if "combined_direction" in second:
            second_part += f"；变卦两卦合参指向{second['combined_direction']}方，可同时关注"
        second_part += "。"
        parts.append(second_part)

    if context == "pet":
        if tendency in ("易得", "可得"):
            parts.append("卦象倾向可寻回，宠物或会自归或在近处，呼唤+守候原地。")
        else:
            parts.append("卦象倾向费力，宜尽快沿上述方向寻找并发布寻宠信息。")
    else:
        if tendency in ("易得", "可得"):
            parts.append("卦象倾向可找回，请耐心细查上述方向的区域。")
        elif tendency == "难寻":
            parts.append("卦象倾向难寻，建议扩大搜索、回忆最后使用地点，必要时联系失物招领或报警。")
        else:
            parts.append("卦象倾向费力，可扩大范围或请他人协助回忆。")

    return "".join(parts)


def build_search_report(
    analysis: HexagramAnalysis,
    *,
    method: str,
    item_name: Optional[str] = None,
    context: str = DEFAULT_CONTEXT,
    casting_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = normalize_context(context)
    yong_is_outer = analysis.yong_position == "上卦"

    relation_key = analysis.wuxing_relation
    findability = FINDABILITY_RULES.get(
        relation_key,
        {
            "tendency": "未知",
            "distance": "中",
            "confidence": "低",
            "reason": f"体用关系：{relation_key}",
        },
    ).copy()
    findability["relation"] = relation_key

    distance = findability["distance"]
    locations: List[Dict[str, Any]] = []

    locations.append(
        _location_from_gua(
            analysis.yong_gua,
            rank=1,
            role="用卦",
            yong_is_outer=yong_is_outer,
            distance=distance,
            context=context,
        )
    )

    bian_yong = analysis.bian_upper if yong_is_outer else analysis.bian_lower
    bian_ti = analysis.bian_lower if yong_is_outer else analysis.bian_upper
    if bian_yong != analysis.yong_gua:
        locations.append(
            _location_from_gua(
                bian_yong,
                rank=2,
                role="变卦",
                yong_is_outer=yong_is_outer,
                distance=distance,
                context=context,
                paired_gua_num=bian_ti,
                hexagram_name=analysis.bian_name,
            )
        )

    hu_gua_for_path = analysis.hu_upper if yong_is_outer else analysis.hu_lower
    hu_other = analysis.hu_lower if yong_is_outer else analysis.hu_upper
    if hu_gua_for_path not in (analysis.yong_gua, bian_yong):
        locations.append(
            _location_from_gua(
                hu_gua_for_path,
                rank=len(locations) + 1,
                role="互卦",
                yong_is_outer=yong_is_outer,
                distance=distance,
                context=context,
                paired_gua_num=hu_other,
                hexagram_name=analysis.hu_name,
            )
        )

    moved = _infer_moved(analysis, context)
    action_advice = _build_action_advice(locations, findability, context)

    ti_info = BAGUA[analysis.ti_gua]
    yong_info = BAGUA[analysis.yong_gua]

    report: Dict[str, Any] = {
        "item_name": item_name,
        "context": context,
        "context_label": CONTEXT_LABELS.get(context, context),
        "casting": {
            "method": method,
            "hexagram": analysis.hex_name,
            "hex_num": analysis.hex_num,
            "changing_line": analysis.changing_line,
            "binary": analysis.binary,
            "upper": f"{BAGUA[analysis.upper_gua]['name']} {BAGUA[analysis.upper_gua]['symbol']}",
            "lower": f"{BAGUA[analysis.lower_gua]['name']} {BAGUA[analysis.lower_gua]['symbol']}",
            **(casting_meta or {}),
        },
        "ti_yong": {
            "ti": f"{ti_info['name']}（{analysis.ti_position}）— {ti_info['element']}",
            "yong": f"{yong_info['name']}（{analysis.yong_position}）— {yong_info['element']}",
            "relation": analysis.wuxing_relation,
        },
        "mutual_hexagram": {
            "name": analysis.hu_name,
            "upper": BAGUA[analysis.hu_upper]["name"],
            "lower": BAGUA[analysis.hu_lower]["name"],
        },
        "transformed_hexagram": {
            "name": analysis.bian_name,
            "binary": analysis.bian_binary,
            "upper": BAGUA[analysis.bian_upper]["name"],
            "lower": BAGUA[analysis.bian_lower]["name"],
        },
        "findability": findability,
        "primary_direction": locations[0]["direction"] if locations else None,
        "direction_note": "方位是跨语境最稳定的线索，请以失物最后出现的位置为原点判断。",
        "locations": locations,
        "moved": moved,
        "action_advice": action_advice,
        "disclaimer": DISCLAIMER,
    }
    return report


# ---------------------------------------------------------------------------
# 起卦入口
# ---------------------------------------------------------------------------


def cast_by_lunar_time(
    lunar_year: int,
    lunar_month: int,
    lunar_day: int,
    hour: int,
    item_name: Optional[str] = None,
    context: str = DEFAULT_CONTEXT,
) -> Dict[str, Any]:
    year_num, year_dizhi = get_year_dizhi(lunar_year)
    shichen_num, shichen_name = get_shichen(hour)

    upper_sum = year_num + lunar_month + lunar_day
    lower_sum = upper_sum + shichen_num

    upper_gua = num_to_gua(upper_sum)
    lower_gua = num_to_gua(lower_sum)
    changing_line = num_to_yao(lower_sum)

    analysis = analyze_hexagram(upper_gua, lower_gua, changing_line)
    meta = {
        "lunar_time": f"{lunar_year}年{lunar_month}月{lunar_day}日 {shichen_name}时",
        "year_dizhi": f"{year_dizhi}年 ({year_num})",
        "month": lunar_month,
        "day": lunar_day,
        "shichen": f"{shichen_name}时 ({shichen_num})",
        "calculation": {
            "upper_sum": upper_sum,
            "lower_sum": lower_sum,
            "upper_gua": upper_gua,
            "lower_gua": lower_gua,
            "changing_line": changing_line,
        },
    }
    return build_search_report(
        analysis, method="lunar_time", item_name=item_name, context=context, casting_meta=meta
    )


def cast_by_gregorian_time(
    year: int,
    month: int,
    day: int,
    hour: int,
    item_name: Optional[str] = None,
    context: str = DEFAULT_CONTEXT,
) -> Dict[str, Any]:
    lunar_year, lunar_month, lunar_day, is_leap = gregorian_to_lunar(year, month, day)
    report = cast_by_lunar_time(lunar_year, lunar_month, lunar_day, hour, item_name, context)
    leap_label = "闰" if is_leap else ""
    report["casting"]["gregorian_time"] = f"{year}年{month}月{day}日 {hour}时"
    report["casting"]["lunar_time"] = (
        f"{lunar_year}年{leap_label}{lunar_month}月{lunar_day}日 "
        f"{report['casting']['shichen'].split(' ')[0]}"
    )
    report["casting"]["method"] = "gregorian_time"
    return report


def cast_by_numbers(
    num1: int,
    num2: int,
    num3: Optional[int] = None,
    item_name: Optional[str] = None,
    context: str = DEFAULT_CONTEXT,
) -> Dict[str, Any]:
    upper_gua = num_to_gua(num1)
    lower_gua = num_to_gua(num2)
    changing_line = num_to_yao(num3 if num3 is not None else num1 + num2)

    analysis = analyze_hexagram(upper_gua, lower_gua, changing_line)
    meta = {
        "numbers": [num1, num2] + ([num3] if num3 is not None else []),
        "calculation": {
            "upper_gua": upper_gua,
            "lower_gua": lower_gua,
            "changing_line": changing_line,
        },
    }
    return build_search_report(
        analysis, method="numbers", item_name=item_name, context=context, casting_meta=meta
    )


def cast_now(item_name: Optional[str] = None, context: str = DEFAULT_CONTEXT) -> Dict[str, Any]:
    now = datetime.now()
    return cast_by_gregorian_time(now.year, now.month, now.day, now.hour, item_name, context)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_usage() -> None:
    print(
        """用法:
  python shiwu_calc.py time [--item 物品名] [--context 语境]
  python shiwu_calc.py gregorian Y M D H [--item 物品名] [--context 语境]
  python shiwu_calc.py lunar Y M D H [--item 物品名] [--context 语境]
  python shiwu_calc.py num N1 N2 [N3] [--item 物品名] [--context 语境]

语境(--context): home(居家) | public(公共场所/户外) | transit(交通工具) | pet(走失生物) | general(默认/通用)

示例:
  python shiwu_calc.py time --item 护照 --context home
  python shiwu_calc.py gregorian 2026 6 17 14 --item 充电线 --context public
  python shiwu_calc.py num 1 6 1 --item 金手链 --context home
  python shiwu_calc.py time --item 猫 --context pet
"""
    )


def _parse_flags(argv: List[str]) -> Tuple[List[str], Optional[str], Optional[str]]:
    item_name = None
    context = None
    cleaned: List[str] = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--item", "-i") and i + 1 < len(argv):
            item_name = argv[i + 1]
            i += 2
        elif argv[i] in ("--context", "-c") and i + 1 < len(argv):
            context = argv[i + 1]
            i += 2
        else:
            cleaned.append(argv[i])
            i += 1
    return cleaned, item_name, context


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    argv, item_name, context_raw = _parse_flags(argv)
    context = normalize_context(context_raw)

    if not argv:
        report = cast_now(item_name, context)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    cmd = argv[0]

    try:
        if cmd == "time":
            report = cast_now(item_name, context)
        elif cmd == "gregorian" and len(argv) >= 5:
            report = cast_by_gregorian_time(
                int(argv[1]), int(argv[2]), int(argv[3]), int(argv[4]), item_name, context
            )
        elif cmd == "lunar" and len(argv) >= 5:
            report = cast_by_lunar_time(
                int(argv[1]), int(argv[2]), int(argv[3]), int(argv[4]), item_name, context
            )
        elif cmd == "num" and len(argv) >= 3:
            n3 = int(argv[3]) if len(argv) > 3 and argv[3].lstrip("-").isdigit() else None
            nums = [int(argv[1]), int(argv[2])]
            if n3 is not None:
                nums.append(n3)
            report = cast_by_numbers(
                nums[0], nums[1], nums[2] if len(nums) > 2 else None, item_name, context
            )
        else:
            _print_usage()
            return 1
    except (ValueError, ImportError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
