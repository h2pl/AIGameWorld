"""领域模型基类 / Domain model base class——所有领域模型共享的字段."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """所有领域模型的基类，统一携带 world_id + ext_json."""

    model_config = ConfigDict(extra="forbid")

    world_id: str = ""
    ext_json: str = "{}"
