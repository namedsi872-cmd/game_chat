
from llm import ask_llm
from memory import RoleMemoryManager
from config import APP_NAME, DEFAULT_ROLE, MAX_MESSAGES, EXIT_COMMANDS, DEFAULT_ROLE_NAME
# from prompts.yagami_light import SYSTEM_PROMPT
from importlib import import_module
from role_loader import get_role_prompt





def main():
    
    SYSTEM_PROMPT = get_role_prompt(DEFAULT_ROLE)
    current_prompt = SYSTEM_PROMPT
    role_name = DEFAULT_ROLE_NAME
    role_memory_manager = RoleMemoryManager(max_messages=MAX_MESSAGES)


    print(f"{APP_NAME}已启动。")
    print("输入 exit、quit 或 退出 可以结束对话。\n输入数字1可以切换角色。")

    while True:
        print("如果要清除11历史记录，请输入 clear。")
        user_input = input("你：").strip()

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print(f"{APP_NAME}已结束。")
            break
        if user_input == "1":
            print("请输入角色名称：1. 夜神月 2. 其他角色")
            role_input = input("角色：").strip()
            role_name = role_input
            current_prompt = get_role_prompt(role_input)
            print(f"已切换到角色：{role_input}")
            continue
        role_memory = role_memory_manager.get_memory_for_role(role_name)
        if user_input == "clear":
            role_memory_manager.clear_memory_for_role(role_name)
            print(f"{role_name}历史记录已清除。")
            continue

        role_memory.add_user_message(user_input)

        # 这里取出历史记录
        history = role_memory.get_messages()

        try:
           # 这里把历史也传给模型
            reply = ask_llm(current_prompt, history)

            # 这里保存模型回复
            role_memory.add_ai_message(reply)
            print(f"{role_name}：{reply}")
        except Exception as e:
            print(f"程序出错了：{e}")


if __name__ == "__main__":
    main()