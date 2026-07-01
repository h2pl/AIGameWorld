"""世界 / World."""

from pydantic import BaseModel


class World(BaseModel):
    id: str
    name: str
    pack_id: str
    description: str = ""
