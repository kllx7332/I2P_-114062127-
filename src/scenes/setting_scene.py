'''
[TODO HACKATHON 5]
Try to mimic the menu_scene.py or game_scene.py to create this new scene
'''
import pygame as pg

from src.scenes.scene import Scene
from src.utils import GameSettings
from src.sprites import BackgroundSprite, Sprite
from src.interface.components import Button
from src.core.services import scene_manager, input_manager
from typing import override

class SettingScene(Scene):
    background: BackgroundSprite
    back_button: Button

    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background1.png")

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            px, py, 100, 100,
            lambda: scene_manager.change_scene("menu")
        )
        # replicate ingame overlay UI (excluding the overlay back button)
        # checkbox paths
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

        # slider resources
        self.slider_track_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_BarFill01f.png"
        self.slider_knob_path = r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_FrameSlot03b.png"
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

        # overlay image
        try:
            self.overlay_img = pg.image.load(r"C:\Users\kllx\Desktop\NTHU-I2P-I-Final-Project-2025-main\assets\images\UI\raw\UI_Flat_Frame03a.png").convert_alpha()
        except Exception:
            self.overlay_img = None
        self.overlay_active = True
        self.overlay_scale = 5

        # font for UI labels
        try:
            self.ui_font = pg.font.SysFont(None, 56)
        except Exception:
            self.ui_font = None
    def on_checkbox_click(self):
        # toggle checkbox state and update sprite
        self.checkbox_checked = not getattr(self, 'checkbox_checked', False)
        new_path = self.checkbox_checked_path if self.checkbox_checked else self.checkbox_unchecked_path
        # recreate sprites at button size
        self.checkbox_button.img_button_default = Sprite(new_path, (self.checkbox_button.hitbox.width, self.checkbox_button.hitbox.height))
        self.checkbox_button.img_button_hover = Sprite(new_path, (self.checkbox_button.hitbox.width, self.checkbox_button.hitbox.height))
        self.checkbox_button.img_button = self.checkbox_button.img_button_default

    @override
    def enter(self) -> None:
        pass

    @override
    def exit(self) -> None:
        pass

    @override
    def update(self, dt: float) -> None:
        self.back_button.update(dt)
        # overlay interaction
        if self.overlay_active:
            self.checkbox_button.update(dt)
            # slider input handling
            if self.overlay_img is not None and self.slider_track_img is not None and self.slider_knob_img is not None:
                ow = int(self.overlay_img.get_width() * self.overlay_scale)
                oh = int(self.overlay_img.get_height() * self.overlay_scale)
                overlay_rect = pg.Rect(0, 0, ow, oh)
                overlay_rect.center = (GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2)
                track_width = int(overlay_rect.width * 0.6)
                track_height = int(self.slider_track_img.get_height() * (track_width / max(1, self.slider_track_img.get_width())))
                track_left = overlay_rect.centerx - track_width // 2
                # account for audio label width
                text_width = 0
                if self.ui_font:
                    try:
                        text_width = self.ui_font.size("Audio")[0]
                    except Exception:
                        text_width = 0
                min_track_left = overlay_rect.left + 10 + text_width + 20
                if track_left < min_track_left:
                    track_left = min_track_left
                track_top = overlay_rect.top + int(overlay_rect.height * 0.08)
                knob_h = int(overlay_rect.height * 0.12)
                knob_w = knob_h
                knob_x = int(track_left + self.slider_value * (track_width - knob_w))
                knob_y = track_top - (knob_h - track_height) // 2
                knob_rect = pg.Rect(knob_x, knob_y, knob_w, knob_h)
                mx, my = input_manager.mouse_pos
                if input_manager.mouse_pressed(1) and knob_rect.collidepoint((mx, my)):
                    self.slider_dragging = True
                if self.slider_dragging and input_manager.mouse_down(1):
                    rel_x = mx - track_left
                    self.slider_value = max(0.0, min(1.0, rel_x / max(1, track_width - knob_w)))
                    # Update audio volume (0-100)
                    from src.core.services import sound_manager
                    GameSettings.AUDIO_VOLUME = self.slider_value
                    # Set current BGM volume if playing
                    if hasattr(sound_manager, 'current_bgm') and sound_manager.current_bgm:
                        sound_manager.current_bgm.set_volume(GameSettings.AUDIO_VOLUME)
                if input_manager.mouse_released(1):
                    self.slider_dragging = False

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        # draw replicated ingame overlay UI (excluding overlay back button)
        if self.overlay_active and self.overlay_img is not None:
            overlay_img_scaled = pg.transform.scale(self.overlay_img, (self.overlay_img.get_width() * self.overlay_scale, self.overlay_img.get_height() * self.overlay_scale))
            overlay_rect = overlay_img_scaled.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2))
            screen.blit(overlay_img_scaled, overlay_rect)
            # move back_button to overlay left-bottom
            self.back_button.hitbox.x = overlay_rect.left + 20
            self.back_button.hitbox.y = overlay_rect.bottom - self.back_button.hitbox.height - 20
            # checkbox center
            self.checkbox_button.hitbox.x = overlay_rect.centerx - self.checkbox_button.hitbox.width // 2
            self.checkbox_button.hitbox.y = overlay_rect.centery - self.checkbox_button.hitbox.height // 2
            # draw mute label
            if self.ui_font is not None:
                label = "mute: on" if getattr(self, 'checkbox_checked', False) else "mute: off"
                text_surf = self.ui_font.render(label, True, (255, 255, 255))
                preferred_x = overlay_rect.left + 20
                max_x = self.checkbox_button.hitbox.left - text_surf.get_width() - 10
                text_x = min(preferred_x, max_x)
                if text_x < overlay_rect.left + 10:
                    text_x = overlay_rect.left + 10
                text_y = self.checkbox_button.hitbox.top + (self.checkbox_button.hitbox.height - text_surf.get_height()) // 2
                screen.blit(text_surf, (text_x, text_y))
            # draw checkbox
            self.checkbox_button.draw(screen)
            # draw slider
            if self.slider_track_img is not None and self.slider_knob_img is not None:
                track_width = int(overlay_rect.width * 0.6)
                track_height = int(self.slider_track_img.get_height() * (track_width / max(1, self.slider_track_img.get_width())))
                track_left = overlay_rect.centerx - track_width // 2
                text_width = 0
                if self.ui_font is not None:
                    try:
                        text_width = self.ui_font.size("Audio")[0]
                    except Exception:
                        text_width = 0
                min_track_left = overlay_rect.left + 10 + text_width + 20
                if track_left < min_track_left:
                    track_left = min_track_left
                track_top = overlay_rect.top + int(overlay_rect.height * 0.08)
                knob_h = int(overlay_rect.height * 0.12)
                knob_w = knob_h
                track_surf = pg.transform.scale(self.slider_track_img, (track_width, max(1, track_height)))
                knob_surf = pg.transform.scale(self.slider_knob_img, (knob_w, knob_h))
                # draw audio label
                if self.ui_font is not None:
                    audio_label = "Audio"
                    text_surf = self.ui_font.render(audio_label, True, (255, 255, 255))
                    text_x = track_left - text_surf.get_width() - 10
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
            # draw back_button on top of overlay so it is not covered
            self.back_button.draw(screen)
        else:
            # if overlay not active, draw back_button normally
            self.back_button.draw(screen)