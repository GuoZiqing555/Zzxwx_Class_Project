"""Prompt builders for the communication strategy demo."""

import json
from typing import Any


SYSTEM_PROMPT = """你是一个组织行为学课程项目中的“沟通策略参谋”。
你的任务不是做心理诊断，也不是保证说服成功，而是基于用户提供的职场沟通情境，使用组织行为学概念生成可演示、可执行、措辞谨慎的沟通建议。

必须遵守：
1. 全程使用中文。
2. 使用“可能、倾向、建议、风险”这类审慎表达，不把人格、情绪或动机说成确定事实。
3. 输出必须是合法 JSON，不要使用 Markdown 代码块，不要添加 JSON 以外的解释。
4. 话术要自然、简洁、能直接复制使用。
5. 理论不是装饰性标签。每项理论应用必须明确连接：用户输入证据 -> 审慎推断 -> 沟通动作 -> 对应话术。
6. 只能使用本次提供的理论工具箱。缺少证据时应明确说明需要验证，不要为了覆盖理论而强行推断。
"""


def build_strategy_prompt(
    form_data: dict[str, Any],
    book_candidates: list[dict[str, str]],
    theory_cards: list[dict[str, Any]],
) -> str:
    """Build the main analysis prompt."""
    pretty_data = json.dumps(form_data, ensure_ascii=False, indent=2)
    pretty_books = json.dumps(book_candidates, ensure_ascii=False, indent=2)
    pretty_theories = json.dumps(theory_cards, ensure_ascii=False, indent=2)
    return f"""请根据以下用户填写的沟通情境表，生成一个完整的沟通策略方案。

用户输入：
{pretty_data}

本地书单检索出的候选书：
{pretty_books}

本次可使用的理论工具箱：
{pretty_theories}

理论应用规则：
- 不要只复述理论定义。先引用用户输入中的具体证据，再进行审慎推断。
- 如果证据不足，inference 中应写明“需要通过提问验证”，并在 action 中给出验证问题。
- 每项理论必须落到一个可执行动作，并说明它影响哪一段话术。
- theory_id 只能使用理论工具箱中的 id；theory_name 必须原样使用工具箱中的 name。
- 理论工具箱中的 boundary 是使用边界，输出时必须遵守。

请严格输出如下 JSON 结构：
{{
  "brief": "约150字分析简报，包含对方可能类型、核心诉求、情绪根源和沟通雷区。",
  "theory_applications": [
    {{
      "theory_id": "理论工具箱中的 id",
      "theory_name": "理论工具箱中的 name",
      "evidence": ["来自用户输入的具体线索；如果缺少证据，写明待验证"],
      "inference": "基于理论的审慎推断，不要写成确定事实",
      "action": "由此推导出的沟通动作或验证问题",
      "script_link": "该动作如何体现在某条话术中"
    }}
  ],
  "engines": {{
    "position_needs": {{
      "title": "立场 & 诉求分析",
      "surface_position": "对方表面上可能反对什么",
      "underlying_needs": ["背后诉求1", "背后诉求2", "背后诉求3"],
      "fairness_risks": ["可能让对方感到不公平或不被尊重的表达方式"],
      "recommendation": "建议如何切入"
    }},
    "personality": {{
      "title": "性格识别",
      "big_five_tendencies": ["大五人格可能倾向，使用谨慎措辞"],
      "recommended_style": "逻辑型/情感型/愿景型/混合型之一，并说明原因",
      "avoid": ["应避免的表达方式"]
    }},
    "emotion": {{
      "title": "情绪洞察",
      "abc": {{
        "a_event": "A 诱发事件",
        "b_belief": "B 可能的信念或解释",
        "c_emotion": "C 可能情绪反应",
        "intervention": "修正 B 的沟通切入点"
      }},
      "self_awareness_risks": ["用户自身可能的沟通惯性或风险"],
      "regulation_tip": "用户自我调节建议"
    }},
    "persuasion": {{
      "title": "说服策略匹配",
      "strategies": [
        {{
          "principle": "西奥迪尼原则名称",
          "why": "为什么适合当前情境",
          "sentence_pattern": "对应句式"
        }}
      ]
    }}
  }},
  "talking_points": [
    {{
      "label": "开场话术1",
      "principles": ["互惠", "权威"],
      "style": "表达风格",
      "text": "可直接复制的话术"
    }},
    {{
      "label": "开场话术2",
      "principles": ["原则"],
      "style": "表达风格",
      "text": "可直接复制的话术"
    }},
    {{
      "label": "开场话术3",
      "principles": ["原则"],
      "style": "表达风格",
      "text": "可直接复制的话术"
    }}
  ],
  "contingencies": [
    {{
      "likely_response": "对方最可能反应1",
      "response_strategy": "应对策略",
      "reply": "应对话术"
    }},
    {{
      "likely_response": "对方最可能反应2",
      "response_strategy": "应对策略",
      "reply": "应对话术"
    }}
  ],
  "cool_down": "如果对方情绪激化，可以使用的降温话术。",
  "next_steps": ["沟通前准备事项1", "沟通前准备事项2", "沟通前准备事项3"],
  "recommended_books": [
    {{
      "id": "候选书编号",
      "title": "候选书中文名",
      "author": "候选书作者",
      "reason": "为什么这本书适合当前沟通情境",
      "reading_focus": "建议优先关注的概念或方法"
    }}
  ]
}}

字段数量要求：
- theory_applications 选择最有解释力的 4 到 6 项理论，不要机械覆盖全部理论。
- talking_points 必须正好 3 条。
- contingencies 必须正好 2 条。
- persuasion.strategies 建议 2 到 3 条。
- recommended_books 必须推荐 2 到 3 本书。
- recommended_books 只能从“本地书单检索出的候选书”中选择，id、title 和 author 必须原样使用候选书信息，不要虚构书籍。
"""


def build_rehearsal_prompt(
    form_data: dict[str, Any],
    strategy: dict[str, Any],
    history: list[dict[str, str]],
    latest_reaction: str,
) -> str:
    """Build a follow-up rehearsal prompt."""
    payload = {
        "original_context": form_data,
        "current_strategy": strategy,
        "rehearsal_history": history,
        "latest_reaction": latest_reaction,
    }
    pretty_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"""请根据以下演练上下文，生成下一轮沟通应对建议。

上下文：
{pretty_payload}

请严格输出如下 JSON：
{{
  "read": "对方这次反应可能说明了什么，使用审慎表达。",
  "theory_basis": "本轮主要沿用 current_strategy.theory_applications 中的哪项理论，以及为什么。",
  "verification_question": "为了避免过度推断，本轮建议向对方确认的一个问题。",
  "recommended_move": "下一步沟通动作，简洁明确。",
  "reply": "用户可以直接说出口的话术。",
  "risk": "如果继续推进，最大的沟通风险是什么。",
  "fallback": "如果对方仍不接受，可以如何收束对话。"
}}
"""
