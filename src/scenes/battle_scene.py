import pygame as pg
from src.scenes.scene import Scene
from src.utils import GameSettings
from src.core.services import scene_manager, input_manager
from src.interface.components import Button
from typing import override
import random

class BattleScene(Scene):
    def __init__(self):
        super().__init__()
        # Load battle background
        try:
            self.background = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\backgrounds\background1.png").convert()
            self.background = pg.transform.scale(self.background, (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        except Exception:
            self.background = None
        
        # Load exclamation icon
        try:
            self.exclamation_icon = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\exclamation.png").convert_alpha()
            self.exclamation_icon = pg.transform.scale(self.exclamation_icon, (24, 24))
        except Exception:
            self.exclamation_icon = None
        
        # Reference to game manager (will be set in enter())
        self.game_manager = None
        
        # Wild pokemon flag and data
        self.is_wild_battle = False
        self.wild_pokemon_name = None
        
        # Battle state
        self.current_monster_index = 0  # Index of current monster in bag
        self.player_monster_name = "Florion"
        self.player_hp = 189
        self.player_max_hp = 201
        self.player_level = 20
        self.player_atk = 20
        self.player_def = 10
        self.player_attribute = "none"
        
        self.enemy_monster_name = "Florion"
        self.enemy_hp = 161
        self.enemy_max_hp = 161
        self.enemy_level = 16
        self.enemy_atk = 20
        self.enemy_def = 10
        self.enemy_attribute = "none"
        
        self.is_player_turn = True
        self.battle_over = False
        self.player_won = False
        self.waiting_for_action = False
        self.action_message = f"What will {self.player_monster_name} do?"
        self.message_timer = 0
        self.show_buttons = True
        
        # Buff effects
        self.temp_atk_boost = 0  # Temporary attack boost for one turn
        self.def_boost = 0  # Permanent defense boost for this battle
        
        # Enemy list for random trainer battles
        self.enemy_list = [
            {"name": "Pikachu", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite1.png", "attribute": "grass"},
            {"name": "Venusaur", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite4.png", "attribute": "none"},
            {"name": "Gengar", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite5.png", "attribute": "none"},
            {"name": "Dragonite", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite6.png", "attribute": "snow"},
            {"name": "Devin", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite10.png", "attribute": "none"},
            {"name": "Booker", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite11.png", "attribute": "none"},
            {"name": "Kevin", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite7.png", "attribute": "fire"},
            {"name": "Durant", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite12.png", "attribute": "water"},
            {"name": "MyGoat", "hp": 10, "max_hp": 10, "level": 1, "sprite_path": "menu_sprites/menusprite15.png", "attribute": "grass"}
        ]
        
        # Load monster sprites (using menusprite for both)
        try:
            monster_sprite_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\menu_sprites\menusprite5.png"
            self.monster_sprite = pg.image.load(monster_sprite_path).convert_alpha()
            self.enemy_monster_sprite = self.monster_sprite  # Enemy's original sprite
            # Enemy monster (top) - larger
            self.enemy_sprite = pg.transform.scale(self.monster_sprite, (200, 200))
            # Player monster (bottom) - smaller
            self.player_sprite = pg.transform.scale(self.monster_sprite, (180, 180))
        except Exception:
            self.enemy_sprite = None
            self.player_sprite = None
            self.enemy_monster_sprite = None
        
        # Fonts
        try:
            self.card_font = pg.font.SysFont(None, 32)
            self.hp_font = pg.font.SysFont(None, 28)
            self.dialog_font = pg.font.SysFont(None, 40)
            self.button_font = pg.font.SysFont(None, 36)
        except Exception:
            self.card_font = None
            self.hp_font = None
            self.dialog_font = None
            self.button_font = None
        
        # Battle action buttons - positioned at bottom in dialog box
        button_y = GameSettings.SCREEN_HEIGHT - 90
        button_width = 150
        button_height = 60
        button_spacing = 20
        
        # Calculate starting x to center all 4 buttons
        total_width = (button_width * 4) + (button_spacing * 3)
        start_x = (GameSettings.SCREEN_WIDTH - total_width) // 2
        
        # Create simple colored rectangles for buttons
        self.fight_button_rect = pg.Rect(start_x, button_y, button_width, button_height)
        self.item_button_rect = pg.Rect(start_x + button_width + button_spacing, button_y, button_width, button_height)
        self.switch_button_rect = pg.Rect(start_x + (button_width + button_spacing) * 2, button_y, button_width, button_height)
        self.run_button_rect = pg.Rect(start_x + (button_width + button_spacing) * 3, button_y, button_width, button_height)
        
        self.hovered_button = None
        
        # Item overlay
        self.item_overlay_active = False
        self.item_buttons = []
        try:
            self.overlay_img = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Frame03a.png").convert_alpha()
        except Exception as e:
            print(f"Failed to load overlay image: {e}")
            self.overlay_img = None
    
    def load_current_monster(self):
        """Load current monster stats from bag"""
        if self.game_manager is None:
            return
        
        monsters = self.game_manager.bag._monsters_data
        
        if len(monsters) == 0:
            # No monsters, use default
            self.player_monster_name = "Florion"
            self.player_hp = 189
            self.player_max_hp = 201
            self.player_level = 20
            return
        
        # Ensure index is valid
        if self.current_monster_index >= len(monsters):
            self.current_monster_index = 0
        
        monster = monsters[self.current_monster_index]
        self.player_monster_name = monster['name']
        self.player_hp = monster['hp']
        self.player_max_hp = monster['max_hp']
        self.player_level = monster['level']
        self.player_atk = monster.get('atk', 20 + (monster['level'] - 1) * 2)
        self.player_def = monster.get('def', 10 + (monster['level'] - 1))
        self.player_attribute = monster.get('attribute', 'none')
        
        # Load monster sprite
        if 'sprite_path' in monster:
            try:
                sprite_path = f"C:\\Users\\kllx\\Desktop\\NTHU-I2P-I-Final-Project-2025-main\\assets\\images\\{monster['sprite_path']}"
                self.monster_sprite = pg.image.load(sprite_path).convert_alpha()
                self.player_sprite = pg.transform.scale(self.monster_sprite, (180, 180))
            except Exception:
                pass
    
    def get_type_effectiveness(self, attacker_type, defender_type, attacker_level):
        """Calculate type effectiveness multiplier based on attacker level"""
        # Type effectiveness chart
        # grass > water > fire > snow > grass
        effectiveness = {
            'grass': {'water': True},
            'water': {'fire': True},
            'fire': {'snow': True},
            'snow': {'grass': True},
            'none': {}
        }
        
        if attacker_type in effectiveness and defender_type in effectiveness[attacker_type]:
            # Determine multiplier based on attacker level
            if attacker_level <= 25:
                return 2.0
            elif attacker_level <= 50:
                return 2.5
            else:  # 51+
                return 3.0
        return 1.0
    
    def on_fight_click(self):
        if not self.is_player_turn or self.battle_over or self.waiting_for_action:
            return
        
        # Player attacks - damage is player's atk (+ temp boost) minus enemy's def
        current_atk = self.player_atk + self.temp_atk_boost
        type_multiplier = self.get_type_effectiveness(self.player_attribute, self.enemy_attribute, self.player_level)
        damage = max(1, int(current_atk * type_multiplier) - self.enemy_def)  # At least 1 damage
        self.enemy_hp -= damage
        
        if self.temp_atk_boost > 0:
            self.action_message = f"{self.player_monster_name} dealt {damage} damage (ATK boosted)!"
            self.temp_atk_boost = 0  # Reset temp boost after use
        elif type_multiplier > 1.0:
            self.action_message = f"{self.player_monster_name} dealt {damage} damage (Super effective!)!"
        else:
            self.action_message = f"{self.player_monster_name} dealt {damage} damage!"
        self.message_timer = 3.0
        self.waiting_for_action = True
        
        if self.enemy_hp <= 0:
            self.enemy_hp = 0
            self.battle_over = True
            self.player_won = True
            self.action_message = f"Victory! {self.enemy_monster_name} fainted!"
        else:
            self.is_player_turn = False
    
    def on_item_click(self):
        if not self.is_player_turn or self.battle_over or self.waiting_for_action:
            return
        
        if self.game_manager is None:
            return
        
        # Show item overlay
        self.item_overlay_active = True
    
    def on_item_overlay_back(self):
        """Close item overlay"""
        self.item_overlay_active = False
        self.item_buttons = []
    
    def use_item(self, item_name):
        """Use an item from the bag"""
        if self.game_manager is None:
            return
        
        # Find item in bag
        item_found = None
        for item in self.game_manager.bag._items_data:
            if item['name'] == item_name and item['count'] > 0:
                item_found = item
                break
        
        if item_found is None:
            self.action_message = f"No {item_name} available!"
            self.message_timer = 1.5
            self.item_overlay_active = False
            return
        
        # Apply item effect
        if item_name == 'HealPotion':
            # Restore 20 HP
            heal_amount = 20
            old_hp = self.player_hp
            self.player_hp = min(self.player_max_hp, self.player_hp + heal_amount)
            actual_heal = self.player_hp - old_hp
            self.action_message = f"Used HealPotion! Restored {actual_heal} HP!"
        elif item_name == 'AtkPotion':
            # Increase attack by 15 for this turn only
            self.temp_atk_boost = 15
            self.action_message = f"Used AtkPotion! Attack increased by 15 for this turn!"
        elif item_name == 'DefPotion':
            # Increase defense by 10 for the entire battle
            self.def_boost += 10
            self.action_message = f"Used DefPotion! Defense increased by 10!"
        
        # Decrease item count
        item_found['count'] -= 1
        
        # Close overlay and set timer
        self.item_overlay_active = False
        self.item_buttons = []
        self.message_timer = 3.0
        self.waiting_for_action = True
    
    def on_switch_click(self):
        if not self.is_player_turn or self.battle_over or self.waiting_for_action:
            return
        
        if self.game_manager is None:
            return
        
        monsters = self.game_manager.bag._monsters_data
        if len(monsters) <= 1:
            self.action_message = "No other monsters to switch to!"
            self.message_timer = 1.5
            return
        
        # Switch to next monster
        self.current_monster_index = (self.current_monster_index + 1) % len(monsters)
        self.load_current_monster()
        
        self.action_message = f"Go, {self.player_monster_name}!"
        self.message_timer = 3.0
        self.waiting_for_action = True
        # Don't change turn - switching doesn't consume turn
    
    def on_run_click(self):
        if not self.is_player_turn or self.battle_over or self.waiting_for_action:
            return
        
        # Run away - return to game
        scene_manager.change_scene("game")
    
    def enemy_turn(self):
        if self.waiting_for_action or self.battle_over:
            return
        
        # Enemy attacks - damage is enemy's atk minus player's def (+ def boost)
        current_def = self.player_def + self.def_boost
        type_multiplier = self.get_type_effectiveness(self.enemy_attribute, self.player_attribute, self.enemy_level)
        damage = max(1, int(self.enemy_atk * type_multiplier) - current_def)  # At least 1 damage
        self.player_hp -= damage
        
        if type_multiplier > 1.0:
            self.action_message = f"{self.enemy_monster_name} attacked! You took {damage} damage (Super effective!)!"
        else:
            self.action_message = f"{self.enemy_monster_name} attacked! You took {damage} damage!"
        self.message_timer = 3.0
        self.waiting_for_action = True
        
        if self.player_hp <= 0:
            self.player_hp = 0
            self.battle_over = True
            self.player_won = False
            self.action_message = f"{self.player_monster_name} fainted! You lost..."
        else:
            self.is_player_turn = True
            # Don't show buttons until message timer finishes
    
    @override
    def enter(self) -> None:
        # Get reference to game manager from game scene
        from src.core.services import scene_manager
        game_scene = scene_manager._scenes.get("game")
        if game_scene and hasattr(game_scene, 'game_manager'):
            self.game_manager = game_scene.game_manager
        
        # Check if this is a wild battle
        if game_scene and hasattr(game_scene, 'wild_pokemon_name') and game_scene.wild_pokemon_name:
            self.is_wild_battle = True
            self.wild_pokemon_name = game_scene.wild_pokemon_name
            # Select random enemy from enemy_list for wild battle
            enemy = random.choice(self.enemy_list)
            self.enemy_monster_name = enemy['name']
            self.enemy_level = random.randint(5, 15)
            self.enemy_max_hp = 50 + self.enemy_level * 10
            self.enemy_hp = self.enemy_max_hp
            self.enemy_atk = 20 + (self.enemy_level - 1) * 2
            self.enemy_def = 10 + (self.enemy_level - 1)
            self.enemy_attribute = enemy['attribute']
            
            # Load enemy sprite for wild battle
            try:
                enemy_sprite_path = f"C:\\Users\\kllx\\Desktop\\NTHU-I2P-I-Final-Project-2025-main\\assets\\images\\{enemy['sprite_path']}"
                self.enemy_monster_sprite = pg.image.load(enemy_sprite_path).convert_alpha()
                self.enemy_sprite = pg.transform.scale(self.enemy_monster_sprite, (200, 200))
            except Exception:
                pass
        else:
            self.is_wild_battle = False
            # Random trainer battle - select random enemy from list
            enemy = random.choice(self.enemy_list)
            self.enemy_monster_name = enemy['name']
            self.enemy_level = random.randint(1, 100)  # Random level from 1-100
            self.enemy_max_hp = self.enemy_level * 5  # max_hp = level * 5
            self.enemy_hp = self.enemy_max_hp
            self.enemy_atk = 20 + (self.enemy_level - 1) * 2
            self.enemy_def = 10 + (self.enemy_level - 1)
            self.enemy_attribute = enemy['attribute']
            
            # Load enemy sprite
            try:
                enemy_sprite_path = f"C:\\Users\\kllx\\Desktop\\NTHU-I2P-I-Final-Project-2025-main\\assets\\images\\{enemy['sprite_path']}"
                self.enemy_monster_sprite = pg.image.load(enemy_sprite_path).convert_alpha()
                self.enemy_sprite = pg.transform.scale(self.enemy_monster_sprite, (200, 200))
            except Exception:
                pass
        
        # Load first monster from bag
        self.current_monster_index = 0
        self.load_current_monster()
        
        # Reset battle state when entering
        self.is_player_turn = True
        self.battle_over = False
        self.player_won = False
        self.waiting_for_action = False
        self.show_buttons = True
        self.action_message = f"What will {self.player_monster_name} do?"
        self.message_timer = 0
        self.item_overlay_active = False
        self.item_buttons = []
        
        # Reset buffs
        self.temp_atk_boost = 0
        self.def_boost = 0
    
    @override
    def exit(self) -> None:
        # Save current monster HP back to bag when exiting battle
        if self.game_manager is not None:
            monsters = self.game_manager.bag._monsters_data
            if len(monsters) > 0 and self.current_monster_index < len(monsters):
                # If current monster's HP is 0 or below, remove it from bag
                if self.player_hp <= 0:
                    monsters.pop(self.current_monster_index)
                else:
                    # Save HP and increase level if won
                    monsters[self.current_monster_index]['hp'] = self.player_hp
                    
                    # If player won, increase level of current monster by 1
                    if self.player_won:
                        monsters[self.current_monster_index]['level'] += 1
                        # Increase HP and max HP by 5
                        monsters[self.current_monster_index]['hp'] += 5
                        monsters[self.current_monster_index]['max_hp'] += 5
                        # Increase atk by 2 and def by 1
                        monsters[self.current_monster_index]['atk'] = monsters[self.current_monster_index].get('atk', 20) + 2
                        monsters[self.current_monster_index]['def'] = monsters[self.current_monster_index].get('def', 10) + 1
                        
                        # Check for evolution
                        current_name = monsters[self.current_monster_index]['name']
                        current_level = monsters[self.current_monster_index]['level']
                        
                        # Pikachu evolves to Charizard at level 26
                        if current_name == "Pikachu" and current_level >= 26:
                            monsters[self.current_monster_index]['name'] = "Charizard"
                            monsters[self.current_monster_index]['sprite_path'] = "menu_sprites/menusprite2.png"
                        # Charizard evolves to Blastoise at level 51
                        elif current_name == "Charizard" and current_level >= 51:
                            monsters[self.current_monster_index]['name'] = "Blastoise"
                            monsters[self.current_monster_index]['sprite_path'] = "menu_sprites/menusprite3.png"
                        # Kevin evolves to LeBron at level 26
                        elif current_name == "Kevin" and current_level >= 26:
                            monsters[self.current_monster_index]['name'] = "LeBron"
                            monsters[self.current_monster_index]['sprite_path'] = "menu_sprites/menusprite8.png"
                        # LeBron evolves to Steph at level 51
                        elif current_name == "LeBron" and current_level >= 51:
                            monsters[self.current_monster_index]['name'] = "Steph"
                            monsters[self.current_monster_index]['sprite_path'] = "menu_sprites/menusprite9.png"
                        # Durant evolves to James at level 26
                        elif current_name == "Durant" and current_level >= 26:
                            monsters[self.current_monster_index]['name'] = "James"
                            monsters[self.current_monster_index]['sprite_path'] = "menu_sprites/menusprite13.png"
                        # James evolves to Curry at level 51
                        elif current_name == "James" and current_level >= 51:
                            monsters[self.current_monster_index]['name'] = "Curry"
                            monsters[self.current_monster_index]['sprite_path'] = "menu_sprites/menusprite14.png"
            
            # If wild battle and player won, add the caught pokemon to bag
            if self.is_wild_battle and self.player_won and self.wild_pokemon_name:
                new_pokemon = {
                    'name': self.wild_pokemon_name,
                    'hp': self.enemy_max_hp,
                    'max_hp': self.enemy_max_hp,
                    'level': self.enemy_level,
                    'sprite_path': 'menu_sprites/menusprite5.png',
                    'atk': 20 + (self.enemy_level - 1) * 2,
                    'def': 10 + (self.enemy_level - 1)
                }
                monsters.append(new_pokemon)
        
        # Clear wild pokemon data from game scene
        from src.core.services import scene_manager
        game_scene = scene_manager._scenes.get("game")
        if game_scene and hasattr(game_scene, 'wild_pokemon_name'):
            game_scene.wild_pokemon_name = None
    
    @override
    def update(self, dt: float):
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.waiting_for_action = False
                # After message timer, if it's enemy turn and battle not over, enemy attacks
                if not self.is_player_turn and not self.battle_over:
                    self.enemy_turn()
                # If still player turn (item/switch used), restore action message
                elif self.is_player_turn and not self.battle_over:
                    self.action_message = f"What will {self.player_monster_name} do?"
        
        # Check button hover
        mouse_pos = input_manager.mouse_pos
        self.hovered_button = None
        
        # Handle item overlay
        if self.item_overlay_active:
            # Update item buttons
            for btn in self.item_buttons:
                btn.update(dt)
            return  # Don't process other buttons when overlay is active
        
        if self.show_buttons and not self.battle_over:
            if self.fight_button_rect.collidepoint(mouse_pos):
                self.hovered_button = "fight"
                if input_manager.mouse_pressed(1):
                    self.on_fight_click()
            elif self.item_button_rect.collidepoint(mouse_pos):
                self.hovered_button = "item"
                if input_manager.mouse_pressed(1):
                    self.on_item_click()
            elif self.switch_button_rect.collidepoint(mouse_pos):
                self.hovered_button = "switch"
                if input_manager.mouse_pressed(1):
                    self.on_switch_click()
            elif self.run_button_rect.collidepoint(mouse_pos):
                self.hovered_button = "run"
                if input_manager.mouse_pressed(1):
                    self.on_run_click()
        
        # Allow ESC key to exit battle
        if input_manager.key_pressed(pg.K_ESCAPE):
            scene_manager.change_scene("game")
        
        # Continue after battle with any key
        if self.battle_over and input_manager.key_pressed(pg.K_SPACE):
            scene_manager.change_scene("game")
    
    @override
    def draw(self, screen: pg.Surface):
        # Draw background
        if self.background is not None:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((40, 40, 60))
        
        # Draw enemy monster sprite (top center-right)
        if self.enemy_sprite is not None:
            enemy_x = GameSettings.SCREEN_WIDTH - 350
            enemy_y = 120
            screen.blit(self.enemy_sprite, (enemy_x, enemy_y))
        
        # Draw player monster sprite (bottom left)
        if self.player_sprite is not None:
            player_x = 100
            player_y = GameSettings.SCREEN_HEIGHT - 380
            screen.blit(self.player_sprite, (player_x, player_y))
        
        # Draw enemy info card (top right)
        self.draw_monster_card(screen, self.enemy_monster_name, self.enemy_hp, self.enemy_max_hp, 
                              self.enemy_level, self.enemy_atk, self.enemy_def, self.enemy_attribute, GameSettings.SCREEN_WIDTH - 320, 30, True)
        
        # Draw player info card (above player sprite)
        player_card_y = GameSettings.SCREEN_HEIGHT - 500
        self.draw_monster_card(screen, self.player_monster_name, self.player_hp, self.player_max_hp,
                              self.player_level, self.player_atk, self.player_def, self.player_attribute, 20, player_card_y, False)
        
        # Draw dialog box at bottom
        dialog_box_height = 150
        dialog_y = GameSettings.SCREEN_HEIGHT - dialog_box_height
        pg.draw.rect(screen, (40, 40, 40), (0, dialog_y, GameSettings.SCREEN_WIDTH, dialog_box_height))
        pg.draw.rect(screen, (200, 200, 200), (0, dialog_y, GameSettings.SCREEN_WIDTH, 3))
        
        # Draw dialog text
        if self.dialog_font is not None:
            dialog_text = self.dialog_font.render(self.action_message, True, (255, 255, 255))
            screen.blit(dialog_text, (30, dialog_y + 20))
        
        # Draw action buttons
        if self.show_buttons and not self.battle_over:
            self.draw_button(screen, self.fight_button_rect, "Fight", self.hovered_button == "fight")
            self.draw_button(screen, self.item_button_rect, "Item", self.hovered_button == "item")
            self.draw_button(screen, self.switch_button_rect, "Switch", self.hovered_button == "switch")
            self.draw_button(screen, self.run_button_rect, "Run", self.hovered_button == "run")
        elif self.battle_over:
            # Draw "Press SPACE to continue" message
            if self.dialog_font is not None:
                continue_text = self.hp_font.render("Press SPACE to continue", True, (200, 200, 200))
                continue_rect = continue_text.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, dialog_y + 100))
                screen.blit(continue_text, continue_rect)
        
        # Draw item overlay
        if self.item_overlay_active:
            self.draw_item_overlay(screen)
    
    def draw_monster_card(self, screen, name, hp, max_hp, level, atk, defense, attribute, x, y, is_enemy):
        # Card background - increased height to fit atk/def
        card_width = 280
        card_height = 120
        pg.draw.rect(screen, (255, 255, 255), (x, y, card_width, card_height))
        pg.draw.rect(screen, (0, 0, 0), (x, y, card_width, card_height), 3)
        
        # Monster icon placeholder (small square on left)
        icon_size = 70
        icon_x = x + 10
        icon_y = y + 10
        pg.draw.rect(screen, (100, 100, 100), (icon_x, icon_y, icon_size, icon_size))
        pg.draw.rect(screen, (0, 0, 0), (icon_x, icon_y, icon_size, icon_size), 2)
        
        # Draw monster sprite in icon
        sprite_to_use = self.enemy_monster_sprite if is_enemy else self.monster_sprite
        if sprite_to_use is not None:
            try:
                small_sprite = pg.transform.scale(sprite_to_use, (icon_size - 4, icon_size - 4))
                screen.blit(small_sprite, (icon_x + 2, icon_y + 2))
            except:
                pass
        
        # Name and level
        text_x = icon_x + icon_size + 15
        if self.card_font is not None:
            name_text = self.card_font.render(name, True, (0, 0, 0))
            screen.blit(name_text, (text_x, y + 12))
            
            level_text = self.card_font.render(f"Lv:{level}", True, (0, 0, 0))
            level_rect = level_text.get_rect(right=x + card_width - 10, top=y + 12)
            screen.blit(level_text, level_rect)
            
            # Display attribute with color coding
            attribute_colors = {
                'grass': (80, 200, 80),
                'water': (60, 120, 220),
                'fire': (220, 80, 60),
                'snow': (150, 200, 255),
                'none': (150, 150, 150)
            }
            attr_color = attribute_colors.get(attribute, (150, 150, 150))
            attr_text = self.hp_font.render(f"[{attribute.upper()}]", True, attr_color)
            screen.blit(attr_text, (text_x, y + 32))
        
        # HP bar
        hp_bar_x = text_x
        hp_bar_y = y + 48
        hp_bar_width = card_width - (text_x - x) - 15
        hp_bar_height = 16
        
        # HP bar background (red)
        pg.draw.rect(screen, (200, 50, 50), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
        
        # HP bar foreground (green/yellow/red based on HP)
        hp_ratio = max(0, hp / max_hp)
        if hp_ratio > 0.5:
            hp_color = (80, 200, 80)
        elif hp_ratio > 0.2:
            hp_color = (220, 180, 60)
        else:
            hp_color = (200, 50, 50)
        
        pg.draw.rect(screen, hp_color, (hp_bar_x, hp_bar_y, int(hp_bar_width * hp_ratio), hp_bar_height))
        pg.draw.rect(screen, (0, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), 2)
        
        # HP text
        if self.hp_font is not None:
            hp_text = self.hp_font.render(f"{hp}/{max_hp}", True, (0, 0, 0))
            screen.blit(hp_text, (hp_bar_x + 5, hp_bar_y + 20))
            
            # ATK and DEF text
            atk_def_y = hp_bar_y + 38
            atk_text = self.hp_font.render(f"ATK:{atk}", True, (220, 60, 60))
            def_text = self.hp_font.render(f"DEF:{defense}", True, (60, 120, 220))
            screen.blit(atk_text, (hp_bar_x, atk_def_y))
            screen.blit(def_text, (hp_bar_x + 90, atk_def_y))
            
            # Show type effectiveness indicator
            if is_enemy:
                # Check if player has advantage over enemy
                multiplier = self.get_type_effectiveness(self.player_attribute, self.enemy_attribute, self.player_level)
                if multiplier > 1.0:
                    if self.exclamation_icon is not None:
                        screen.blit(self.exclamation_icon, (x + card_width - 30, atk_def_y + 10))
                # Check if enemy has advantage over player
                enemy_multiplier = self.get_type_effectiveness(self.enemy_attribute, self.player_attribute, self.enemy_level)
                if enemy_multiplier > 1.0:
                    if self.exclamation_icon is not None:
                        screen.blit(self.exclamation_icon, (x + card_width - 30, atk_def_y + 10))
            else:
                # Check if enemy has advantage over player
                multiplier = self.get_type_effectiveness(self.enemy_attribute, self.player_attribute, self.enemy_level)
                if multiplier > 1.0:
                    if self.exclamation_icon is not None:
                        screen.blit(self.exclamation_icon, (x + 10, atk_def_y + 18))
                # Check if player has advantage over enemy
                player_multiplier = self.get_type_effectiveness(self.player_attribute, self.enemy_attribute, self.player_level)
                if player_multiplier > 1.0:
                    if self.exclamation_icon is not None:
                        screen.blit(self.exclamation_icon, (x + 10, atk_def_y + 18))
    
    def draw_button(self, screen, rect, text, is_hovered):
        # Button background
        if is_hovered:
            color = (255, 180, 100)
            border_color = (255, 255, 255)
        else:
            color = (255, 255, 255)
            border_color = (100, 100, 100)
        
        pg.draw.rect(screen, color, rect)
        pg.draw.rect(screen, border_color, rect, 3)
        
        # Button text
        if self.button_font is not None:
            text_surf = self.button_font.render(text, True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)
    
    def draw_item_overlay(self, screen):
        """Draw item selection overlay"""
        if self.overlay_img is None or self.game_manager is None:
            return
        
        # Draw overlay background
        overlay_img_scaled = pg.transform.scale(
            self.overlay_img,
            (self.overlay_img.get_width() * 8, self.overlay_img.get_height() * 8)
        )
        overlay_rect = overlay_img_scaled.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2))
        screen.blit(overlay_img_scaled, overlay_rect)
        
        # Title
        if self.dialog_font is not None:
            title_text = self.dialog_font.render("Select Item", True, (255, 255, 255))
            title_x = overlay_rect.centerx - title_text.get_width() // 2
            title_y = overlay_rect.top + 30
            screen.blit(title_text, (title_x, title_y))
        
        # Get items from bag
        items = self.game_manager.bag._items_data
        potion_items = [item for item in items if 'Potion' in item['name']]
        
        # Clear and recreate buttons
        self.item_buttons = []
        
        y_offset = overlay_rect.top + 100
        content_left = overlay_rect.left + 100
        
        if potion_items:
            for item_data in potion_items:
                if self.card_font is not None:
                    # Draw item name and count
                    text = f"{item_data['name']} x{item_data['count']}"
                    text_surf = self.card_font.render(text, True, (255, 255, 255))
                    screen.blit(text_surf, (content_left, y_offset))
                    
                    # Create use button (no hover effect)
                    btn_x = overlay_rect.right - 180
                    btn_y = y_offset - 5
                    btn = Button(
                        img_path="UI/raw/UI_Flat_ButtonCheck01a.png",
                        img_hovered_path="UI/raw/UI_Flat_ButtonCheck01a.png",
                        x=btn_x,
                        y=btn_y,
                        width=40,
                        height=40,
                        on_click=lambda name=item_data['name']: self.use_item(name)
                    )
                    btn.update(0)
                    btn.draw(screen)
                    self.item_buttons.append(btn)
                    
                    y_offset += 60
        else:
            if self.card_font is not None:
                no_items_text = self.card_font.render("No items available", True, (150, 150, 150))
                screen.blit(no_items_text, (content_left, y_offset))
        
        # Draw back button in bottom left corner
        back_btn_x = overlay_rect.left + 20
        back_btn_y = overlay_rect.bottom - 120
        back_btn = Button(
            img_path="UI/button_back.png",
            img_hovered_path="UI/button_back_hover.png",
            x=back_btn_x,
            y=back_btn_y,
            width=100,
            height=100,
            on_click=self.on_item_overlay_back
        )
        back_btn.update(0)
        back_btn.draw(screen)
        self.item_buttons.append(back_btn)
