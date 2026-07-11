from __future__ import annotations

import json
from typing import Any

import streamlit as st

from book_recommender import ground_recommendations, recommend_candidates
from deepseek_client import DeepSeekConfigError, call_deepseek_json
from prompts import SYSTEM_PROMPT, build_rehearsal_prompt, build_strategy_prompt
from quota import QuotaExceededError, get_quota_status
from theory_catalog import ground_theory_applications, recommend_theories


st.set_page_config(
    page_title="沟通策略 AI Agent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --ink: #1d2733;
            --muted: #667085;
            --line: #d9e2ec;
            --accent: #247c7b;
            --accent-soft: #e8f5f3;
            --warm: #fff4df;
            --danger-soft: #fff0f0;
        }
        .main .block-container {
            padding-top: 2rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .app-hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 22px 24px;
            background: linear-gradient(135deg, #f7fbfa 0%, #fffaf0 100%);
            margin-bottom: 18px;
        }
        .app-title {
            font-size: 34px;
            font-weight: 760;
            line-height: 1.2;
            color: var(--ink);
            margin: 0 0 8px 0;
        }
        .app-subtitle {
            max-width: 860px;
            color: var(--muted);
            font-size: 16px;
            line-height: 1.7;
        }
        .metric-row {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 16px 0 4px;
        }
        .mini-card, .content-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface);
            padding: 16px;
        }
        .mini-label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 6px;
        }
        .mini-value {
            color: var(--ink);
            font-weight: 720;
            font-size: 15px;
        }
        .content-card {
            min-height: 132px;
            margin-bottom: 12px;
        }
        .card-title {
            font-size: 17px;
            font-weight: 760;
            color: var(--ink);
            margin-bottom: 8px;
        }
        .card-body {
            color: #344054;
            line-height: 1.65;
        }
        .tag {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
            font-size: 12px;
            margin: 2px 4px 2px 0;
            border: 1px solid #cce7e3;
        }
        .soft-note {
            border-left: 4px solid var(--accent);
            padding: 12px 14px;
            background: #f7fbfa;
            color: #344054;
            border-radius: 0 8px 8px 0;
            line-height: 1.7;
        }
        .warning-note {
            border-left: 4px solid #d98b00;
            padding: 12px 14px;
            background: var(--warm);
            color: #513a12;
            border-radius: 0 8px 8px 0;
            line-height: 1.7;
        }
        .stButton > button {
            border-radius: 7px;
            min-height: 42px;
            font-weight: 650;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            border-radius: 7px;
        }
        @media (max-width: 780px) {
            .metric-row {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .app-title {
                font-size: 28px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "form_data": {},
        "strategy": None,
        "rehearsal_history": [],
        "page": "情境填写",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def card(title: str, body: str, tags: list[str] | None = None) -> None:
    tag_html = "".join(f'<span class="tag">{tag}</span>' for tag in tags or [])
    st.markdown(
        f"""
        <div class="content-card">
            <div class="card-title">{title}</div>
            <div>{tag_html}</div>
            <div class="card-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bullet_block(items: list[str]) -> str:
    if not items:
        return "暂无"
    return "<br>".join(f"• {item}" for item in items)


def show_hero() -> None:
    st.markdown(
        """
        <div class="app-hero">
            <div class="app-title">沟通策略 AI Agent</div>
            <div class="app-subtitle">
                先诊断，再开方。根据职场沟通情境，结合组织行为学理论生成分析简报、可复制话术和多轮演练建议。
            </div>
            <div class="metric-row">
                <div class="mini-card"><div class="mini-label">分析逻辑</div><div class="mini-value">四大引擎</div></div>
                <div class="mini-card"><div class="mini-label">输出形式</div><div class="mini-value">话术 + 预案</div></div>
                <div class="mini-card"><div class="mini-label">演示定位</div><div class="mini-value">课程 Demo</div></div>
                <div class="mini-card"><div class="mini-label">模型接入</div><div class="mini-value">DeepSeek API</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> None:
    with st.sidebar:
        st.subheader("导航")
        pages = ["情境填写", "智能诊断", "理论依据", "话术包", "延伸阅读", "演练", "结果汇总"]
        st.session_state.page = st.radio(
            "选择页面",
            pages,
            index=pages.index(st.session_state.page),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("API 配置")
        try:
            quota = get_quota_status()
            st.metric("今日剩余体验次数", f"{quota.remaining} / {quota.limit}")
        except Exception:
            st.caption("体验配额暂不可用，请联系管理员。")
        st.caption("为保障服务稳定，所有用户共享每日体验额度。")
        st.divider()
        st.caption("声明")
        st.info("本 demo 只做沟通策略辅助，不进行心理诊断，也不保证沟通结果。")


def situation_page() -> None:
    show_hero()
    st.subheader("情境填写")

    with st.form("situation_form"):
        st.markdown("#### 第一步：基本情境")
        col1, col2 = st.columns(2)
        with col1:
            target = st.text_input("沟通对象", placeholder="例：直属领导、市场部负责人、项目成员")
            purpose = st.selectbox("沟通目的", ["争取资源", "推动决策", "解决冲突", "汇报进展", "绩效反馈", "对外谈判", "其他"])
        with col2:
            scene = st.selectbox("沟通场景", ["一对一会议", "邮件", "大会发言", "跨部门会议", "即时消息", "电话/视频会议"])
            expected_result = st.text_input("希望达成的结果", placeholder="例：获得两名临时人手支持")

        st.markdown("#### 第二步：对方信息")
        concerns = st.text_area("你觉得对方可能反对或顾虑什么？", height=96)
        style_words = st.multiselect(
            "对方工作风格描述词",
            ["重视数据", "谨慎保守", "追求效率", "关注关系", "重视创新", "强势直接", "容易焦虑", "喜欢公开认可", "风险敏感", "结果导向"],
        )
        history = st.text_area("之前有过类似沟通，结果如何？", height=76)

        st.markdown("#### 第三步：自我觉察")
        feelings = st.text_area("面对这个人，你通常的感受是什么？", height=76)
        worries = st.text_area("你最担心沟通中出现什么情况？", height=76)

        submitted = st.form_submit_button("生成沟通策略", use_container_width=True)

    if submitted:
        if not target.strip() or not expected_result.strip():
            st.warning("请至少填写“沟通对象”和“希望达成的结果”。")
            return

        form_data = {
            "target": target.strip(),
            "purpose": purpose,
            "scene": scene,
            "expected_result": expected_result.strip(),
            "concerns": concerns.strip(),
            "style_words": style_words,
            "history": history.strip(),
            "feelings": feelings.strip(),
            "worries": worries.strip(),
        }
        st.session_state.form_data = form_data
        st.session_state.strategy = None
        st.session_state.rehearsal_history = []

        with st.spinner("正在调用 DeepSeek 生成诊断与话术..."):
            try:
                book_candidates = recommend_candidates(form_data)
                theory_cards = recommend_theories(form_data)
                strategy = call_deepseek_json(
                    SYSTEM_PROMPT,
                    build_strategy_prompt(form_data, book_candidates, theory_cards),
                    required_keys={
                        "brief",
                        "theory_applications",
                        "engines",
                        "talking_points",
                        "contingencies",
                        "cool_down",
                        "next_steps",
                        "recommended_books",
                    },
                )
                strategy = ground_theory_applications(strategy, theory_cards)
                strategy = ground_recommendations(strategy, book_candidates)
            except (DeepSeekConfigError, QuotaExceededError) as exc:
                st.error(str(exc))
                st.stop()
            except Exception as exc:
                st.error(str(exc))
                st.stop()

        st.session_state.strategy = strategy
        st.session_state.page = "智能诊断"
        st.success("策略已生成，可以查看智能诊断和话术包。")
        st.rerun()


def require_strategy() -> dict[str, Any] | None:
    strategy = st.session_state.get("strategy")
    if not strategy:
        st.warning("请先在“情境填写”页面生成沟通策略。")
        return None
    return strategy


def diagnosis_page() -> None:
    strategy = require_strategy()
    if not strategy:
        return

    st.subheader("智能诊断")
    st.markdown(f'<div class="soft-note">{strategy.get("brief", "暂无分析简报。")}</div>', unsafe_allow_html=True)
    st.write("")

    engines = strategy.get("engines", {})
    col1, col2 = st.columns(2)
    with col1:
        position = engines.get("position_needs", {})
        card(
            "立场 & 诉求分析",
            f"""
            <b>表面立场：</b>{position.get("surface_position", "暂无")}<br>
            <b>背后诉求：</b><br>{bullet_block(as_list(position.get("underlying_needs")))}<br>
            <b>公平风险：</b><br>{bullet_block(as_list(position.get("fairness_risks")))}<br>
            <b>建议切入：</b>{position.get("recommendation", "暂无")}
            """,
            ["公平理论", "利益冲突"],
        )

        emotion = engines.get("emotion", {})
        abc = emotion.get("abc", {})
        card(
            "情绪洞察",
            f"""
            <b>A 事件：</b>{abc.get("a_event", "暂无")}<br>
            <b>B 信念：</b>{abc.get("b_belief", "暂无")}<br>
            <b>C 情绪：</b>{abc.get("c_emotion", "暂无")}<br>
            <b>切入点：</b>{abc.get("intervention", "暂无")}<br>
            <b>自我调节：</b>{emotion.get("regulation_tip", "暂无")}
            """,
            ["ABC 理论", "元认知"],
        )

    with col2:
        personality = engines.get("personality", {})
        card(
            "性格识别",
            f"""
            <b>可能倾向：</b><br>{bullet_block(as_list(personality.get("big_five_tendencies")))}<br>
            <b>推荐风格：</b>{personality.get("recommended_style", "暂无")}<br>
            <b>避免表达：</b><br>{bullet_block(as_list(personality.get("avoid")))}
            """,
            ["大五人格", "表达风格"],
        )

        persuasion = engines.get("persuasion", {})
        strategies = persuasion.get("strategies", [])
        body = ""
        for item in strategies:
            body += (
                f"<b>{item.get('principle', '策略')}</b>：{item.get('why', '暂无')}<br>"
                f"<span style='color:#667085'>句式：</span>{item.get('sentence_pattern', '暂无')}<br><br>"
            )
        card("说服策略匹配", body or "暂无", ["西奥迪尼", "影响力原则"])


def talking_points_page() -> None:
    strategy = require_strategy()
    if not strategy:
        return

    st.subheader("话术包")
    st.markdown('<div class="warning-note">这些话术是沟通准备素材，实际使用时可根据关系亲疏和现场语气微调。</div>', unsafe_allow_html=True)
    st.write("")

    for item in strategy.get("talking_points", []):
        card(
            item.get("label", "话术"),
            item.get("text", "暂无"),
            as_list(item.get("principles")) + [item.get("style", "")],
        )

    st.markdown("#### 预案备选")
    cols = st.columns(2)
    for idx, item in enumerate(strategy.get("contingencies", [])):
        with cols[idx % 2]:
            card(
                item.get("likely_response", f"反应 {idx + 1}"),
                f"<b>应对策略：</b>{item.get('response_strategy', '暂无')}<br><b>应对话术：</b>{item.get('reply', '暂无')}",
            )

    st.markdown("#### 情绪降温")
    st.markdown(f'<div class="soft-note">{strategy.get("cool_down", "暂无")}</div>', unsafe_allow_html=True)


def theory_page() -> None:
    strategy = require_strategy()
    if not strategy:
        return

    st.subheader("理论依据")
    st.markdown('<div class="soft-note">这里展示理论如何从用户提供的线索走向建议。推断仍然需要在真实沟通中通过提问验证，不能当作对他人的心理诊断。</div>', unsafe_allow_html=True)
    st.write("")

    applications = strategy.get("theory_applications", [])
    if not applications:
        st.info("本次策略暂未生成理论推导记录，请重新生成沟通策略。")
        return

    for item in applications:
        card(
            item.get("theory_name", "理论"),
            f"""
            <b>观察线索：</b><br>{bullet_block(as_list(item.get("evidence")))}<br>
            <b>审慎推断：</b>{item.get("inference", "暂无")}<br>
            <b>沟通动作：</b>{item.get("action", "暂无")}<br>
            <b>话术连接：</b>{item.get("script_link", "暂无")}<br>
            <b>使用边界：</b>{item.get("boundary", "暂无")}
            """,
            [item.get("domain", "理论工具")],
        )


def rehearsal_page() -> None:
    strategy = require_strategy()
    if not strategy:
        return

    st.subheader("多轮沟通演练")

    for turn in st.session_state.rehearsal_history:
        with st.chat_message("user"):
            st.write(turn["reaction"])
        with st.chat_message("assistant"):
            st.write(turn["reply"])
            st.caption(f"下一步：{turn['recommended_move']} | 风险：{turn['risk']}")
            if turn.get("theory_basis"):
                st.caption(f"理论依据：{turn['theory_basis']}")
            if turn.get("verification_question"):
                st.caption(f"验证问题：{turn['verification_question']}")

    reaction = st.chat_input("输入对方的实际反应或你想演练的回应...")
    if reaction:
        with st.spinner("正在生成下一轮应对..."):
            try:
                result = call_deepseek_json(
                    SYSTEM_PROMPT,
                    build_rehearsal_prompt(
                        st.session_state.form_data,
                        strategy,
                        st.session_state.rehearsal_history,
                        reaction,
                    ),
                    max_tokens=1300,
                    required_keys={
                        "read",
                        "theory_basis",
                        "verification_question",
                        "recommended_move",
                        "reply",
                        "risk",
                        "fallback",
                    },
                )
            except (DeepSeekConfigError, QuotaExceededError) as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                st.error(str(exc))
                return

        st.session_state.rehearsal_history.append(
            {
                "reaction": reaction,
                "read": result.get("read", ""),
                "theory_basis": result.get("theory_basis", ""),
                "verification_question": result.get("verification_question", ""),
                "recommended_move": result.get("recommended_move", ""),
                "reply": result.get("reply", ""),
                "risk": result.get("risk", ""),
                "fallback": result.get("fallback", ""),
            }
        )
        st.rerun()


def books_page() -> None:
    strategy = require_strategy()
    if not strategy:
        return

    st.subheader("延伸阅读")
    st.markdown('<div class="soft-note">以下书籍来自本地书单，并根据当前沟通情境筛选。可以把它们作为沟通前准备或事后复盘的延伸材料。</div>', unsafe_allow_html=True)
    st.write("")

    books = strategy.get("recommended_books", [])
    if not books:
        st.info("本次策略暂未生成书籍推荐，请重新生成沟通策略。")
        return

    for item in books:
        card(
            f"《{item.get('title', '未命名书籍')}》",
            f"""
            <b>作者：</b>{item.get("author", "暂无")}<br>
            <b>推荐理由：</b>{item.get("reason", "暂无")}<br>
            <b>优先阅读：</b>{item.get("reading_focus", "暂无")}
            """,
            [f"书单编号 {item.get('id', '暂无')}"],
        )


def build_markdown_summary(strategy: dict[str, Any]) -> str:
    form = st.session_state.form_data
    lines = [
        "# 沟通策略 AI Agent 输出",
        "",
        "## 情境",
        f"- 沟通对象：{form.get('target', '')}",
        f"- 沟通目的：{form.get('purpose', '')}",
        f"- 沟通场景：{form.get('scene', '')}",
        f"- 希望达成：{form.get('expected_result', '')}",
        "",
        "## 分析简报",
        strategy.get("brief", ""),
        "",
        "## 开场话术",
    ]
    for item in strategy.get("talking_points", []):
        principles = " + ".join(as_list(item.get("principles")))
        lines.extend(["", f"### {item.get('label', '话术')}", f"- 原则：{principles}", item.get("text", "")])

    lines.extend(["", "## 预案备选"])
    for item in strategy.get("contingencies", []):
        lines.extend(
            [
                "",
                f"### {item.get('likely_response', '可能反应')}",
                f"- 策略：{item.get('response_strategy', '')}",
                f"- 话术：{item.get('reply', '')}",
            ]
        )

    lines.extend(["", "## 情绪降温话术", strategy.get("cool_down", ""), "", "## 下一步准备"])
    for item in as_list(strategy.get("next_steps")):
        lines.append(f"- {item}")

    applications = strategy.get("theory_applications", [])
    if applications:
        lines.extend(["", "## 理论依据"])
        for item in applications:
            evidence = "；".join(as_list(item.get("evidence")))
            lines.extend(
                [
                    "",
                    f"### {item.get('theory_name', '理论')}",
                    f"- 观察线索：{evidence}",
                    f"- 审慎推断：{item.get('inference', '')}",
                    f"- 沟通动作：{item.get('action', '')}",
                    f"- 话术连接：{item.get('script_link', '')}",
                    f"- 使用边界：{item.get('boundary', '')}",
                ]
            )

    books = strategy.get("recommended_books", [])
    if books:
        lines.extend(["", "## 延伸阅读"])
        for item in books:
            lines.extend(
                [
                    "",
                    f"### 《{item.get('title', '未命名书籍')}》",
                    f"- 书单编号：{item.get('id', '')}",
                    f"- 作者：{item.get('author', '')}",
                    f"- 推荐理由：{item.get('reason', '')}",
                    f"- 优先阅读：{item.get('reading_focus', '')}",
                ]
            )

    if st.session_state.rehearsal_history:
        lines.extend(["", "## 演练记录"])
        for idx, turn in enumerate(st.session_state.rehearsal_history, 1):
            lines.extend(
                [
                    "",
                    f"### 第 {idx} 轮",
                    f"- 对方反应：{turn['reaction']}",
                    f"- 建议回应：{turn['reply']}",
                    f"- 理论依据：{turn.get('theory_basis', '')}",
                    f"- 验证问题：{turn.get('verification_question', '')}",
                    f"- 风险提示：{turn['risk']}",
                ]
            )
    return "\n".join(lines)


def summary_page() -> None:
    strategy = require_strategy()
    if not strategy:
        return

    st.subheader("结果汇总")
    markdown = build_markdown_summary(strategy)
    st.text_area("最终版 Markdown", markdown, height=560)
    st.download_button(
        "下载 Markdown",
        markdown,
        file_name="沟通策略AI_Agent输出.md",
        mime="text/markdown",
        use_container_width=True,
    )
    with st.expander("查看原始 JSON"):
        st.code(json.dumps(strategy, ensure_ascii=False, indent=2), language="json")


def main() -> None:
    inject_css()
    init_state()
    sidebar()

    page = st.session_state.page
    if page == "情境填写":
        situation_page()
    elif page == "智能诊断":
        diagnosis_page()
    elif page == "理论依据":
        theory_page()
    elif page == "话术包":
        talking_points_page()
    elif page == "延伸阅读":
        books_page()
    elif page == "演练":
        rehearsal_page()
    elif page == "结果汇总":
        summary_page()


if __name__ == "__main__":
    main()
