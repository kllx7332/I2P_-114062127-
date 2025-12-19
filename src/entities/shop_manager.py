from __future__ import annotations
import pygame
from typing import override

from .entity import Entity
from src.sprites import Sprite, Animation
from src.core import GameManager
from src.core.services import input_manager
from src.utils import GameSettings, Direction, Position, PositionCamera


class ShopManager(Entity):
    interaction_sign: Sprite
    can_interact: bool
    interaction_distance: int

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        facing: Direction = Direction.DOWN,
        interaction_distance: int = 1,
    ) -> None:
        super().__init__(x, y, game_manager)
        # 使用 ow3.png 替換默認的動畫
        self.animation = Animation(
            "character/ow3.png", ["down", "left", "right", "up"], 4,
            (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        )
        self.animation.update_pos(self.position)
        self._set_direction(facing)
        self.interaction_distance = interaction_distance
        # 交互提示符號
        self.interaction_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.interaction_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.can_interact = False

    @override
    def update(self, dt: float) -> None:
        self._check_player_nearby()
        if self.can_interact and input_manager.key_pressed(pygame.K_SPACE):
            self._open_shop()
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.can_interact:
            self.interaction_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            interaction_rect = self._get_interaction_rect()
            if interaction_rect is not None:
                pygame.draw.rect(screen, (0, 255, 0), camera.transform_rect(interaction_rect), 1)

    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")

    def _get_interaction_rect(self) -> pygame.Rect | None:
        '''
        Create hitbox to detect player proximity for interaction in front of the shop manager
        Returns a rectangle representing the interaction area (2 tiles in front)
        '''
        if self.interaction_distance is None or self.interaction_distance <= 0:
            return None
        
        tile_size = GameSettings.TILE_SIZE
        interaction_tiles = 2  # 前方兩格
        
        x = self.position.x
        y = self.position.y
        
        # 根據面朝方向創建前方的互動區域
        if self.direction == Direction.UP:
            # 面朝上 - 互動區域在上方
            return pygame.Rect(x, y - (tile_size * interaction_tiles), tile_size, tile_size * interaction_tiles)
        elif self.direction == Direction.DOWN:
            # 面朝下 - 互動區域在下方
            return pygame.Rect(x, y + tile_size, tile_size, tile_size * interaction_tiles)
        elif self.direction == Direction.LEFT:
            # 面朝左 - 互動區域在左方
            return pygame.Rect(x - (tile_size * interaction_tiles), y, tile_size * interaction_tiles, tile_size)
        elif self.direction == Direction.RIGHT:
            # 面朝右 - 互動區域在右方
            return pygame.Rect(x + tile_size, y, tile_size * interaction_tiles, tile_size)
        
        return None

    def _check_player_nearby(self) -> None:
        player = self.game_manager.player
        if player is None:
            self.can_interact = False
            return
        
        interaction_rect = self._get_interaction_rect()
        if interaction_rect is None:
            self.can_interact = False
            return
        
        # Check if player's hitbox intersects with interaction rectangle
        player_rect = player.animation.rect
        if interaction_rect.colliderect(player_rect):
            self.can_interact = True
            # Update interaction sign position above shop manager
            self.interaction_sign.update_pos(Position(
                self.position.x + GameSettings.TILE_SIZE // 4, 
                self.position.y - GameSettings.TILE_SIZE // 2
            ))
        else:
            self.can_interact = False

    def _open_shop(self) -> None:
        '''
        Open the shop interface
        '''
        # Trigger the shop overlay in game_scene
        from src.core.services import scene_manager
        current_scene = scene_manager._current_scene
        if hasattr(current_scene, 'on_shop_click'):
            current_scene.on_shop_click()

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "ShopManager":
        facing_val = data.get("facing", "DOWN")
        facing: Direction = Direction.DOWN
        if isinstance(facing_val, str):
            facing = Direction[facing_val]
        elif isinstance(facing_val, Direction):
            facing = facing_val
        
        interaction_distance = data.get("interaction_distance", 1)
        
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            facing,
            interaction_distance,
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["facing"] = self.direction.name
        base["interaction_distance"] = self.interaction_distance
        return base
