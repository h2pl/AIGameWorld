"""Node layer: State <-> Service glue / Node 层：State ↔ Service 胶水。

├── dm_nodes.py           — Phase 1 & 6: DM create + narrate
├── world_nodes.py        — Phase 2: WorldEngine
├── character_nodes.py    — Phase 3: PC + Actor decision
├── combat_nodes.py       — Phase 4: CombatEngine
├── dialogue_nodes.py     — Phase 4: DialogueEngine
├── exploration_nodes.py  — Phase 4: ExplorationEngine
├── quest_nodes.py        — Phase 4: QuestEngine
├── reflection_nodes.py   — Phase 7: CharacterReflection
└── summarizer_nodes.py   — Phase 7: StorySummarizer

Layer       | Responsibility
------------|------------------------------------------------
Graph       | Orchestrate subgraphs (graph/graph.py)
Subgraph    | Encapsulate phase flow (graph/subgraphs/)
Node        | Read/Write State, call Service (nodes/)  ← this layer
Service     | Business logic, LLM, prompts (engine/)
Tool/Repo   | Database, vectors, external APIs (storage/, pack/)
"""
