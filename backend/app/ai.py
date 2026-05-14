import json
from collections.abc import AsyncIterator
from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI


class AIConfigError(RuntimeError):
    pass


class AIServiceError(RuntimeError):
    pass


AI_TIMEOUT_SECONDS = 120.0


def _client(settings: dict[str, str], model_key: str = "model") -> tuple[AsyncOpenAI, str]:
    api_key = settings.get("api_key", "").strip()
    model = (settings.get(model_key, "") or settings.get("model", "")).strip()
    base_url = settings.get("base_url", "").strip() or "https://api.openai.com/v1"
    if not api_key or not model:
        raise AIConfigError("请先在系统设置中配置 LLM API Key 和模型名称。")
    return AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=AI_TIMEOUT_SECONDS), model


async def chat_text(settings: dict[str, str], messages: list[dict[str, str]], model_key: str = "model") -> str:
    client, model = _client(settings, model_key)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1200,
        )
        return response.choices[0].message.content or ""
    except APITimeoutError as exc:
        raise AIServiceError("模型响应超时，请稍后重试或调低上下文长度。") from exc
    except APIConnectionError as exc:
        raise AIServiceError("无法连接模型服务，请检查 API 地址、网络或本地模型服务状态。") from exc


async def chat_text_stream(settings: dict[str, str], messages: list[dict[str, str]], model_key: str = "model") -> AsyncIterator[str]:
    client, model = _client(settings, model_key)
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1200,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except APITimeoutError as exc:
        raise AIServiceError("模型流式响应超时，请稍后重试或调低上下文长度。") from exc
    except APIConnectionError as exc:
        raise AIServiceError("无法连接模型流式服务，请检查 API 地址、网络或本地模型服务状态。") from exc


async def extract_resume_text(settings: dict[str, str], local_text: str, image_data_urls: list[str]) -> str:
    client, model = _client(settings, "resume_extract_model")
    instruction = (
        "请提取简历中的可见文字，尽量保持原始顺序、原始措辞和条目结构。"
        "不要总结，不要归纳，不要补充，不要评价，不要把内容改写成第三人称。"
        "只输出简历文字本身。"
    )
    content: str | list[dict[str, Any]] = instruction
    if local_text.strip():
        content = f"{instruction}\n\n本地 PDF 文本抽取结果如下，请在不改写内容的前提下整理明显的断行问题：\n{local_text[:30000]}"
    if image_data_urls:
        image_content: list[dict[str, Any]] = [{"type": "text", "text": content if isinstance(content, str) else instruction}]
        for url in image_data_urls:
            image_content.append({"type": "image_url", "image_url": {"url": url}})
        content = image_content
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是简历OCR与文字提取助手。你的输出必须忠实于简历原文。",
                },
                {"role": "user", "content": content},
            ],
            temperature=0.1,
            max_tokens=4000,
        )
        return (response.choices[0].message.content or "").strip()
    except APITimeoutError as exc:
        raise AIServiceError("简历 AI 提取超时，请稍后重试或换用更快的模型。") from exc
    except APIConnectionError as exc:
        raise AIServiceError("无法连接模型服务，请检查 API 地址、网络或本地模型服务状态。") from exc
    except Exception as exc:
        raise AIServiceError("简历 AI 提取失败。若是扫描件，请确认当前模型支持图片理解；否则可直接使用本地提取文本。") from exc


async def chat_json(settings: dict[str, str], messages: list[dict[str, str]], fallback: dict[str, Any], model_key: str = "model") -> dict[str, Any]:
    try:
        text = await chat_text(
            settings,
            messages
            + [
                {
                    "role": "system",
                    "content": "只返回严格 JSON，不要 Markdown，不要代码块。",
                }
            ],
            model_key=model_key,
        )
        return json.loads(text)
    except AIConfigError:
        raise
    except AIServiceError:
        raise
    except Exception:
        return fallback


async def extract_jd_requirements(settings: dict[str, str], jd_text: str) -> dict[str, Any]:
    fallback = {
        "skills": [],
        "responsibilities": [],
        "keywords": [],
        "seniority": "未识别",
    }
    return await chat_json(
        settings,
        [
            {
                "role": "system",
                "content": "你是招聘 JD 分析助手，提取岗位能力画像。",
            },
            {
                "role": "user",
                "content": f"请从以下 JD 中提取 skills（skills不多于6个）、responsibilities、keywords、seniority：\n{jd_text}",
            },
        ],
        fallback,
        model_key="jd_model",
    )


def _response_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text
    data = response.model_dump() if hasattr(response, "model_dump") else {}
    texts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if text:
                texts.append(text)
    return "\n".join(texts)


async def extract_jd_from_url(settings: dict[str, str], url: str) -> dict[str, Any]:
    client, model = _client(settings, "url_extract_model")
    responses = getattr(client, "responses", None)
    if responses is None:
        raise AIServiceError("当前 openai SDK 不支持 Responses API，请升级 openai 包。")
    try:
        response = await responses.create(
            model=model,
            input=(
                "请打开并分析这个招聘页面 URL，抽取结构化 JD 信息。"
                "只返回严格 JSON，不要 Markdown。JSON 字段："
                "{title:string, company:string, content:string, company_background:string}。"
                "content 应该是职位描述和任职要求的完整中文整理；"
                "company_background 是公司业务、产品、文化、行业、规模等背景简介。"
                f"\nURL: {url}"
            ),
            tools=[
                {"type": "web_search"},
                {"type": "web_extractor"},
                {"type": "code_interpreter"},
            ],
            extra_body={"enable_thinking": True},
        )
        text = _response_output_text(response)
        return json.loads(text)
    except AIServiceError:
        raise
    except APITimeoutError as exc:
        raise AIServiceError("网页提取超时，请稍后重试或手动粘贴 JD。") from exc
    except APIConnectionError as exc:
        raise AIServiceError("无法连接模型网页工具服务，请检查 API 地址、Key 或模型能力。") from exc
    except Exception as exc:
        raise AIServiceError("网页提取失败。请确认模型支持 Responses API 和 web_search/web_extractor 工具。") from exc


