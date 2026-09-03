from llm import ask_llm


def build_intent_prompt(message: str, active_mode: str = "") -> str:
    return f"""
你是一个“对话模式判断器”，负责为智能体判断当前用户输入应该进入哪一种模式。

当前已有模式：
{active_mode if active_mode else "无"}

可选模式只有四种：
- chat：普通聊天、轻互动、身份确认、记忆确认、情绪表达、陪伴、简单问答
- training：明确请求训练建议、练习方法、提升方案、打法分析、角色训练
- review：明确请求复盘某一局、某次操作、某段对局过程，定位问题并分析原因
- draw：明确请求绘图、作图、生成图像、设计图像内容

判定原则：
1. 如果用户是在确认“你记不记得我”“我是谁”“我叫什么”“你知道我在练什么吗”这类内容，优先判为 chat，不要因为出现旧记忆主题词就误判成 training。
2. 如果用户只是随口提到某个角色、某个主题，但没有明确请求训练建议、训练计划、打法指导，也优先判为 chat。
3. 只有当用户明确表达“我要练”“帮我训练”“给我方案”“怎么提升”“怎么练习”“帮我分析打法”时，才判为 training。
4. 只有当用户明确表达“帮我复盘这局”“分析我这波哪里错了”“回看这段操作”时，才判为 review。
5. 如果你不确定，默认判为 chat，不要激进地判成 training 或 review。
6. 当前已有模式只作为弱参考，不能因为之前在 training，就把当前一句普通聊天也硬判成 training。
7. 只有当用户当前这句话本身明显延续训练任务时，才继续保持 training。

请严格只输出下面三行，不要输出任何解释性废话：

intent: chat 或 training 或 review 或 draw
final_mode: chat 或 training 或 review 或 draw
reason: 一句简短中文原因

用户输入：
{message}
"""


def router_intent(message: str, active_mode: str = "") -> dict:
    prompt = build_intent_prompt(message, active_mode)
    result = ask_llm(prompt, [])
    return parse_intent_result(result.strip())


def parse_intent_result(result: str) -> dict:
    intent = "chat"
    final_mode = "chat"
    reason = ""

    for line in result.splitlines():
        if line.startswith("intent:"):
            intent = line.split(":", 1)[1].strip()
        elif line.startswith("final_mode:"):
            final_mode = line.split(":", 1)[1].strip()
        elif line.startswith("reason:"):
            reason = line.split(":", 1)[1].strip()

    if intent not in {"chat", "training", "review", "draw"}:
        intent = "chat"
    if final_mode not in {"chat", "training", "review", "draw"}:
        final_mode = "chat"

    return {
        "intent": intent,
        "final_mode": final_mode,
        "reason": reason,
    }
