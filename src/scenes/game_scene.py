import pygame as pg
from collections import deque
import threading
import time
import random
import string
import math
from src.interface.components import Button
from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.services import sound_manager,scene_manager, input_manager
from src.sprites import Sprite
from src.sprites import Animation
from typing import override
from typing import override, Dict, Tuple
from src.interface.components.chat_overlay import ChatOverlay

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    wild_pokemon_name: str | None
    used_pokemon_names: set[str]
    
    def __init__(self):
        super().__init__()
        # Game Manager - Load from backup (initial state) instead of save file
        manager = GameManager.load("saves/backup.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager
        
        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
            self._chat_overlay = ChatOverlay(
                send_callback=self.online_manager.send_chat,
                get_messages=self.online_manager.get_recent_chat,
            )
        else:
            self.online_manager = None
            self._chat_overlay = None
        self._online_player_animations: Dict[int, Animation] = {}  # Store animations for each online player
        self._chat_bubbles: Dict[int, Tuple[str, str]] = {}
        self._last_chat_id_seen = 0
        self._online_last_pos: Dict[int, Position] = {}  # Track last known positions of online players
        # Wild pokemon tracking
        self.wild_pokemon_name = None
        self.used_pokemon_names = set()
        # Track player position before bush battle
        self.player_pos_before_battle = None
        # remember loaded player position (from save) if any
        if self.game_manager.player:
            self.loaded_player_spawn_pos = self.game_manager.player.position.copy()
        else:
            self.loaded_player_spawn_pos = None
        #ingame_setting_button
        self.ingame_setting_button = Button(
            img_path="UI/button_setting.png",
            img_hovered_path="UI/button_setting_hover.png",
            x=20,
            y=20,
            width=80,
            height=80,
            on_click=self.on_ingame_setting_click
        )
        # bagpack_button (right of ingame_setting_button)
        self.bagpack_button = Button(
            img_path="UI/button_backpack.png",
            img_hovered_path="UI/button_backpack_hover.png",
            x=110,
            y=20,
            width=80,
            height=80,
            on_click=self.on_bagpack_click
        )
        # navigation_button (right of bagpack_button)
        self.navigation_button = Button(
            img_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Button02a_3.png",
            img_hovered_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Button02a_2.png",
            x=200,
            y=20,
            width=80,
            height=80,
            on_click=self.on_navigation_button_click
        )
        # Load letter N image for navigation button
        temp_img = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\N.png").convert()
        # Set both white and light gray as transparent
        for x in range(temp_img.get_width()):
            for y in range(temp_img.get_height()):
                r, g, b, _ = temp_img.get_at((x, y))
                # If pixel is close to white or gray (checkerboard pattern)
                if r > 200 and g > 200 and b > 200:
                    temp_img.set_at((x, y), (255, 255, 255, 0))
        temp_img.set_colorkey((255, 255, 255))
        self.navigation_letter_img = temp_img
        self.overlay_active = False
        self.bagpack_overlay_active = False
        self.shop_overlay_active = False
        self.navigation_overlay_active = False
        # navigation path (list of tile coords)
        self.navigation_path: list[tuple[int,int]] = []
        # Auto navigation state
        self.auto_navigation_active = False
        self.navigation_current_index = 0  # Track which waypoint we're moving to
        self.navigation_final_goal = None  # Track final destination: 'start', 'gym', 'new_world', or None
        self.previous_map_key = self.game_manager.current_map_key if self.game_manager.current_map else None  # Track previous map to detect map changes
        # arrow icon for navigation (used to draw path)
        try:
            self.nav_arrow_img = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_IconPoint01c.png").convert_alpha()
        except Exception:
            self.nav_arrow_img = None
        # Shop item buttons (dynamically created when shop opens)
        self.shop_item_buttons = []
        # Pagination
        self.current_page = 0
        self.items_per_page = 8  # Maximum items to show per page
        #back_button (for setting overlay)
        self.back_button = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 50,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_back_click
        )
        # bagpack_back_button (for bagpack overlay)
        self.bagpack_back_button = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 50,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_bagpack_back_click
        )
        # shop_back_button (for shop overlay)
        self.shop_back_button = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 50,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_shop_back_click
        )
        # navigation_back_button (for navigation overlay)
        self.navigation_back_button = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 50,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_navigation_back_click
        )
        # navigation action buttons (positioned inside overlay during draw)
        self.navigation_start = Button(
            img_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\button_play.png",
            img_hovered_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\button_play_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 100,
            y=GameSettings.SCREEN_HEIGHT // 2,
            width=80,
            height=80,
            on_click=self.on_navigation_start_click
        )
        self.navigation_gym = Button(
            img_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\button_play.png",
            img_hovered_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\button_play_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 + 20,
            y=GameSettings.SCREEN_HEIGHT // 2,
            width=80,
            height=80,
            on_click=self.on_navigation_gym_click
        )
        self.navigation_new_world = Button(
            img_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\button_play.png",
            img_hovered_path=r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\button_play_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 + 140,
            y=GameSettings.SCREEN_HEIGHT // 2,
            width=80,
            height=80,
            on_click=self.on_navigation_new_world_click
        )
        # navigation_back_button (for navigation overlay)
        self.navigation_back_button = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 50,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_navigation_back_click
        )
        # next_page and last_page buttons (for bag and shop overlays)
        self.next_page_button = Button(
            img_path="UI/button_play.png",
            img_hovered_path="UI/button_play_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2,
            y=GameSettings.SCREEN_HEIGHT // 2,
            width=60,
            height=60,
            on_click=self.on_next_page_click
        )
        self.last_page_button = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2,
            y=GameSettings.SCREEN_HEIGHT // 2,
            width=60,
            height=60,
            on_click=self.on_last_page_click
        )
        # checkbox_button (appears above back_button when overlay is active)
        # use Bar05a as unchecked, Bar10a as checked
        self.checkbox_unchecked_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Bar11a.png"
        self.checkbox_checked_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Bar10a.png"
        self.checkbox_button = Button(
            img_path=self.checkbox_unchecked_path,
            img_hovered_path=self.checkbox_unchecked_path,
            x=GameSettings.SCREEN_WIDTH // 2 - 40,
            y=GameSettings.SCREEN_HEIGHT // 2 - 40,
            width=80,
            height=80,
            on_click=self.on_checkbox_click
        )
        self.checkbox_checked = False
        # slider resources and state (will be positioned inside overlay)
        self.slider_track_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_BarFill01f.png"
        self.slider_knob_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_FrameSlot03b.png"
        # load raw images
        try:
            self.slider_track_img = pg.image.load(self.slider_track_path).convert_alpha()
        except Exception:
            self.slider_track_img = None
        try:
            self.slider_knob_img = pg.image.load(self.slider_knob_path).convert_alpha()
        except Exception:
            self.slider_knob_img = None
        self.slider_value = 0.5
        self.slider_dragging = False
        # overlay scale multiplier (used consistently in update/draw)
        self.overlay_scale = 5
        # overlay image
        self.overlay_img = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Frame03a.png").convert_alpha()
        # font for UI labels
        try:
            # make the label font 2x larger (was 28 before)
            self.ui_font = pg.font.SysFont(None, 56)
        except Exception:
            # fallback: create Font when drawing if font module isn't ready yet
            self.ui_font = None
        
        # Save button
        self.save_button = Button(
            img_path="UI/button_save.png",
            img_hovered_path="UI/button_save_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 - 120,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_save_click
        )
        
        # Load button
        self.load_button = Button(
            img_path="UI/button_load.png",
            img_hovered_path="UI/button_load_hover.png",
            x=GameSettings.SCREEN_WIDTH // 2 + 20,
            y=GameSettings.SCREEN_HEIGHT // 2 + 50,
            width=100,
            height=100,
            on_click=self.on_load_click
        )
        
        # Minimap properties
        self.minimap_size = 200  # Size of the minimap in pixels
        self.minimap_padding = 20  # Padding from the top-right corner
        self.minimap_border_width = 3  # Border thickness
    @override
    def on_ingame_setting_click(self):
        self.overlay_active = True
        self.bagpack_overlay_active = False
    
    def on_bagpack_click(self):
        self.bagpack_overlay_active = True
        self.overlay_active = False
        self.shop_overlay_active = False
        self.current_page = 0  # Reset to first page
    
    def on_navigation_button_click(self):
        Logger.info("Navigation button clicked!")
        self.navigation_overlay_active = True
        self.overlay_active = False
        self.bagpack_overlay_active = False
        self.shop_overlay_active = False
    
    def on_navigation_back_click(self):
        self.navigation_overlay_active = False

    def on_navigation_start_click(self):
        Logger.info("Navigation start clicked")
        
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        current_map_name = self.game_manager.current_map.path_name
        
        # 設置最終目標
        self.navigation_final_goal = 'start'
        
        # 如果不在 map.tmx 上，先導航到返回 map.tmx 的傳送點
        if current_map_name != "map.tmx":
            Logger.info(f"Currently on {current_map_name}, navigating to map.tmx teleporter first")
            self._navigate_to_teleporter("map.tmx")
            return
        
        # 在 map.tmx 上，導航到出生點
        self.navigation_path = []
        tile_size = GameSettings.TILE_SIZE
        map_obj = self.game_manager.current_map
        width = map_obj.tmxdata.width
        height = map_obj.tmxdata.height

        start = (self.game_manager.player.position.x // tile_size, self.game_manager.player.position.y // tile_size)
        # Use loaded player position (from save) as goal if available, otherwise use map spawn
        if getattr(self, 'loaded_player_spawn_pos', None) is not None:
            goal = (self.loaded_player_spawn_pos.x // tile_size, self.loaded_player_spawn_pos.y // tile_size)
        else:
            goal = (map_obj.spawn.x // tile_size, map_obj.spawn.y // tile_size)

        # Build blocked set from collision rectangles
        blocked = set()
        for rect in getattr(map_obj, '_collision_map', []):
            bx = rect.x // tile_size
            by = rect.y // tile_size
            blocked.add((bx, by))
        
        # Add NPC positions to blocked set
        for enemy in self.game_manager.current_enemy_trainers:
            ex = int(enemy.position.x // tile_size)
            ey = int(enemy.position.y // tile_size)
            blocked.add((ex, ey))
        for shop in self.game_manager.current_shop_managers:
            sx = int(shop.position.x // tile_size)
            sy = int(shop.position.y // tile_size)
            blocked.add((sx, sy))

        # BFS
        q = deque([start])
        prev: dict[tuple[int,int], tuple[int,int] | None] = {start: None}
        found = False
        while q:
            x, y = q.popleft()
            if (x, y) == goal:
                found = True
                break
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                if (nx, ny) in blocked:
                    continue
                if (nx, ny) in prev:
                    continue
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))

        if not found:
            Logger.info("No path to spawn found")
            return

        # reconstruct path from goal to start
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        self.navigation_path = path
        
        # 啟動自動導航
        if len(self.navigation_path) > 0:
            self.auto_navigation_active = True
            self.navigation_current_index = 0
            self.navigation_overlay_active = False  # 關閉導航覆蓋層
            Logger.info(f"Auto navigation started with {len(self.navigation_path)} waypoints")
        else:
            self.navigation_final_goal = None  # 清除目標如果無法導航

    def on_navigation_gym_click(self):
        Logger.info("Navigation gym clicked")
        
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        current_map_name = self.game_manager.current_map.path_name
        
        # 設置最終目標
        self.navigation_final_goal = 'gym'
        
        # 如果已經在 gym.tmx 上，導航到出生點
        if current_map_name == "gym.tmx":
            Logger.info("Already on gym.tmx, navigating to spawn point")
            self._navigate_to_spawn()
        elif current_map_name == "map.tmx":
            # 在 map.tmx 上，直接導航到 gym 傳送點
            self._navigate_to_teleporter("gym.tmx")
        else:
            # 在其他地圖（new_map），先導航到返回 map.tmx 的傳送點
            Logger.info(f"On {current_map_name}, need to go to map.tmx first")
            self._navigate_to_teleporter("map.tmx")

    def on_navigation_new_world_click(self):
        Logger.info("Navigation new world clicked")
        
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        current_map_name = self.game_manager.current_map.path_name
        
        # 設置最終目標
        self.navigation_final_goal = 'new_world'
        
        # 如果已經在 new_map.tmx 上，導航到出生點
        if current_map_name == "new_map.tmx":
            Logger.info("Already on new_map.tmx, navigating to spawn point")
            self._navigate_to_spawn()
        elif current_map_name == "map.tmx":
            # 在 map.tmx 上，直接導航到 new_map 傳送點
            self._navigate_to_teleporter("new_map.tmx")
        else:
            # 在其他地圖（gym），先導航到返回 map.tmx 的傳送點
            Logger.info(f"On {current_map_name}, need to go to map.tmx first")
            self._navigate_to_teleporter("map.tmx")
    
    
    def _navigate_to_position(self, goal_tile: tuple[int, int]):
        """導航到指定的格子位置"""
        self.navigation_path = []
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        tile_size = GameSettings.TILE_SIZE
        map_obj = self.game_manager.current_map
        width = map_obj.tmxdata.width
        height = map_obj.tmxdata.height
        
        start = (self.game_manager.player.position.x // tile_size, self.game_manager.player.position.y // tile_size)
        goal = goal_tile
        
        # Build blocked set from collision rectangles
        blocked = set()
        for rect in getattr(map_obj, '_collision_map', []):
            bx = rect.x // tile_size
            by = rect.y // tile_size
            blocked.add((bx, by))
        
        # Add NPC positions to blocked set
        for enemy in self.game_manager.current_enemy_trainers:
            ex = int(enemy.position.x // tile_size)
            ey = int(enemy.position.y // tile_size)
            blocked.add((ex, ey))
        for shop in self.game_manager.current_shop_managers:
            sx = int(shop.position.x // tile_size)
            sy = int(shop.position.y // tile_size)
            blocked.add((sx, sy))
        
        # BFS
        q = deque([start])
        prev: dict[tuple[int,int], tuple[int,int] | None] = {start: None}
        found = False
        while q:
            x, y = q.popleft()
            if (x, y) == goal:
                found = True
                break
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                if (nx, ny) in blocked:
                    continue
                if (nx, ny) in prev:
                    continue
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))
        
        if not found:
            Logger.info(f"No path to position {goal} found")
            return
        
        # Reconstruct path from goal to start
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        self.navigation_path = path
        
        # 啟動自動導航
        if len(self.navigation_path) > 0:
            self.auto_navigation_active = True
            self.navigation_current_index = 0
            Logger.info(f"Auto navigation to position {goal} started with {len(self.navigation_path)} waypoints")
    
    def _navigate_to_spawn(self):
        """導航到當前地圖的出生點"""
        self.navigation_path = []
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        tile_size = GameSettings.TILE_SIZE
        map_obj = self.game_manager.current_map
        width = map_obj.tmxdata.width
        height = map_obj.tmxdata.height
        
        start = (self.game_manager.player.position.x // tile_size, self.game_manager.player.position.y // tile_size)
        goal = (map_obj.spawn.x // tile_size, map_obj.spawn.y // tile_size)
        
        # Build blocked set from collision rectangles
        blocked = set()
        for rect in getattr(map_obj, '_collision_map', []):
            bx = rect.x // tile_size
            by = rect.y // tile_size
            blocked.add((bx, by))
        
        # Add NPC positions to blocked set
        for enemy in self.game_manager.current_enemy_trainers:
            ex = int(enemy.position.x // tile_size)
            ey = int(enemy.position.y // tile_size)
            blocked.add((ex, ey))
        for shop in self.game_manager.current_shop_managers:
            sx = int(shop.position.x // tile_size)
            sy = int(shop.position.y // tile_size)
            blocked.add((sx, sy))
        
        # BFS
        q = deque([start])
        prev: dict[tuple[int,int], tuple[int,int] | None] = {start: None}
        found = False
        while q:
            x, y = q.popleft()
            if (x, y) == goal:
                found = True
                break
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                if (nx, ny) in blocked:
                    continue
                if (nx, ny) in prev:
                    continue
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))
        
        if not found:
            Logger.info("No path to spawn found")
            return
        
        # Reconstruct path from goal to start
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        self.navigation_path = path
        
        # 啟動自動導航
        if len(self.navigation_path) > 0:
            self.auto_navigation_active = True
            self.navigation_current_index = 0
            self.navigation_overlay_active = False
            Logger.info(f"Auto navigation to spawn started with {len(self.navigation_path)} waypoints")
        else:
            self.navigation_final_goal = None  # 清除目標如果無法導航
    
    def _navigate_to_teleporter(self, destination_map: str):
        """通用方法：導航到指定目的地的傳送點"""
        self.navigation_path = []
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        # Find teleporter with matching destination
        target_teleporter = None
        for tp in self.game_manager.current_map.teleporters:
            if tp.destination == destination_map:
                target_teleporter = tp
                break
        
        if target_teleporter is None:
            Logger.info(f"No teleporter to {destination_map} found on current map")
            return
        
        tile_size = GameSettings.TILE_SIZE
        map_obj = self.game_manager.current_map
        width = map_obj.tmxdata.width
        height = map_obj.tmxdata.height
        
        start = (self.game_manager.player.position.x // tile_size, self.game_manager.player.position.y // tile_size)
        goal = (target_teleporter.pos.x // tile_size, target_teleporter.pos.y // tile_size)
        
        # Build blocked set from collision rectangles
        blocked = set()
        for rect in getattr(map_obj, '_collision_map', []):
            bx = rect.x // tile_size
            by = rect.y // tile_size
            blocked.add((bx, by))
        
        # Add NPC positions to blocked set
        for enemy in self.game_manager.current_enemy_trainers:
            ex = int(enemy.position.x // tile_size)
            ey = int(enemy.position.y // tile_size)
            blocked.add((ex, ey))
        for shop in self.game_manager.current_shop_managers:
            sx = int(shop.position.x // tile_size)
            sy = int(shop.position.y // tile_size)
            blocked.add((sx, sy))
        
        # BFS
        q = deque([start])
        prev: dict[tuple[int,int], tuple[int,int] | None] = {start: None}
        found = False
        while q:
            x, y = q.popleft()
            if (x, y) == goal:
                found = True
                break
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                if (nx, ny) in blocked:
                    continue
                if (nx, ny) in prev:
                    continue
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))
        
        if not found:
            Logger.info(f"No path to {destination_map} teleporter found")
            return
        
        # Reconstruct path from goal to start
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        self.navigation_path = path
        
        # 啟動自動導航
        if len(self.navigation_path) > 0:
            self.auto_navigation_active = True
            self.navigation_current_index = 0
            self.navigation_overlay_active = False  # 關閉導航覆蓋層
            Logger.info(f"Auto navigation started to {destination_map} with {len(self.navigation_path)} waypoints")
    
    def on_bagpack_back_click(self):
        self.bagpack_overlay_active = False
    
    def on_shop_click(self):
        self.shop_overlay_active = True
        self.overlay_active = False
        self.bagpack_overlay_active = False
        self.current_page = 0  # Reset to first page
        # Initialize shop buttons dynamically
        self._create_shop_buttons()
    
    def on_shop_back_click(self):
        self.shop_overlay_active = False
        # Clear shop buttons when closing
        self.shop_item_buttons = []
    
    def on_next_page_click(self):
        # Calculate total items based on current overlay
        if self.bagpack_overlay_active:
            total_monsters = len(self.game_manager.bag._monsters_data)
            total_items = len(self.game_manager.bag._items_data)
            total = total_monsters + total_items
        elif self.shop_overlay_active:
            total_monsters = len(self.game_manager.shop_list._monsters_data)
            total_items = len(self.game_manager.shop_list._items_data)
            total = total_monsters + total_items
        else:
            return
        
        max_page = max(0, (total - 1) // self.items_per_page)
        if self.current_page < max_page:
            self.current_page += 1
            Logger.info(f"Next page: {self.current_page}")
    
    def on_last_page_click(self):
        if self.current_page > 0:
            self.current_page -= 1
            Logger.info(f"Last page: {self.current_page}")
    
    def on_back_click(self):
        self.overlay_active = False
        self.bagpack_overlay_active = False

    def on_checkbox_click(self):
        # toggle checkbox state
        self.checkbox_checked = not getattr(self, 'checkbox_checked', False)
        # update checkbox_button sprite to reflect checked/unchecked state
        new_path = self.checkbox_checked_path if self.checkbox_checked else self.checkbox_unchecked_path
        # recreate sprites at button size
        self.checkbox_button.img_button_default = Sprite(new_path, (self.checkbox_button.hitbox.width, self.checkbox_button.hitbox.height))
        self.checkbox_button.img_button_hover = Sprite(new_path, (self.checkbox_button.hitbox.width, self.checkbox_button.hitbox.height))
        # ensure current reference points to default (update() may override if hovering)
        self.checkbox_button.img_button = self.checkbox_button.img_button_default
    
    def on_save_click(self):
        # Save the current game state
        self.game_manager.save("saves/game0.json")
        Logger.info("Game saved successfully")
    
    def on_load_click(self):
        # Load the game state from file
        loaded_manager = GameManager.load("saves/game0.json")
        if loaded_manager is not None:
            self.game_manager = loaded_manager
            Logger.info("Game loaded successfully")
        else:
            Logger.warning("Failed to load game")
    
    def _create_shop_buttons(self):
        """Create buttons for each item in the shop"""
        self.shop_item_buttons = []
        # Buttons will be positioned in draw method based on item positions
    
    def on_shop_item_click(self, item_index: int, is_monster: bool):
        """Handle click on a shop item button"""
        # Check if player has enough coins
        coins_item = None
        for bag_item in self.game_manager.bag._items_data:
            if bag_item['name'] == 'Coins':
                coins_item = bag_item
                break
        
        if coins_item is None or coins_item['count'] < 1:
            Logger.info("Not enough coins to purchase!")
            return
        
        if is_monster:
            # Purchase monster from shop_list
            monsters = self.game_manager.shop_list._monsters_data
            if 0 <= item_index < len(monsters):
                monster_data = monsters[item_index].copy()
                self.game_manager.bag._monsters_data.append(monster_data)
                # Deduct 1 coin
                coins_item['count'] -= 1
                Logger.info(f"Purchased monster: {monster_data['name']}, remaining coins: {coins_item['count']}")
        else:
            # Purchase item from shop_list
            # item_index is the adjusted index (total_index - number_of_monsters)
            items = self.game_manager.shop_list._items_data
            monsters = self.game_manager.shop_list._monsters_data
            adjusted_index = item_index - len(monsters)
            
            if 0 <= adjusted_index < len(items):
                shop_item = items[adjusted_index]
                item_name = shop_item['name']
                
                # Check if item already exists in bag
                found = False
                for bag_item in self.game_manager.bag._items_data:
                    if bag_item['name'] == item_name:
                        bag_item['count'] += 1
                        found = True
                        # Deduct 1 coin
                        coins_item['count'] -= 1
                        Logger.info(f"Purchased item: {item_name}, new count: {bag_item['count']}, remaining coins: {coins_item['count']}")
                        break
                
                # If item doesn't exist, add new entry
                if not found:
                    new_item = shop_item.copy()
                    new_item['count'] = 1
                    self.game_manager.bag._items_data.append(new_item)
                    # Deduct 1 coin
                    coins_item['count'] -= 1
                    Logger.info(f"Purchased new item: {item_name}, remaining coins: {coins_item['count']}")

    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        # Only call online_manager.enter() if not already connected
        if self.online_manager and self.online_manager.player_id == -1:
            self.online_manager.enter()
        
        # Clear old online player data to prevent ghost players after returning from battle
        self._online_player_animations.clear()
        self._online_last_pos.clear()
        
        # 檢查是否有待完成的導航目標（在傳送後繼續導航）
        if self.navigation_final_goal and self.game_manager.player and self.game_manager.current_map:
            current_map_name = self.game_manager.current_map.path_name
            Logger.info(f"Continuing navigation to final goal: {self.navigation_final_goal} on map: {current_map_name}")
            
            if self.navigation_final_goal == 'start':
                # 導航到 start（應該已經在 map.tmx 上）
                if current_map_name == "map.tmx":
                    # 使用 loaded_player_spawn_pos 或 spawn
                    tile_size = GameSettings.TILE_SIZE
                    if getattr(self, 'loaded_player_spawn_pos', None) is not None:
                        goal = (self.loaded_player_spawn_pos.x // tile_size, self.loaded_player_spawn_pos.y // tile_size)
                    else:
                        goal = (self.game_manager.current_map.spawn.x // tile_size, self.game_manager.current_map.spawn.y // tile_size)
                    Logger.info(f"Navigating to start position: {goal}")
                    self._navigate_to_position(goal)
                    # 只有在成功啟動導航後才清除 final_goal
                    if self.auto_navigation_active:
                        self.navigation_final_goal = None
            elif self.navigation_final_goal == 'gym':
                if current_map_name == "gym.tmx":
                    self._navigate_to_spawn()
                    if self.auto_navigation_active:
                        self.navigation_final_goal = None
                elif current_map_name == "map.tmx":
                    # 還在 map.tmx，繼續導航到 gym 傳送點
                    self._navigate_to_teleporter("gym.tmx")
            elif self.navigation_final_goal == 'new_world':
                if current_map_name == "new_map.tmx":
                    self._navigate_to_spawn()
                    if self.auto_navigation_active:
                        self.navigation_final_goal = None
                elif current_map_name == "map.tmx":
                    # 還在 map.tmx，繼續導航到 new_map 傳送點
                    self._navigate_to_teleporter("new_map.tmx")
        
        # If returning from bush battle, move player back one tile
        if self.player_pos_before_battle is not None and self.game_manager.player:
            # Calculate direction from current pos to stored pos
            dx = self.player_pos_before_battle.x - self.game_manager.player.position.x
            dy = self.player_pos_before_battle.y - self.game_manager.player.position.y
            
            # Move player backward (opposite of the direction they were moving)
            if abs(dx) > abs(dy):
                # Horizontal movement was dominant
                if dx > 0:
                    # Was moving left, move back right
                    self.game_manager.player.position.x += GameSettings.TILE_SIZE
                else:
                    # Was moving right, move back left
                    self.game_manager.player.position.x -= GameSettings.TILE_SIZE
            else:
                # Vertical movement was dominant
                if dy > 0:
                    # Was moving up, move back down
                    self.game_manager.player.position.y += GameSettings.TILE_SIZE
                else:
                    # Was moving down, move back up
                    self.game_manager.player.position.y -= GameSettings.TILE_SIZE
            
            # Clear the stored position
            self.player_pos_before_battle = None
        
    @override
    def exit(self) -> None:
        # Don't disconnect online_manager when exiting to battle_scene
        # Keep the connection alive so other players can still see us
        pass
        
    @override
    def update(self, dt: float):
        # Check if there is assigned next scene
        self.game_manager.try_switch_map()
        
        # 檢測地圖是否切換，如果有最終目標則繼續導航
        current_map_key = self.game_manager.current_map_key if self.game_manager.current_map else None
        if current_map_key != self.previous_map_key and current_map_key is not None:
            Logger.info(f"Map changed from {self.previous_map_key} to {current_map_key}")
            self.previous_map_key = current_map_key
            
            # 如果有最終導航目標，繼續導航
            if self.navigation_final_goal and self.game_manager.player and self.game_manager.current_map:
                current_map_name = self.game_manager.current_map.path_name
                Logger.info(f"Continuing navigation to final goal: {self.navigation_final_goal} on map: {current_map_name}")
                
                if self.navigation_final_goal == 'start':
                    # 導航到 start（只能在 map.tmx 上）
                    if current_map_name == "map.tmx":
                        tile_size = GameSettings.TILE_SIZE
                        if getattr(self, 'loaded_player_spawn_pos', None) is not None:
                            goal = (self.loaded_player_spawn_pos.x // tile_size, self.loaded_player_spawn_pos.y // tile_size)
                        else:
                            goal = (self.game_manager.current_map.spawn.x // tile_size, self.game_manager.current_map.spawn.y // tile_size)
                        Logger.info(f"Navigating to start position: {goal}")
                        self._navigate_to_position(goal)
                        if self.auto_navigation_active:
                            self.navigation_final_goal = None
                
                elif self.navigation_final_goal == 'gym':
                    if current_map_name == "gym.tmx":
                        # 已經在 gym，導航到出生點
                        self._navigate_to_spawn()
                        if self.auto_navigation_active:
                            self.navigation_final_goal = None
                    elif current_map_name == "map.tmx":
                        # 在 map 上，繼續導航到 gym 傳送點
                        self._navigate_to_teleporter("gym.tmx")
                    # 如果在其他地圖（new_map），不應該發生，因為應該先回到 map
                
                elif self.navigation_final_goal == 'new_world':
                    if current_map_name == "new_map.tmx":
                        # 已經在 new_map，導航到出生點
                        self._navigate_to_spawn()
                        if self.auto_navigation_active:
                            self.navigation_final_goal = None
                    elif current_map_name == "map.tmx":
                        # 在 map 上，繼續導航到 new_map 傳送點
                        self._navigate_to_teleporter("new_map.tmx")
                    # 如果在其他地圖（gym），不應該發生，因為應該先回到 map
        
        # Update player and other data
        if self.game_manager.player:
            # 處理自動導航
            if self.auto_navigation_active:
                self._update_auto_navigation(dt)
            elif self._chat_overlay and self._chat_overlay.is_open:
                # 聊天窗口打開時不允許移動，只更新動畫
                self.game_manager.player.animation.update_pos(self.game_manager.player.position)
                self.game_manager.player.animation.update(dt)
            else:
                # 只有在非自動導航且聊天窗口關閉時才允許手動控制
                self.game_manager.player.update(dt)
            
            # Check for bush interaction
            player_rect = pg.Rect(
                self.game_manager.player.position.x,
                self.game_manager.player.position.y,
                GameSettings.TILE_SIZE,
                GameSettings.TILE_SIZE
            )
            
            if self.game_manager.current_map.check_bush(player_rect):
                # 如果遇到草叢，停止自動導航
                if self.auto_navigation_active:
                    self.auto_navigation_active = False
                    self.navigation_path = []
                    Logger.info("Auto navigation stopped due to bush encounter")
                
                # Player is on a bush - trigger battle immediately
                # Store player position before battle
                self.player_pos_before_battle = Position(
                    self.game_manager.player.position.x,
                    self.game_manager.player.position.y
                )
                # Generate unique wild pokemon name
                self.wild_pokemon_name = self._generate_unique_pokemon_name()
                # Enter battle scene
                scene_manager.change_scene("battle")
                    
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)
        
        for shop in self.game_manager.current_shop_managers:
            shop.update(dt)
            
        # Update others
        self.game_manager.bag.update(dt)
        
        # Chat overlay - press T to open
        if self._chat_overlay:
            if input_manager.key_pressed(pg.K_t):
                self._chat_overlay.open()
            self._chat_overlay.update(dt)
        
        # Update chat bubbles from recent messages
        if self.online_manager:
            try:
                msgs = self.online_manager.get_recent_chat(50)
                max_id = self._last_chat_id_seen
                now = time.monotonic()
                for m in msgs:
                    mid = int(m.get("id", 0))
                    if mid <= self._last_chat_id_seen:
                        continue
                    sender = int(m.get("from", -1))
                    text = str(m.get("text", ""))
                    if sender >= 0 and text:
                        self._chat_bubbles[sender] = (text, now + 5.0)
                    if mid > max_id:
                        max_id = mid
                self._last_chat_id_seen = max_id
            except Exception:
                pass
        self.bagpack_button.update(dt)
        self.navigation_button.update(dt)
        if self.shop_overlay_active:
            # update shop back button
            self.shop_back_button.update(dt)
            # update page navigation buttons
            self.next_page_button.update(dt)
            self.last_page_button.update(dt)
            # shop item buttons are updated in draw() method to avoid double-trigger
        if self.bagpack_overlay_active:
            # update bagpack back button
            self.bagpack_back_button.update(dt)
            # update page navigation buttons
            self.next_page_button.update(dt)
            self.last_page_button.update(dt)
        if self.navigation_overlay_active:
            # update navigation back button
            self.navigation_back_button.update(dt)
            # update navigation action buttons
            self.navigation_start.update(dt)
            self.navigation_gym.update(dt)
            self.navigation_new_world.update(dt)
        # Always update setting button (so能點擊)
        self.ingame_setting_button.update(dt)
        if self.overlay_active:
            # update checkbox above back_button first, then back_button
            self.checkbox_button.update(dt)
            self.back_button.update(dt)
            # update save and load buttons
            self.save_button.update(dt)
            self.load_button.update(dt)
            # handle slider dragging input
            # compute overlay rect (same as draw uses)
            if self.overlay_img is not None:
                ow = int(self.overlay_img.get_width() * self.overlay_scale)
                oh = int(self.overlay_img.get_height() * self.overlay_scale)
                overlay_rect = pg.Rect(0, 0, ow, oh)
                overlay_rect.center = (GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2)
                # compute track and knob sizes
                if self.slider_track_img is not None and self.slider_knob_img is not None:
                    track_width = int(overlay_rect.width * 0.6)
                    track_height = int(self.slider_track_img.get_height() * (track_width / max(1, self.slider_track_img.get_width())))
                    track_left = overlay_rect.centerx - track_width // 2
                    # ensure track doesn't overlap the 'Audio' label on the left
                    text_width = 0
                    if self.ui_font is not None:
                        try:
                            text_width = self.ui_font.size("Audio")[0]
                        except Exception:
                            text_width = 0
                    min_track_left = overlay_rect.left + 10 + text_width + 20
                    if track_left < min_track_left:
                        track_left = min_track_left
                    # position track near the top of the overlay to avoid overlapping other controls
                    track_top = overlay_rect.top + int(overlay_rect.height * 0.08)
                    knob_h = int(overlay_rect.height * 0.12)
                    knob_w = knob_h
                    # knob rect based on slider_value
                    knob_x = int(track_left + self.slider_value * (track_width - knob_w))
                    knob_y = track_top - (knob_h - track_height) // 2
                    knob_rect = pg.Rect(knob_x, knob_y, knob_w, knob_h)
                    mx, my = input_manager.mouse_pos
                    # start dragging if pressed on knob
                    if input_manager.mouse_pressed(1) and knob_rect.collidepoint((mx, my)):
                        self.slider_dragging = True
                    # update while mouse held down
                    if self.slider_dragging and input_manager.mouse_down(1):
                        # update slider_value based on mouse x
                        rel_x = mx - track_left
                        self.slider_value = max(0.0, min(1.0, rel_x / max(1, track_width - knob_w)))
                        # Update audio volume (0-1)
                        # 直接使用頂部已匯入的 GameSettings, sound_manager
                        GameSettings.AUDIO_VOLUME = self.slider_value
                        # Set current BGM volume if playing
                        if hasattr(sound_manager, 'current_bgm') and sound_manager.current_bgm:
                            sound_manager.current_bgm.set_volume(GameSettings.AUDIO_VOLUME)
                    # stop dragging on release
                    if input_manager.mouse_released(1):
                        self.slider_dragging = False
        if self.game_manager.player is not None and self.online_manager is not None:
            _ = self.online_manager.update(
                self.game_manager.player.position.x, 
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name
            )
        
    @override
    def draw(self, screen: pg.Surface):        
        if self.game_manager.player:
            '''
            [TODO HACKATHON 3]
            Implement the camera algorithm logic here
            Right now it's hard coded, you need to follow the player's positions
            you may use the below example, but the function still incorrect, you may trace the entity.py
            
            camera = self.game_manager.player.camera
            '''
            camera = self.game_manager.player.camera
            self.game_manager.current_map.draw(screen, camera)
            # Draw navigation arrows if path exists (only show remaining path)
            if getattr(self, 'navigation_path', None) and self.nav_arrow_img is not None:
                # scale arrow to fit tile
                tile_size = GameSettings.TILE_SIZE
                arrow_size = int(tile_size * 0.6)
                try:
                    arrow_surf = pg.transform.scale(self.nav_arrow_img, (arrow_size, arrow_size))
                except Exception:
                    arrow_surf = self.nav_arrow_img
                # Only draw arrows from current index onwards (hide walked path)
                start_index = getattr(self, 'navigation_current_index', 0)
                for i in range(start_index, len(self.navigation_path)):
                    tx, ty = self.navigation_path[i]
                    # compute pixel position of tile center
                    px = tx * tile_size + tile_size // 2
                    py = ty * tile_size + tile_size // 2
                    screen_pos = camera.transform_position(Position(px - arrow_size//2, py - arrow_size//2))
                    screen.blit(arrow_surf, screen_pos)
            self.game_manager.player.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)
        
        for shop in self.game_manager.current_shop_managers:
            shop.draw(screen, camera)

        self.game_manager.bag.draw(screen)
        self.ingame_setting_button.draw(screen)
        self.bagpack_button.draw(screen)
        self.navigation_button.draw(screen)
        # Draw letter N on navigation button (scaled to fit button)
        button_size = min(self.navigation_button.hitbox.width, self.navigation_button.hitbox.height)
        letter_size = int(button_size * 0.6)  # Make letter 60% of button size
        scaled_letter = pg.transform.scale(self.navigation_letter_img, (letter_size, letter_size))
        letter_rect = scaled_letter.get_rect(
            center=(self.navigation_button.hitbox.centerx, self.navigation_button.hitbox.centery)
        )
        screen.blit(scaled_letter, letter_rect)
        # Darken background when any overlay/chat is active so overlay stands out
        overlay_any = (
            self.overlay_active
            or self.bagpack_overlay_active
            or self.shop_overlay_active
            or self.navigation_overlay_active
            or (self._chat_overlay and getattr(self._chat_overlay, 'is_open', False))
        )
        if overlay_any:
            dark_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            dark_surf.fill((0, 0, 0, 150))
            screen.blit(dark_surf, (0, 0))
        if self.navigation_overlay_active:
            # Draw navigation overlay
            overlay_img_scaled = pg.transform.scale(
                self.overlay_img,
                (self.overlay_img.get_width() * 5, self.overlay_img.get_height() * 5)
            )
            overlay_rect = overlay_img_scaled.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2))
            screen.blit(overlay_img_scaled, overlay_rect)
            
            # Draw back button for navigation overlay
            self.navigation_back_button.hitbox.x = overlay_rect.left + 20
            self.navigation_back_button.hitbox.y = overlay_rect.bottom - self.navigation_back_button.hitbox.height - 20
            self.navigation_back_button.draw(screen)
            # Position and draw navigation action buttons at overlay's top-left
            margin_x = overlay_rect.left + 20
            margin_y = overlay_rect.top + 20
            spacing = 10
            # place buttons left-to-right starting from top-left corner
            self.navigation_start.hitbox.x = margin_x
            self.navigation_start.hitbox.y = margin_y
            self.navigation_gym.hitbox.x = margin_x + self.navigation_start.hitbox.width + spacing
            self.navigation_gym.hitbox.y = margin_y
            self.navigation_new_world.hitbox.x = margin_x + self.navigation_start.hitbox.width + spacing + self.navigation_gym.hitbox.width + spacing
            self.navigation_new_world.hitbox.y = margin_y
            self.navigation_start.draw(screen)
            self.navigation_gym.draw(screen)
            self.navigation_new_world.draw(screen)
            
            # Draw labels below navigation buttons
            try:
                nav_label_font = pg.font.SysFont(None, 24)
            except Exception:
                nav_label_font = None
            
            if nav_label_font is not None:
                # Start label
                start_label = nav_label_font.render("Start", True, (255, 255, 255))
                start_label_x = self.navigation_start.hitbox.centerx - start_label.get_width() // 2
                start_label_y = self.navigation_start.hitbox.bottom + 5
                screen.blit(start_label, (start_label_x, start_label_y))
                
                # Gym label
                gym_label = nav_label_font.render("Gym", True, (255, 255, 255))
                gym_label_x = self.navigation_gym.hitbox.centerx - gym_label.get_width() // 2
                gym_label_y = self.navigation_gym.hitbox.bottom + 5
                screen.blit(gym_label, (gym_label_x, gym_label_y))
                
                # New World label
                new_world_label = nav_label_font.render("New World", True, (255, 255, 255))
                new_world_label_x = self.navigation_new_world.hitbox.centerx - new_world_label.get_width() // 2
                new_world_label_y = self.navigation_new_world.hitbox.bottom + 5
                screen.blit(new_world_label, (new_world_label_x, new_world_label_y))
        if self.bagpack_overlay_active:
            # Draw bagpack overlay with monster and item list
            overlay_img_scaled = pg.transform.scale(
                self.overlay_img,
                (self.overlay_img.get_width() * 10, self.overlay_img.get_height() * 10)
            )
            overlay_rect = overlay_img_scaled.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2))
            screen.blit(overlay_img_scaled, overlay_rect)
            
            # Initialize font if needed
            if self.ui_font is None:
                try:
                    self.ui_font = pg.font.SysFont(None, 56)
                except Exception:
                    pass
            
            # Create smaller font for list items
            try:
                list_font = pg.font.SysFont(None, 28)
            except Exception:
                list_font = self.ui_font
            
            if list_font is not None:
                # Title
                title_text = list_font.render("Backpack", True, (255, 255, 255))
                title_x = overlay_rect.centerx - title_text.get_width() // 2
                title_y = overlay_rect.top + 20
                screen.blit(title_text, (title_x, title_y))
                
                # Calculate safe content area (avoid back button on the left)
                content_left = overlay_rect.left + 140
                content_right = overlay_rect.right - 30
                
                # Combine monsters and items into one list for pagination
                monsters = self.game_manager.bag._monsters_data
                items = self.game_manager.bag._items_data
                all_items = []
                
                # Add monsters with type flag
                for monster in monsters:
                    all_items.append(('monster', monster))
                
                # Add items with type flag
                for item in items:
                    all_items.append(('item', item))
                
                # Calculate pagination
                start_idx = self.current_page * self.items_per_page
                end_idx = min(start_idx + self.items_per_page, len(all_items))
                page_items = all_items[start_idx:end_idx]
                
                # Display page number
                total_pages = max(1, (len(all_items) + self.items_per_page - 1) // self.items_per_page)
                page_text = list_font.render(f"Page {self.current_page + 1}/{total_pages}", True, (255, 255, 255))
                page_x = overlay_rect.centerx - page_text.get_width() // 2
                page_y = overlay_rect.top + 50
                screen.blit(page_text, (page_x, page_y))
                
                # Draw items
                y_offset = overlay_rect.top + 90
                
                if page_items:
                    for item_type, item_data in page_items:
                        # Draw sprite
                        if 'sprite_path' in item_data:
                            try:
                                from src.sprites import Sprite
                                sprite = Sprite(item_data['sprite_path'], (32, 32))
                                sprite_rect = sprite.image.get_rect()
                                sprite_rect.x = content_right - 70
                                sprite_rect.y = y_offset
                                screen.blit(sprite.image, sprite_rect)
                            except Exception:
                                pass
                        
                        # Draw text based on type
                        if item_type == 'monster':
                            text = f"{item_data['name']} - Lv.{item_data['level']} HP:{item_data['hp']}/{item_data['max_hp']}"
                            color = (255, 255, 255)  # White
                        else:  # item
                            text = f"{item_data['name']} x{item_data['count']}"
                            color = (255, 255, 255)  # White
                        
                        text_surf = list_font.render(text, True, color)
                        text_x = content_left + 10
                        screen.blit(text_surf, (text_x, y_offset))
                        y_offset += 40
                else:
                    no_items_text = list_font.render("No items", True, (150, 150, 150))
                    screen.blit(no_items_text, (content_left + 10, y_offset))
            
            # Draw page navigation buttons in bottom right
            # Last page button (left)
            self.last_page_button.hitbox.x = overlay_rect.right - 140
            self.last_page_button.hitbox.y = overlay_rect.bottom - self.last_page_button.hitbox.height - 20
            self.last_page_button.draw(screen)
            # Next page button (right)
            self.next_page_button.hitbox.x = overlay_rect.right - 70
            self.next_page_button.hitbox.y = overlay_rect.bottom - self.next_page_button.hitbox.height - 20
            self.next_page_button.draw(screen)
            
            # Draw back button for bagpack overlay
            self.bagpack_back_button.hitbox.x = overlay_rect.left + 20
            self.bagpack_back_button.hitbox.y = overlay_rect.bottom - self.bagpack_back_button.hitbox.height - 20
            self.bagpack_back_button.draw(screen)
        
        if self.shop_overlay_active:
            # Draw shop overlay with monster and item list from shop_list
            overlay_img_scaled = pg.transform.scale(
                self.overlay_img,
                (self.overlay_img.get_width() * 10, self.overlay_img.get_height() * 10)
            )
            overlay_rect = overlay_img_scaled.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2))
            screen.blit(overlay_img_scaled, overlay_rect)
            
            # Initialize font if needed
            if self.ui_font is None:
                try:
                    self.ui_font = pg.font.SysFont(None, 56)
                except Exception:
                    pass
            
            # Create larger font for shop list items (32 * 1.5 = 48, reduced to 42)
            try:
                list_font = pg.font.SysFont(None, 42)
            except Exception:
                list_font = self.ui_font
            
            if list_font is not None:
                # Title
                title_text = list_font.render("Shop", True, (255, 255, 255))
                title_x = overlay_rect.centerx - title_text.get_width() // 2
                title_y = overlay_rect.top + 20
                screen.blit(title_text, (title_x, title_y))
                
                # Calculate safe content area
                content_left = overlay_rect.left + 140
                content_right = overlay_rect.right - 30
                
                # Combine monsters and items into one list for pagination
                monsters = self.game_manager.shop_list._monsters_data
                items = self.game_manager.shop_list._items_data
                all_items = []
                
                # Add monsters with type flag
                for monster in monsters:
                    all_items.append(('monster', monster))
                
                # Add items with type flag
                for item in items:
                    all_items.append(('item', item))
                
                # Calculate pagination
                start_idx = self.current_page * self.items_per_page
                end_idx = min(start_idx + self.items_per_page, len(all_items))
                page_items = all_items[start_idx:end_idx]
                
                # Display page number
                total_pages = max(1, (len(all_items) + self.items_per_page - 1) // self.items_per_page)
                page_text = list_font.render(f"Page {self.current_page + 1}/{total_pages}", True, (255, 255, 255))
                page_x = overlay_rect.centerx - page_text.get_width() // 2
                page_y = overlay_rect.top + 50
                screen.blit(page_text, (page_x, page_y))
                
                # Draw items
                y_offset = overlay_rect.top + 90
                # Clear and recreate buttons
                self.shop_item_buttons = []
                
                if page_items:
                    for idx, (item_type, item_data) in enumerate(page_items):
                        actual_idx = start_idx + idx  # Calculate actual index in full list
                        
                        # Draw sprite
                        if 'sprite_path' in item_data:
                            try:
                                from src.sprites import Sprite
                                sprite = Sprite(item_data['sprite_path'], (32, 32))
                                sprite_rect = sprite.image.get_rect()
                                sprite_rect.x = content_right - 130  # Adjusted for larger button
                                sprite_rect.y = y_offset
                                screen.blit(sprite.image, sprite_rect)
                            except Exception:
                                pass
                        
                        # Draw text based on type
                        if item_type == 'monster':
                            text = f"{item_data['name']} - Lv.{item_data['level']} HP:{item_data['hp']}/{item_data['max_hp']}"
                            color = (255, 255, 255)  # White
                            is_monster = True
                        else:  # item
                            text = f"{item_data['name']}"
                            color = (255, 255, 255)  # White
                            is_monster = False
                        
                        text_surf = list_font.render(text, True, color)
                        text_x = content_left + 10
                        screen.blit(text_surf, (text_x, y_offset))
                        
                        # Create buy button (larger for shop: 30 * 1.5 = 45)
                        btn_width = 45
                        btn_height = 45
                        btn_x = content_right - btn_width - 10
                        btn_y = y_offset
                        btn = Button(
                            img_path="UI/button_shop.png",
                            img_hovered_path="UI/button_shop_hover.png",
                            x=btn_x,
                            y=btn_y,
                            width=btn_width,
                            height=btn_height,
                            on_click=lambda idx=actual_idx, is_m=is_monster: self.on_shop_item_click(idx, is_m)
                        )
                        btn.update(0)
                        btn.draw(screen)
                        self.shop_item_buttons.append(btn)
                        
                        y_offset += 60  # 40 * 1.5 = 60
                else:
                    no_items_text = list_font.render("No items", True, (150, 150, 150))
                    screen.blit(no_items_text, (content_left + 10, y_offset))
            
            # Draw page navigation buttons in bottom right
            # Last page button (left)
            self.last_page_button.hitbox.x = overlay_rect.right - 140
            self.last_page_button.hitbox.y = overlay_rect.bottom - self.last_page_button.hitbox.height - 20
            self.last_page_button.draw(screen)
            # Next page button (right)
            self.next_page_button.hitbox.x = overlay_rect.right - 70
            self.next_page_button.hitbox.y = overlay_rect.bottom - self.next_page_button.hitbox.height - 20
            self.next_page_button.draw(screen)
            
            # Draw back button for shop overlay
            self.shop_back_button.hitbox.x = overlay_rect.left + 20
            self.shop_back_button.hitbox.y = overlay_rect.bottom - self.shop_back_button.hitbox.height - 20
            self.shop_back_button.draw(screen)
        
        if self.overlay_active:
            #enlarge overlay
            overlay_img_scaled = pg.transform.scale(
                self.overlay_img,
                (self.overlay_img.get_width() * 5, self.overlay_img.get_height() * 5)
            )
            overlay_rect = overlay_img_scaled.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2))
            screen.blit(overlay_img_scaled, overlay_rect)
            # move back_button to overlay left-bottom
            self.back_button.hitbox.x = overlay_rect.left + 20
            self.back_button.hitbox.y = overlay_rect.bottom - self.back_button.hitbox.height - 20
            # position checkbox_button at the center of the overlay image
            self.checkbox_button.hitbox.x = overlay_rect.centerx - self.checkbox_button.hitbox.width // 2
            self.checkbox_button.hitbox.y = overlay_rect.centery - self.checkbox_button.hitbox.height // 2
            # draw mute label left of checkbox (shows on/off depending on checkbox state)
            if self.ui_font is None:
                try:
                    self.ui_font = pg.font.SysFont(None, 56)
                except Exception:
                    self.ui_font = None
            if self.ui_font is not None:
                label = "mute: on" if getattr(self, 'checkbox_checked', False) else "mute: off"
                text_surf = self.ui_font.render(label, True, (255, 255, 255))
                # place text slightly to the right of the overlay left border, but ensure it doesn't overlap checkbox
                preferred_x = overlay_rect.left + 20
                max_x = self.checkbox_button.hitbox.left - text_surf.get_width() - 10
                text_x = min(preferred_x, max_x)
                if text_x < overlay_rect.left + 10:
                    text_x = overlay_rect.left + 10
                text_y = self.checkbox_button.hitbox.top + (self.checkbox_button.hitbox.height - text_surf.get_height()) // 2
                screen.blit(text_surf, (text_x, text_y))
            # draw checkbox then back_button so checkbox appears above
            self.checkbox_button.draw(screen)
            self.back_button.draw(screen)
            # Calculate button spacing - make all buttons evenly spaced at bottom
            button_spacing = 20
            back_button_x = overlay_rect.left + 20
            # position and draw save button (after back button with equal spacing)
            self.save_button.hitbox.x = back_button_x + self.back_button.hitbox.width + button_spacing
            self.save_button.hitbox.y = overlay_rect.bottom - self.save_button.hitbox.height - 20
            self.save_button.draw(screen)
            # position and draw load button (after save button with equal spacing)
            self.load_button.hitbox.x = self.save_button.hitbox.x + self.save_button.hitbox.width + button_spacing
            self.load_button.hitbox.y = overlay_rect.bottom - self.load_button.hitbox.height - 20
            self.load_button.draw(screen)
            # draw slider track and knob inside overlay
            if self.slider_track_img is not None and self.slider_knob_img is not None:
                # compute track and knob sizes same as update
                track_width = int(overlay_rect.width * 0.6)
                track_height = int(self.slider_track_img.get_height() * (track_width / max(1, self.slider_track_img.get_width())))
                track_left = overlay_rect.centerx - track_width // 2
                # ensure track doesn't overlap the 'Audio' label on the left
                text_width = 0
                if self.ui_font is not None:
                    try:
                        text_width = self.ui_font.size("Audio")[0]
                    except Exception:
                        text_width = 0
                min_track_left = overlay_rect.left + 10 + text_width + 20
                if track_left < min_track_left:
                    track_left = min_track_left
                # position track near the top of the overlay to avoid overlapping other controls
                track_top = overlay_rect.top + int(overlay_rect.height * 0.08)
                knob_h = int(overlay_rect.height * 0.12)
                knob_w = knob_h
                # scale images
                track_surf = pg.transform.scale(self.slider_track_img, (track_width, max(1, track_height)))
                knob_surf = pg.transform.scale(self.slider_knob_img, (knob_w, knob_h))
                # draw 'Audio' label to the left of the track, keep inside overlay
                if self.ui_font is None:
                    try:
                        self.ui_font = pg.font.SysFont(None, 56)
                    except Exception:
                        self.ui_font = None
                if self.ui_font is not None:
                    audio_label = "Audio"
                    text_surf = self.ui_font.render(audio_label, True, (255, 255, 255))
                    text_x = track_left - text_surf.get_width() - 10
                    # ensure text stays inside overlay left border
                    if text_x < overlay_rect.left + 10:
                        text_x = overlay_rect.left + 10
                    text_y = track_top + (knob_h - text_surf.get_height()) // 2
                    screen.blit(text_surf, (text_x, text_y))
                screen.blit(track_surf, (track_left, track_top))
                knob_x = int(track_left + self.slider_value * (track_width - knob_w))
                knob_y = track_top - (knob_h - track_height) // 2
                screen.blit(knob_surf, (knob_x, knob_y))
                # Draw value (0-100) below audio label
                if self.ui_font is not None:
                    value_label = f"{int(self.slider_value * 100)}"
                    value_surf = self.ui_font.render(value_label, True, (255, 255, 255))
                    value_x = text_x + (text_surf.get_width() - value_surf.get_width()) // 2
                    value_y = text_y + text_surf.get_height() + 5
                    screen.blit(value_surf, (value_x, value_y))
        if self._chat_overlay:
            self._chat_overlay.draw(screen)
        # Draw online players only if no overlay is active
        if not (self.overlay_active or self.bagpack_overlay_active or self.shop_overlay_active or self.navigation_overlay_active):
            if self.online_manager and self.game_manager.player:
                list_online = self.online_manager.get_list_players()
                # Get current online player IDs and clean up old data
                current_online_ids = set()
                for player in list_online:
                    player_id = int(player.get("id", -1))
                    current_online_ids.add(player_id)
                    
                    if player["map"] == self.game_manager.current_map.path_name:
                        cam = self.game_manager.player.camera
                        world_pos = Position(player["x"], player["y"])
                        
                        # Create animation for new players
                        if player_id not in self._online_player_animations:
                            self._online_player_animations[player_id] = Animation(
                                "character/ow8.png", 
                                ["down", "left", "right", "up"], 
                                4,
                                (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                            )
                        
                        # Update direction based on movement
                        if player_id in self._online_last_pos:
                            old_pos = self._online_last_pos[player_id]
                            dx = world_pos.x - old_pos.x
                            dy = world_pos.y - old_pos.y
                            
                            if abs(dx) > 0.1 or abs(dy) > 0.1:  # Player is moving
                                if abs(dy) > abs(dx):  # Vertical movement priority
                                    if dy < 0:
                                        self._online_player_animations[player_id].switch("up")
                                    else:
                                        self._online_player_animations[player_id].switch("down")
                                else:  # Horizontal movement
                                    if dx < 0:
                                        self._online_player_animations[player_id].switch("left")
                                    else:
                                        self._online_player_animations[player_id].switch("right")
                        
                        self._online_last_pos[player_id] = world_pos
                        
                        # Update and draw animation
                        anim = self._online_player_animations[player_id]
                        anim.update_pos(world_pos)
                        anim.update(0.016)  # Approximate 60 FPS
                        anim.draw(screen, cam)
                
                # Clean up disconnected players
                for pid in list(self._online_player_animations.keys()):
                    if pid not in current_online_ids:
                        del self._online_player_animations[pid]
                for pid in list(self._online_last_pos.keys()):
                    if pid not in current_online_ids:
                        del self._online_last_pos[pid]
                
                try:
                    self._draw_chat_bubbles(screen, self.game_manager.player.camera)
                except Exception:
                    pass
        # Draw minimap only if no overlay is active
        if not (self.overlay_active or self.bagpack_overlay_active or self.shop_overlay_active or self.navigation_overlay_active):
            self._draw_minimap(screen)
    
    def _draw_minimap(self, screen: pg.Surface):
        """Draw a minimap in the top-right corner showing player position on the full map"""
        if not self.game_manager.player or not self.game_manager.current_map:
            return
        
        # Get map dimensions in pixels
        map_width = self.game_manager.current_map.tmxdata.width * GameSettings.TILE_SIZE
        map_height = self.game_manager.current_map.tmxdata.height * GameSettings.TILE_SIZE
        
        # Calculate minimap position (top-right corner)
        minimap_x = GameSettings.SCREEN_WIDTH - self.minimap_size - self.minimap_padding
        minimap_y = self.minimap_padding
        
        # Calculate scale to fit the entire map in the minimap
        scale_x = self.minimap_size / map_width
        scale_y = self.minimap_size / map_height
        scale = min(scale_x, scale_y)  # Use the smaller scale to maintain aspect ratio
        
        # Calculate actual minimap dimensions
        minimap_width = int(map_width * scale)
        minimap_height = int(map_height * scale)
        
        # Adjust position to keep it aligned to top-right
        minimap_x = GameSettings.SCREEN_WIDTH - minimap_width - self.minimap_padding
        
        # Create a semi-transparent background for the minimap
        minimap_bg = pg.Surface((minimap_width, minimap_height), pg.SRCALPHA)
        minimap_bg.fill((0, 0, 0, 180))  # Semi-transparent black
        screen.blit(minimap_bg, (minimap_x, minimap_y))
        
        # Scale and draw the map on the minimap
        scaled_map = pg.transform.scale(
            self.game_manager.current_map._surface,
            (minimap_width, minimap_height)
        )
        screen.blit(scaled_map, (minimap_x, minimap_y))
        
        # Draw border around minimap
        pg.draw.rect(
            screen,
            (255, 255, 255),
            (minimap_x, minimap_y, minimap_width, minimap_height),
            self.minimap_border_width
        )
        
        # Calculate player position on minimap
        player_x = self.game_manager.player.position.x
        player_y = self.game_manager.player.position.y
        
        minimap_player_x = minimap_x + int(player_x * scale)
        minimap_player_y = minimap_y + int(player_y * scale)
        
        # Draw camera viewport rectangle (what the player can see)
        camera_width = GameSettings.SCREEN_WIDTH * scale
        camera_height = GameSettings.SCREEN_HEIGHT * scale
        
        camera_rect_x = minimap_player_x - camera_width / 2
        camera_rect_y = minimap_player_y - camera_height / 2
        
        # Clamp to minimap bounds
        camera_rect_x = max(minimap_x, min(camera_rect_x, minimap_x + minimap_width - camera_width))
        camera_rect_y = max(minimap_y, min(camera_rect_y, minimap_y + minimap_height - camera_height))
        
        # Draw viewport rectangle
        pg.draw.rect(
            screen,
            (255, 255, 0, 150),  # Yellow with transparency
            (camera_rect_x, camera_rect_y, camera_width, camera_height),
            2
        )
        
        # Draw player position as a dot
        player_dot_size = max(4, int(GameSettings.TILE_SIZE * scale))
        pg.draw.circle(
            screen,
            (255, 0, 0),  # Red color
            (int(minimap_player_x), int(minimap_player_y)),
            player_dot_size
        )

    def _update_auto_navigation(self, dt: float):
        """處理自動導航邏輯"""
        if not self.navigation_path or not self.game_manager.player:
            self.auto_navigation_active = False
            return
        
        tile_size = GameSettings.TILE_SIZE
        player = self.game_manager.player
        
        # 如果已經走完所有路徑點，停止導航
        if self.navigation_current_index >= len(self.navigation_path):
            self.auto_navigation_active = False
            self.navigation_path = []  # 清空路徑
            Logger.info("Auto navigation path completed")
            
            # 檢查是否在傳送點上，如果是則觸發傳送
            tp = self.game_manager.current_map.check_teleport(player.position)
            if tp and self.navigation_final_goal:
                Logger.info(f"Reached teleporter to {tp.destination}, teleporting...")
                # 觸發傳送
                self.game_manager.switch_map(tp.destination, tp.target_pos)
                # 等待下一幀繼續導航到最終目標
                # 使用 pygame 延遲事件來在地圖切換後繼續導航
                return
            else:
                # 沒有傳送點或沒有最終目標，導航完成
                self.navigation_final_goal = None
            return
        
        # 獲取當前目標格子
        target_tile = self.navigation_path[self.navigation_current_index]
        target_x = target_tile[0] * tile_size
        target_y = target_tile[1] * tile_size
        
        # 計算到目標的距離
        dx = target_x - player.position.x
        dy = target_y - player.position.y
        distance = math.hypot(dx, dy)
        
        # 如果已經到達當前目標格子，移動到下一個
        if distance < 5:  # 5像素容差
            # 對齊到格子中心
            player.position.x = target_x
            player.position.y = target_y
            self.navigation_current_index += 1
            return
        
        # 計算移動方向並正規化
        if distance > 0:
            dx /= distance
            dy /= distance
        
        # 更新方向和動畫
        from src.utils import Direction
        if abs(dy) > abs(dx):  # 垂直移動優先
            if dy < 0:
                player.direction = Direction.UP
            else:
                player.direction = Direction.DOWN
        else:  # 水平移動
            if dx < 0:
                player.direction = Direction.LEFT
            else:
                player.direction = Direction.RIGHT
        # 切換動畫
        player.animation.switch(player.direction.name.lower())
        
        # 應用速度和時間增量
        move_distance = player.speed * dt
        dis_x = dx * move_distance
        dis_y = dy * move_distance
        
        # 更新 X 座標，檢查碰撞
        old_x = player.position.x
        player.position.x += dis_x
        rect_x = pg.Rect(player.position.x, player.position.y, tile_size, tile_size)
        
        if self.game_manager.check_collision(rect_x):
            player.position.x = old_x
            # 碰撞時停止自動導航
            self.auto_navigation_active = False
            self.navigation_path = []
            Logger.info("Auto navigation stopped due to collision")
            return
        
        # 更新 Y 座標，檢查碰撞
        old_y = player.position.y
        player.position.y += dis_y
        rect_y = pg.Rect(player.position.x, player.position.y, tile_size, tile_size)
        
        if self.game_manager.check_collision(rect_y):
            player.position.y = old_y
            # 碰撞時停止自動導航
            self.auto_navigation_active = False
            self.navigation_path = []
            Logger.info("Auto navigation stopped due to collision")
            return
        
        # 更新玩家位置和動畫
        player.animation.update_pos(player.position)
        player.animation.update(dt)
    
    def _generate_unique_pokemon_name(self) -> str:
        """Generate a unique random 5-letter pokemon name"""
        while True:
            name = ''.join(random.choices(string.ascii_lowercase, k=5))
            if name not in self.used_pokemon_names:
                self.used_pokemon_names.add(name)
                return name
    def _draw_chat_bubbles(self, screen: pg.Surface, camera: PositionCamera) -> None:
        
        if not self.online_manager:
            return
        # REMOVE EXPIRED BUBBLES
        now = time.monotonic()
        expired = [pid for pid, (_, ts) in self._chat_bubbles.items() if ts <= now]
        for pid in expired:
            self._chat_bubbles.pop(pid, None)
        if not self._chat_bubbles:
            return

        # DRAW LOCAL PLAYER'S BUBBLE
        local_pid = self.online_manager.player_id
        if self.game_manager.player and local_pid in self._chat_bubbles:
            text, _ = self._chat_bubbles[local_pid]
            self._draw_chat_bubble_for_pos(screen, camera, self.game_manager.player.position, text, self._get_chat_font())

        # DRAW OTHER PLAYERS' BUBBLES
        for pid, (text, _) in self._chat_bubbles.items():
            if pid == local_pid:
                continue
            pos_xy = self._online_last_pos.get(pid, None)
            if not pos_xy:
                continue
            self._draw_chat_bubble_for_pos(screen, camera, pos_xy, text, self._get_chat_font())

        """
        DRAWING CHAT BUBBLES:
        - When a player sends a chat message, the message should briefly appear above
        that player's character in the world, similar to speech bubbles in RPGs.
        - Each bubble should last only a few seconds before fading or disappearing.
        - Only players currently visible on the map should show bubbles.

         What you need to think about:
            ------------------------------
            1. **Which players currently have messages?**
            You will have a small structure mapping player IDs to the text they sent
            and the time the bubble should disappear.

            2. **How do you know where to place the bubble?**
            The bubble belongs above the player's *current position in the world*.
            The game already tracks each player's world-space location.
            Convert that into screen-space and draw the bubble there.

            3. **How should bubbles look?**
            You decide. The visual style is up to you:
            - A rounded rectangle, or a simple box.
            - Optional border.
            - A small triangle pointing toward the character's head.
            - Enough padding around the text so it looks readable.

            4. **How do bubbles disappear?**
            Compare the current time to the stored expiration timestamp.
            Remove any bubbles that have expired.

            5. **In what order should bubbles be drawn?**
            Draw them *after* world objects but *before* UI overlays.

        Reminder:
        - For the local player, you can use the self.game_manager.player.position to get the player's position
        - For other players, maybe you can find some way to store other player's last position?
        - For each player with a message, maybe you can call a helper to actually draw a single bubble?
        """
        """
        DRAWING CHAT BUBBLES:
        - When a player sends a chat message, the message should briefly appear above
        that player's character in the world, similar to speech bubbles in RPGs.
        - Each bubble should last only a few seconds before fading or disappearing.
        - Only players currently visible on the map should show bubbles.

         What you need to think about:
            ------------------------------
            1. **Which players currently have messages?**
            You will have a small structure mapping player IDs to the text they sent
            and the time the bubble should disappear.

            2. **How do you know where to place the bubble?**
            The bubble belongs above the player's *current position in the world*.
            The game already tracks each player’s world-space location.
            Convert that into screen-space and draw the bubble there.

            3. **How should bubbles look?**
            You decide. The visual style is up to you:
            - A rounded rectangle, or a simple box.
            - Optional border.
            - A small triangle pointing toward the character's head.
            - Enough padding around the text so it looks readable.

            4. **How do bubbles disappear?**
            Compare the current time to the stored expiration timestamp.
            Remove any bubbles that have expired.

            5. **In what order should bubbles be drawn?**
            Draw them *after* world objects but *before* UI overlays.

        Reminder:
        - For the local player, you can use the self.game_manager.player.position to get the player's position
        - For other players, maybe you can find some way to store other player's last position?
        - For each player with a message, maybe you can call a helper to actually draw a single bubble?
        """

    def _draw_chat_bubble_for_pos(self, screen: pg.Surface, camera: PositionCamera, world_pos: Position, text: str, font: pg.font.Font):
        """Convert world position to screen position and draw chat bubble above player."""
        # Convert world position to screen position
        screen_pos = camera.transform_position(world_pos)
        
        # Position above the player (offset upward)
        bubble_x = screen_pos[0]
        bubble_y = screen_pos[1] - 40  # 40 pixels above the player
        
        # Render text and measure size
        text_surf = font.render(text, True, (255, 255, 255))
        text_width = text_surf.get_width()
        text_height = text_surf.get_height()
        
        # Add padding around text
        padding = 8
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2
        
        # Create bubble background
        bubble_surface = pg.Surface((box_width, box_height), pg.SRCALPHA)
        bubble_surface.fill((0, 0, 0, 200))  # Semi-transparent black background
        pg.draw.rect(bubble_surface, (255, 255, 255), bubble_surface.get_rect(), 2)  # White border
        
        # Draw bubble on screen
        bubble_x_centered = bubble_x - box_width // 2
        _ = screen.blit(bubble_surface, (bubble_x_centered, bubble_y))
        
        # Draw text inside bubble
        text_x = bubble_x_centered + padding
        text_y = bubble_y + padding
        _ = screen.blit(text_surf, (text_x, text_y))
    
    def _get_chat_font(self) -> pg.font.Font:
        """Get or create a font for chat bubbles."""
        try:
            return pg.font.Font("assets/fonts/Minecraft.ttf", 12)
        except:
            return pg.font.SysFont("arial", 12)
        """
        Steps:
            ------------------
            1. Convert a player’s world position into a location on the screen.
            (Use the camera system provided by the game engine.)

            2. Decide where "above the player" is.
            Typically a little above the sprite’s head.

            3. Measure the rendered text to determine bubble size.
            Add padding around the text.
        """       










