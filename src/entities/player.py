from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Logger, Direction
from src.core import GameManager
import math
from typing import override

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager
    teleport_cooldown: float = 0.0

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)
        self.teleport_cooldown = 0.0

    @override
    def update(self, dt: float) -> None:
        # Update teleport cooldown
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= dt
        
        dis = Position(0, 0)

        if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
            dis.x -= 1
        if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
            dis.x += 1
        if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
            dis.y -= 1
        if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
            dis.y += 1
        
        # Update direction based on input
        if dis.x != 0 or dis.y != 0:
            if abs(dis.y) > abs(dis.x):  # Vertical movement priority
                if dis.y < 0:
                    self.direction = Direction.UP
                else:
                    self.direction = Direction.DOWN
            else:  # Horizontal movement
                if dis.x < 0:
                    self.direction = Direction.LEFT
                else:
                    self.direction = Direction.RIGHT
            # Switch animation based on direction
            self.animation.switch(self.direction.name.lower())
        
        # Normalize the movement so diagonal speed isn't faster
        length = math.hypot(dis.x, dis.y)  # sqrt(x^2 + y^2)
        if length > 0:
            dis.x /= length
            dis.y /= length

        # Apply speed and delta time
        dis.x *= self.speed * dt
        dis.y *= self.speed * dt

        # Update X, check collision
        self.position.x += dis.x
        rect_x= pg.Rect(self.position.x, self.position.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)

        if self.game_manager.check_collision(rect_x):
            self.position.x=self._snap_to_grid(self.position.x)


        # Update Y, check collision
        self.position.y += dis.y
        rect_y = pg.Rect(self.position.x, self.position.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)

        if self.game_manager.check_collision(rect_y):
            self.position.y=self._snap_to_grid(self.position.y)


        # Check teleportation (only if cooldown expired)
        if self.teleport_cooldown <= 0:
            tp = self.game_manager.current_map.check_teleport(self.position)
            if tp:
                self.game_manager.switch_map(tp.destination, tp.target_pos)
                self.teleport_cooldown = 0.5  # 0.5 second cooldown

        super().update(dt)
        


    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)