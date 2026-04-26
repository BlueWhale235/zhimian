import json
from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI


class AIConfigError(RuntimeError):
    pass


class AIServiceError(RuntimeError):
    pass


AI_TIMEOUT_SECONDS = 120.0


def _client(settings: dict[str, str]) -> tuple[AsyncOpenAI, str]:
    api_key = settings.get("api_key", "").strip()
    model = settings.get("model", "").strip()
    base_url = settings.get("base_url", "").strip() or "https://api.openai.com/v1"
    if not api_key or not model:
        raise AIConfigError("请先在系统设置中配置 LLM API Key 和模型名称。")
    return AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=AI_TIMEOUT_SECONDS), model


async def chat_text(settings: dict[str, str], messages: list[dict[str, str]]) -> str:
    client, model = _client(settings)
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


async def chat_json(settings: dict[str, str], messages: list[dict[str, str]], fallback: dict[str, Any]) -> dict[str, Any]:
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
                "content": f"请从以下 JD 中提取 skills、responsibilities、keywords、seniority：\n{jd_text}",
            },
        ],
        fallback,
    )


async def generate_question(
    settings: dict[str, str],
    *,
    mode: str,
    pressure_level: int,
    resume_hint: str,
    jd_hint: str,
    history: list[dict[str, str]],
    interviewer_prompt: str = "",
) -> str:
    style = (
        "温和、引导式，关注候选人与岗位的初步匹配度。"
        if mode == "normal"
        else f"""压力强度 {pressure_level}/5，风格如下：
        ## Role
            你是一位拥有15年行业经验顶级大区经理。你现在正在主持一场决定候选人去留的终轮压力面试。

            ## Persona
            - **语气**：冷淡、专业、不带感情色彩。严禁说“很好”、“没关系”、“我理解”等安抚性词语。
            - **态度**：对平庸的答案零容忍，习惯于打断虚伪的陈述，直戳逻辑漏洞。
            - **目标**：通过不断的追问探寻候选人的能力边界，测试其在被质疑时的情绪控制能力和逻辑自洽性。

            ## Interview Tactics (面试策略)
            1. **深度质疑**：当候选人描述项目成就时，立即质疑其真实贡献度（例如：“这难道不是平台的功劳吗？换个人来做是不是结果也一样？”）。
            2. **数据逼问**：如果候选人给出的描述是模糊的（如“大幅提升”、“显著优化”），必须强制要求其给出具体量化数据和推导逻辑。
            3. **极端假设**：提出“如果项目失败了”、“如果预算砍掉50%”、“如果团队全员离职”等极端场景，观察候选人的应变。
            4. **否定式追问**：在候选人回答完后，使用类似“我觉得你的逻辑站不住脚”、“这听起来太理想化了”作为开头，强制其进行二次辩护。
            5. **打破平衡**：故意揪住简历中的一个小瑕疵（如空窗期、技术栈陈旧、项目规模小）反复攻击。

            ## Constraints (行为约束)
            - 每次只提一个问题，且问题必须简短、有力、具有攻击性。
            - 严禁表现出被说服的样子，即便候选人回答得不错，也要寻找下一个切入点继续质疑。
            - 始终结合用户提供的【简历内容】和【目标JD】进行针对性攻击。

            ## Initialization
            1. 首先，你需要根据用户提供的【简历】和【JD】，用一句话指出该候选人最致命的“弱点”或“不匹配点”作为开场，语气要生硬。
            2. 然后，直接抛出第一个具有挑战性的问题。
        """
    )
    system_prompt = interviewer_prompt.strip() or f"你是中文招聘者，一个回合对话只提出一个问题。风格：{style}"
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": f"简历信息：{resume_hint}\nJD 信息：{jd_hint}\n历史对话：{history}\n请生成下一道面试问题。",
        },
    ]
    return await chat_text(settings, messages)


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
    )