async def generate_question(
    settings: dict[str, str],
    *,
    mode: str,
    pressure_level: int,
    resume_hint: str,
    jd_hint: str,
    history: list[dict[str, str]],
    interviewer_prompt: str = "",
    company_background: str = "",
    current_round: int = 0,
    max_rounds: int = 0,
    is_final_turn: bool = False,
) -> str:
    return await chat_text(settings, build_question_messages(
        mode=mode,
        pressure_level=pressure_level,
        resume_hint=resume_hint,
        jd_hint=jd_hint,
        history=history,
        interviewer_prompt=interviewer_prompt,
        company_background=company_background,
        current_round=current_round,
        max_rounds=max_rounds,
        is_final_turn=is_final_turn,
    ), model_key="interview_model")


async def stream_question(
    settings: dict[str, str],
    *,
    mode: str,
    pressure_level: int,
    resume_hint: str,
    jd_hint: str,
    history: list[dict[str, str]],
    interviewer_prompt: str = "",
    company_background: str = "",
    current_round: int = 0,
    max_rounds: int = 0,
    is_final_turn: bool = False,
) -> AsyncIterator[str]:
    messages = build_question_messages(
        mode=mode,
        pressure_level=pressure_level,
        resume_hint=resume_hint,
        jd_hint=jd_hint,
        history=history,
        interviewer_prompt=interviewer_prompt,
        company_background=company_background,
        current_round=current_round,
        max_rounds=max_rounds,
        is_final_turn=is_final_turn,
    )
    async for delta in chat_text_stream(settings, messages, model_key="interview_model"):
        yield delta


def build_question_messages(
    *,
    mode: str,
    pressure_level: int,
    resume_hint: str,
    jd_hint: str,
    history: list[dict[str, str]],
    interviewer_prompt: str = "",
    company_background: str = "",
    current_round: int = 0,
    max_rounds: int = 0,
    is_final_turn: bool = False,
) -> list[dict[str, str]]:
    style = (
        "温和、引导式，关注候选人与岗位的初步匹配度。"
        if mode == "normal"
        else f"""压力强度 {pressure_level}/5，风格：
        你现在扮演从业多年的线下业务大区经理，开展专业型压力面试。
        整体风格：沉稳严肃、极简沟通、没有多余客套，语气冷静克制，不情绪化、不刻意抬杠、不人身否定。
        面试逻辑：
        1.提问直击业务核心，聚焦业绩目标、区域管理、客户谈判、团队协作、突发问题、跨部门协作、抗压兜底等实际工作场景；
        2.用户每回答完一段，你针对回答里的模糊点、漏洞、理想化内容、未落地的部分，进行层层深挖+反向反问；
        3.加快提问节奏，连续递进追问，不给长篇空话套话的空间，逼迫给出具体方案、数据、实际做法；
        4.针对短板、薄弱经历、空白环节主动提问，考验临场应变、问题解决能力和心理抗压；
        5.不刻意反驳，但会持续质疑方案可行性、成本、风险、实际落地难点，模拟管理层真实审视视角；
        6.全程保持职场专业感，不放水、不引导、不鼓励，保持高压但理性的面试氛围。
        现在直接开始正式面试，抛出第一个问题。
        """
    )
    default_prompt = (
        f"你是招聘者，一个回合对话只提出一个问题。压力强度：{pressure_level}/5。风格：{style}"
        if mode == "pressure"
        else f"你是招聘者，一个回合对话只提出一个问题。风格：{style}"
    )
    system_prompt = interviewer_prompt.strip() or default_prompt
    background = company_background.strip() or "未提供"
    round_info = (
        f"当前进度：候选人已完成 {current_round}/{max_rounds} 轮回答。"
        if max_rounds
        else f"当前进度：候选人已完成 {current_round} 轮回答。"
    )
    final_instruction = (
        "\n\n本轮为结束对话。作为面试官，需要对招聘者说最后一条消息："
        "简短总结本场面试感受，指出后续会进入复盘报告，不要再提出新的实质性面试问题，"
        "不要要求候选人继续回答。"
        if is_final_turn
        else ""
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n\n"
                f"{round_info}\n"
                "如果提供了公司背景，请把公司业务、文化、岗位场景自然融入追问，但不要虚构背景之外的信息。"
                f"{final_instruction}"
            ),
        },
        {
            "role": "user",
            "content": f"简历信息：{resume_hint}\nJD 信息：{jd_hint}\n公司背景：{background}\n{round_info}\n历史对话：{history}\n请生成下一道面试问题。",
        },
    ]
    return messages


async def generate_report(settings: dict[str, str], transcript: list[dict[str, str]]) -> dict[str, Any]:
    fallback = {
        "summary": "报告生成失败，请检查模型配置后重试。",
        "star": [],
        "highlights": [],
        "improvements": [],
    }
    return await chat_json(
        settings,
        [
            {
                "role": "system",
                "content": "你是专业中文面试复盘教练，使用 STAR 法则输出结构化反馈。",
            },
            {
                "role": "user",
                "content": (
                    "基于以下面试 transcript 输出 JSON："
                    "{summary:string, star:array, highlights:array长度3, improvements:array长度3}。\n"
                    f"{transcript}"
                ),
            },
        ],
        fallback,
        model_key="report_model",
    )
