"""Service layer: State ↔ Engine glue / Service 层：State ↔ Engine 胶水。

├── dm_service.py           — Phase 1 & 6: dm_create / dm_narrate
├── world_service.py        — Phase 2: world_update
├── character_service.py    — Phase 3: pc_decide / actor_decide
├── state_update_service.py — Phase 5: state_update
├── combat_service.py       — Phase 4: combat
├── dialogue_service.py     — Phase 4: dialogue
├── exploration_service.py  — Phase 4: exploration
├── quest_service.py        — Phase 4: quest
├── reflection_service.py   — Phase 7: reflect
└── summarizer_service.py   — Phase 7: summarize

Layer       | Responsibility
------------|------------------------------------------------
Graph       | Orchestrate subgraphs (graph/graph.py)
Subgraph    | Encapsulate phase flow (graph/subgraphs/)
Service     | Read/Write State, convert params, call Engine (services/)
Engine      | Business logic, LLM, prompts (engine/)
Tool/Repo   | Database, vectors, external APIs (storage/, pack/)
"""

from .dm_service import dm_create, dm_narrate
from .world_service import world_update
from .character_service import pc_decide, actor_decide
from .combat_service import combat
from .dialogue_service import dialogue
from .exploration_service import exploration
from .quest_service import quest
from .state_update_service import state_update
from .reflection_service import reflect
from .summarizer_service import summarize
