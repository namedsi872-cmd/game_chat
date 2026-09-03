from importlib import import_module
from pathlib import Path
from typing import Optional

ROLE_MAP = {
    "yagami_light": "夜神月",
    "mihaisha": "弥海砂",
    "other_role": "其他角色",
}

DISPLAY_TO_ROLE = {
    "夜神月": "yagami_light",
    "弥海砂": "mihaisha",
    "其他角色": "other_role",
}

KNOWLEDGE_ROOT = Path(__file__).resolve().parent / "knowledge"

GAME_MAP = {
    "dwrg": "第五人格",
    "sister_weake": "孱弱的姐妹",
}

DISPLAY_TO_GAME = {
    "dwrg": "dwrg",
    "identity_v": "dwrg",
    "Identity V": "dwrg",
    "第五人格": "dwrg",


    "sister_weake": "sister_weake",
    "孱弱的姐妹": "sister_weake",
    
}


def get_role_prompt(role_name):
    if role_name in DISPLAY_TO_ROLE:
        role_name = DISPLAY_TO_ROLE[role_name]

    prompt_module = import_module(f"prompts.{role_name}")
    return prompt_module.SYSTEM_PROMPT


def all_role_name():
    return ROLE_MAP


def normalize_role_name(role_name: str) -> str:
    if role_name in DISPLAY_TO_ROLE:
        return DISPLAY_TO_ROLE[role_name]
    return role_name
def get_role_display_name(role_name: str) -> str:
    role_name = normalize_role_name(role_name)
    return ROLE_MAP.get(role_name, role_name)


def normalize_game_name(game_name: Optional[str]) -> Optional[str]:
    if game_name is None:
        return None

    game_name = game_name.strip()
    if not game_name:
        return None

    return DISPLAY_TO_GAME.get(game_name, game_name)


def get_game_display_name(game_name: Optional[str]) -> str:
    normalized = normalize_game_name(game_name)
    if normalized is None:
        return "纯聊天"

    return GAME_MAP.get(normalized, normalized)


def get_game_aliases(game_name: Optional[str]) -> list[str]:
    normalized = normalize_game_name(game_name)
    if normalized is None:
        return []

    aliases = {normalized}
    for alias, code in DISPLAY_TO_GAME.items():
        if code == normalized:
            aliases.add(alias)

    return sorted(aliases)


def get_knowledge_base_dir(game_name: Optional[str]) -> Optional[Path]:
    normalized = normalize_game_name(game_name)
    if normalized is None:
        return None

    return KNOWLEDGE_ROOT / normalized / "raw"
