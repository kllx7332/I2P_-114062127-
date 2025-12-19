from pygame import Rect
from .settings import GameSettings
from dataclasses import dataclass
from enum import Enum
from typing import overload, TypedDict, Protocol

MouseBtn = int
Key = int

Direction = Enum('Direction', ['UP', 'DOWN', 'LEFT', 'RIGHT', 'NONE'])

@dataclass
class Position:
    x: float
    y: float
    
    def copy(self):
        return Position(self.x, self.y)
        
    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        
@dataclass
class PositionCamera:
    x: int
    y: int
    
    def copy(self):
        return PositionCamera(self.x, self.y)
        
    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)
        
    def transform_position(self, position: Position) -> tuple[int, int]:
        return (int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_position_as_position(self, position: Position) -> Position:
        return Position(int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_rect(self, rect: Rect) -> Rect:
        return Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

@dataclass
class Teleport:
    pos: Position
    destination: str
    target_pos: Position | None = None
    
    @overload
    def __init__(self, x: int, y: int, destination: str, target_x: int = None, target_y: int = None) -> None: ...
    @overload
    def __init__(self, pos: Position, destination: str, target_pos: Position = None) -> None: ...

    def __init__(self, *args, **kwargs):
        if isinstance(args[0], Position):
            self.pos = args[0]
            self.destination = args[1]
            self.target_pos = args[2] if len(args) > 2 else None
        else:
            x, y, dest = args[0], args[1], args[2]
            self.pos = Position(x, y)
            self.destination = dest
            if len(args) > 4:
                self.target_pos = Position(args[3], args[4])
            else:
                self.target_pos = None
    
    def to_dict(self):
        result = {
            "x": self.pos.x // GameSettings.TILE_SIZE,
            "y": self.pos.y // GameSettings.TILE_SIZE,
            "destination": self.destination
        }
        if self.target_pos:
            result["target_x"] = self.target_pos.x // GameSettings.TILE_SIZE
            result["target_y"] = self.target_pos.y // GameSettings.TILE_SIZE
        return result
    
    @classmethod
    def from_dict(cls, data: dict):
        x = data["x"] * GameSettings.TILE_SIZE
        y = data["y"] * GameSettings.TILE_SIZE
        dest = data["destination"]
        if "target_x" in data and "target_y" in data:
            target_x = data["target_x"] * GameSettings.TILE_SIZE
            target_y = data["target_y"] * GameSettings.TILE_SIZE
            tp = cls(x, y, dest, target_x, target_y)
            return tp
        return cls(x, y, dest)
    
class Monster(TypedDict, total=False):
    name: str
    hp: int
    max_hp: int
    level: int
    sprite_path: str
    attribute: str
    atk: int
    # Note: 'def' field is accessed as monster['def'] in code

class Item(TypedDict):
    name: str
    count: int
    sprite_path: str