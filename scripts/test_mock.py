"""Test mock data module."""
from src.llm.mock_data import DATASETS, get_mock
from src.schemas.llm_output import DMOutput, DMNarrativeSchema, CharacterActionSchema

print("datasets:", list(DATASETS.keys()))

# test dm_create
data = get_mock("dm_create", "tavern")
m = DMOutput(**data)
print("dm_create:", m.plot_brief)

# test dm_narrate
data = get_mock("dm_narrate", "tavern")
m = DMNarrativeSchema(**data)
print("dm_narrative:", m.narrative[:50], "...")

# test pc_decision
data = get_mock("pc_decision", "tavern")
m = CharacterActionSchema(**data)
print("pc_decision:", m.action_type, m.target_id)

# test combat dataset
data = get_mock("dm_create", "combat")
m = DMOutput(**data)
print("combat:", m.plot_brief)

# test unknown dataset → fallback to default
data = get_mock("dm_create", "unknown")
m = DMOutput(**data)
print("default:", m.plot_brief)

print("All OK")
