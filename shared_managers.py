from config import MAX_MESSAGES
from memory import RoleMemoryManager, LongTermMemory


role_memory_manager = RoleMemoryManager(MAX_MESSAGES)
long_term_memory_manager = LongTermMemory(MAX_MESSAGES)
