from pydantic import BaseModel
from typing import Optional

# Pydantic Models

class RobotControlMessage(BaseModel):
    status: str
    speed: Optional[float] = None
    duration: Optional[float] = None


class WebSocketMessage(BaseModel):
    image: str
    left_motor: float
    right_motor: float
    control: Optional[RobotControlMessage] = None

