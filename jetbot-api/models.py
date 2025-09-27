from pydantic import BaseModel

# Pydantic Models
class WebSocketMessage(BaseModel):
    image: str
    left_motor: float
    right_motor: float
