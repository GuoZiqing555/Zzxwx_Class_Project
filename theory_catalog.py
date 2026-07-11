"""Structured theory cards for traceable communication strategy generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Theory:
    id: str
    name: str
    domain: str
    core_question: str
    concepts: tuple[str, ...]
    evidence_cues: tuple[str, ...]
    application_steps: tuple[str, ...]
    boundary: str
    triggers: tuple[str, ...] = ()
    required: bool = False

    def for_prompt(self) -> dict[str, Any]:
        return asdict(self)


THEORIES = (
    Theory(
        id="equity_theory",
        name="公平理论",
        domain="组织行为学",
        core_question="对方是否可能把投入、回报、程序或互动方式理解为不公平？",
        concepts=("投入与回报比较", "分配公平", "程序公平", "互动公平"),
        evidence_cues=("资源分配", "工作量", "认可", "待遇", "规则", "被尊重"),
        application_steps=("识别对方可能比较的参照对象", "说明分配依据与程序", "为对方保留表达和校正空间"),
        boundary="不能在缺少事实时断言对方感到不公平，也不能把所有异议都归因为利益计算。",
        triggers=("资源", "绩效", "反馈", "工作量", "待遇", "认可", "公平"),
        required=True,
    ),
    Theory(
        id="interest_based_negotiation",
        name="利益导向谈判",
        domain="谈判与冲突管理",
        core_question="对方的表面立场背后，可能有哪些可协商的利益、顾虑和约束？",
        concepts=("立场与利益分离", "共同收益", "客观标准", "备选方案"),
        evidence_cues=("拒绝", "资源", "跨部门", "冲突", "谈判", "顾虑"),
        application_steps=("区分表面立场与背后利益", "提出澄清问题", "寻找共同目标与可交换条件"),
        boundary="不能替对方确定真实动机；应把推测转化为待验证的问题。",
        triggers=("资源", "冲突", "拒绝", "谈判", "跨部门", "顾虑"),
        required=True,
    ),
    Theory(
        id="big_five",
        name="大五人格框架",
        domain="人格心理学",
        core_question="用户提供的行为线索，可能提示哪些沟通偏好？",
        concepts=("开放性", "尽责性", "外向性", "宜人性", "情绪稳定性"),
        evidence_cues=("重视数据", "谨慎保守", "追求效率", "关注关系", "重视创新", "容易焦虑"),
        application_steps=("只引用用户提供的行为线索", "用可能倾向描述偏好", "调整信息密度、节奏和表达方式"),
        boundary="不能凭单次互动给对方贴人格标签，也不能把沟通偏好当作稳定人格结论。",
        triggers=("数据", "谨慎", "效率", "关系", "创新", "焦虑", "强势"),
        required=True,
    ),
    Theory(
        id="abc_model",
        name="ABC 模型",
        domain="认知行为取向",
        core_question="事件、解释和情绪反应之间可能存在怎样的链条？",
        concepts=("A 诱发事件", "B 信念或解释", "C 情绪与行为后果"),
        evidence_cues=("担心", "焦虑", "生气", "防御", "紧张", "历史冲突"),
        application_steps=("区分事件与解释", "提出可替代解释", "设计降低威胁感的表达"),
        boundary="这是沟通准备工具，不是心理诊断；不能声称识别了对方的真实信念。",
        triggers=("担心", "焦虑", "生气", "防御", "紧张", "情绪", "冲突"),
        required=True,
    ),
    Theory(
        id="metacognition",
        name="元认知",
        domain="认知心理学",
        core_question="用户自身可能有哪些自动化反应，需要在沟通前监测和调整？",
        concepts=("觉察自动想法", "区分事实与推断", "监测情绪唤醒", "预设暂停点"),
        evidence_cues=("担心", "通常感受", "历史沟通", "急于推进", "回避", "情绪升级"),
        application_steps=("识别自己的触发点", "准备事实与推断清单", "设置暂停和复述动作"),
        boundary="不评价用户人格，也不要求压抑情绪；重点是提升沟通时的选择空间。",
        triggers=("担心", "感受", "紧张", "焦虑", "冲突", "回避"),
        required=True,
    ),
    Theory(
        id="cialdini",
        name="西奥迪尼影响力原则",
        domain="社会心理学",
        core_question="哪些影响方式适合当前情境，并且不会演变为操控？",
        concepts=("互惠", "承诺与一致", "社会认同", "权威", "喜好", "稀缺", "共同体"),
        evidence_cues=("争取支持", "推动决策", "说服", "资源", "协作", "认可"),
        application_steps=("选择与情境匹配的原则", "说明真实依据", "给对方保留拒绝和讨论空间"),
        boundary="原则用于改善信息呈现和合作，不用于制造虚假稀缺、夸大权威或施压。",
        triggers=("资源", "决策", "支持", "说服", "协作", "认可"),
        required=True,
    ),
    Theory(
        id="psychological_safety",
        name="心理安全",
        domain="团队与组织行为学",
        core_question="对方是否可能担心表达异议、承认问题或承担人际风险？",
        concepts=("人际风险", "可表达异议", "容许提问", "复盘而非归罪"),
        evidence_cues=("公开会议", "团队", "冲突", "犯错", "质疑", "反馈"),
        application_steps=("降低公开暴露风险", "邀请异议", "先讨论事实和机制再讨论责任"),
        boundary="心理安全不等于降低标准，也不等于回避必要的绩效讨论。",
        triggers=("团队", "会议", "冲突", "反馈", "公开", "犯错", "质疑"),
    ),
    Theory(
        id="power_dependence",
        name="权力依赖视角",
        domain="组织行为学",
        core_question="双方掌握的资源、替代方案和正式权力如何影响沟通？",
        concepts=("资源依赖", "正式权力", "替代方案", "联盟与利益相关者"),
        evidence_cues=("领导", "跨部门", "资源", "审批", "支持", "权限"),
        application_steps=("识别双方资源与约束", "减少单点诉求", "准备客观依据和可接受备选"),
        boundary="用于理解组织约束，不用于鼓励操纵、绕过规则或政治报复。",
        triggers=("领导", "跨部门", "资源", "审批", "权限", "支持"),
    ),
    Theory(
        id="self_determination",
        name="自我决定理论",
        domain="动机心理学",
        core_question="沟通方案是否照顾到自主、胜任和关系三类基本心理需要？",
        concepts=("自主", "胜任", "关系"),
        evidence_cues=("授权", "激励", "绩效", "成长", "抵触", "参与"),
        application_steps=("提供有限但真实的选择", "明确支持与反馈", "说明共同目标和关系承诺"),
        boundary="不能把提供选择包装成虚假参与；约束条件应明确说明。",
        triggers=("绩效", "反馈", "激励", "成长", "授权", "抵触", "参与"),
    ),
    Theory(
        id="framing_effect",
        name="框架效应",
        domain="行为决策",
        core_question="同一方案以收益、损失或风险呈现时，是否可能引发不同反应？",
        concepts=("收益框架", "损失框架", "风险感知", "决策偏差"),
        evidence_cues=("风险", "决策", "保守", "损失", "收益", "方案比较"),
        application_steps=("同时呈现收益与风险", "避免只用单一框架推动结论", "提供可比较的客观信息"),
        boundary="不能利用偏差隐藏成本或风险；目标是提升判断质量。",
        triggers=("风险", "决策", "保守", "损失", "收益", "方案"),
    ),
)


def _query_text(form_data: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in form_data.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts)


def recommend_theories(form_data: dict[str, Any], limit: int = 9) -> list[dict[str, Any]]:
    """Return required theory cards plus contextual cards ranked by input cues."""
    query = _query_text(form_data)
    required = [theory for theory in THEORIES if theory.required]
    contextual = sorted(
        (theory for theory in THEORIES if not theory.required),
        key=lambda theory: (-sum(query.count(trigger) for trigger in theory.triggers), theory.id),
    )
    matched = [theory for theory in contextual if any(trigger in query for trigger in theory.triggers)]
    selected = (required + matched)[:limit]
    return [theory.for_prompt() for theory in selected]


def ground_theory_applications(
    strategy: dict[str, Any],
    theory_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """Keep theory traces attached to supplied cards and normalize card metadata."""
    catalog = {card["id"]: card for card in theory_cards}
    applications = strategy.get("theory_applications", [])
    if not isinstance(applications, list):
        applications = []

    grounded: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for application in applications:
        if not isinstance(application, dict):
            continue
        theory_id = str(application.get("theory_id", ""))
        if theory_id not in catalog or theory_id in selected_ids:
            continue
        card = catalog[theory_id]
        evidence = application.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = [str(evidence)] if evidence else []
        grounded.append(
            {
                "theory_id": theory_id,
                "theory_name": card["name"],
                "domain": card["domain"],
                "evidence": [str(item) for item in evidence if str(item).strip()],
                "inference": str(application.get("inference", "")).strip(),
                "action": str(application.get("action", "")).strip(),
                "script_link": str(application.get("script_link", "")).strip(),
                "boundary": card["boundary"],
            }
        )
        selected_ids.add(theory_id)
        if len(grounded) == 6:
            break

    strategy["theory_applications"] = grounded
    return strategy
