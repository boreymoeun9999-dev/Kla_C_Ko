from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import cv2
import pygame
from cv2.typing import MatLike

from src.config import (
    ASSET_DIR,
    BACKGROUND_ASSET_DIR,
    BOARD_LEFT,
    BOARD_PIXELS,
    BOARD_TOP,
    CELL_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.game_rules import BOARD_SIZE, legal_cow_moves, legal_tiger_moves
from src.game_state import TIGER_WIN_CAPTURES, TOTAL_COWS, GameState


BACKGROUND = (221, 234, 207)
SUN_GLOW = (247, 211, 135, 105)
TRACK_COLOR = (106, 139, 82, 34)
NAVY = (35, 51, 74)
MUTED = (64, 79, 101)
ACCENT = (61, 133, 205)
TIGER_COLOR = (225, 125, 43)
TIGER_PALE = (255, 232, 202)
COW_COLOR = (57, 151, 125)
COW_PALE = (219, 243, 231)
WHITE = (255, 255, 255)
CELL_LIGHT = (250, 251, 253)
CELL_DARK = (231, 236, 243)


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.title_font = pygame.font.Font(None, 42)
        self.cover_title_font = pygame.font.Font(None, 82)
        self.cover_subtitle_font = pygame.font.Font(None, 32)
        self.versus_font = pygame.font.Font(None, 68)
        self.versus_font.set_bold(True)
        self.congratulations_font = pygame.font.Font(None, 52)
        self.body_font = pygame.font.Font(None, 25)
        self.small_font = pygame.font.Font(None, 21)
        self.backgrounds = {
            "start": self._load_soft_background(
                BACKGROUND_ASSET_DIR / "start-angkor.png", (255, 248, 226, 92)
            ),
            "game": self._load_soft_background(
                BACKGROUND_ASSET_DIR / "game-angkor.png", (221, 234, 207, 105)
            ),
        }
        self.background_details = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(self.background_details, SUN_GLOW, (84, 96), 44)
        self._draw_pawprint((318, 350))
        self._draw_pawprint((1042, 515))
        self.images = {
            name: pygame.image.load(ASSET_DIR / filename).convert_alpha()
            for name, filename in {
                "tiger": "tiger_face.png",
                "cow": "cow_face.png",
                "frame": "selection_frame.png",
                "restart": "restart_button.png",
                "close": "close_button.png",
            }.items()
        }
        self.images["tiger"] = pygame.transform.smoothscale(self.images["tiger"], (92, 92))
        self.images["cow"] = pygame.transform.smoothscale(self.images["cow"], (92, 92))
        self.images["frame"] = pygame.transform.smoothscale(self.images["frame"], (CELL_SIZE, CELL_SIZE))
        self.images["restart"] = pygame.transform.smoothscale(self.images["restart"], (54, 54))
        self.images["close"] = pygame.transform.smoothscale(self.images["close"], (54, 54))
        self.restart_rect = pygame.Rect(WINDOW_WIDTH - 124, 19, 54, 54)
        self.close_rect = pygame.Rect(WINDOW_WIDTH - 58, 19, 54, 54)
        self.home_rect = pygame.Rect(WINDOW_WIDTH - 190, WINDOW_HEIGHT - 66, 170, 46)
        self.start_button_rect = pygame.Rect(0, 0, 300, 76)
        self.start_button_rect.center = (WINDOW_WIDTH // 2, 566)
        self.name_field_rects = {
            "tiger": pygame.Rect(0, 0, 270, 42),
            "cow": pygame.Rect(0, 0, 270, 42),
        }
        panel = pygame.Rect(0, 0, 1040, 600)
        panel.center = self.screen.get_rect().center
        for player, offset in (("tiger", -250), ("cow", 250)):
            self.name_field_rects[player].center = (
                panel.centerx + offset,
                panel.top + 370,
            )
        self.player_name_inputs = {"tiger": "", "cow": ""}
        self.active_name_field: str | None = "tiger"
        self.music_rect = pygame.Rect(WINDOW_WIDTH - 364, 24, 150, 40)
        self.music_label = "Choose song"
        self.music_toggle_rect = pygame.Rect(WINDOW_WIDTH - 196, 24, 68, 40)
        self.music_paused = False
        self.sound_settings_rect = pygame.Rect(WINDOW_WIDTH - 520, 24, 136, 40)
        self.sound_settings_open = False
        self.sound_volume = 0.7
        self.sound_muted = False
        self.player_sound_labels = {"tiger": "Generated", "cow": "Generated"}
        self.settings_panel_rect = pygame.Rect(0, 0, 500, 430)
        self.settings_panel_rect.center = self.screen.get_rect().center
        panel_left = self.settings_panel_rect.left
        panel_top = self.settings_panel_rect.top
        self.settings_tiger_rect = pygame.Rect(panel_left + 30, panel_top + 110, 208, 48)
        self.settings_cow_rect = pygame.Rect(panel_left + 262, panel_top + 110, 208, 48)
        self.settings_volume_down_rect = pygame.Rect(panel_left + 120, panel_top + 218, 70, 46)
        self.settings_volume_up_rect = pygame.Rect(panel_left + 310, panel_top + 218, 70, 46)
        self.settings_mute_rect = pygame.Rect(panel_left + 120, panel_top + 288, 260, 46)
        self.settings_close_rect = pygame.Rect(panel_left + 170, panel_top + 360, 160, 42)
        self.board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP, BOARD_PIXELS, BOARD_PIXELS)
        self.camera_rects = {
            "tiger": pygame.Rect(24, 246, 220, 165),
            "cow": pygame.Rect(WINDOW_WIDTH - 244, 246, 220, 165),
        }

    def _load_soft_background(
        self,
        path: Path,
        tint: tuple[int, int, int, int],
    ) -> pygame.Surface:
        image = pygame.image.load(path).convert()
        size = self.screen.get_size()
        reduced_size = (max(1, size[0] // 8), max(1, size[1] // 8))
        image = pygame.transform.smoothscale(image, reduced_size)
        image = pygame.transform.smoothscale(image, size)
        overlay = pygame.Surface(size, pygame.SRCALPHA)
        overlay.fill(tint)
        image.blit(overlay, (0, 0))
        return image

    def cell_at(self, position: tuple[int, int]) -> int | None:
        if not self.board_rect.collidepoint(position):
            return None
        col = (position[0] - BOARD_LEFT) // CELL_SIZE
        row = (position[1] - BOARD_TOP) // CELL_SIZE
        return row * BOARD_SIZE + col

    @property
    def player_names(self) -> dict[str, str]:
        return {
            player: self.player_name_inputs[player].strip() or f"{player.title()} Player"
            for player in ("tiger", "cow")
        }

    def focus_name_field(self, position: tuple[int, int]) -> bool:
        for player, rect in self.name_field_rects.items():
            if rect.collidepoint(position):
                self.active_name_field = player
                return True
        self.active_name_field = None
        return False

    def handle_name_input(
        self,
        event: pygame.event.Event,
        allow_key_text: bool = True,
    ) -> None:
        player = self.active_name_field
        if player is None:
            return
        if event.type == pygame.TEXTINPUT:
            name = self.player_name_inputs[player]
            self.player_name_inputs[player] = (
                name + "".join(character for character in event.text if character.isprintable())
            )[:18]
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.player_name_inputs[player] = self.player_name_inputs[player][:-1]
            elif event.key == pygame.K_TAB:
                self.active_name_field = "cow" if player == "tiger" else "tiger"
            elif event.key == pygame.K_RETURN:
                self.active_name_field = None
            elif allow_key_text:
                text = getattr(event, "unicode", "")
                if text and text.isprintable():
                    name = self.player_name_inputs[player]
                    self.player_name_inputs[player] = (name + text)[:18]

    def draw(
        self,
        state: GameState,
        cursor: tuple[int, int] | None,
        camera_frames: Mapping[str, MatLike | None],
        camera_messages: Mapping[str, str | None],
        camera_indices: Mapping[str, int | None],
    ) -> None:
        self.screen.blit(self.backgrounds["game"], (0, 0))
        self.screen.blit(self.background_details, (0, 0))
        self._draw_header(state)
        self._draw_music_button()
        self._draw_music_toggle_button()
        pygame.draw.rect(
            self.screen, (255, 248, 226), self.sound_settings_rect, border_radius=10
        )
        pygame.draw.rect(
            self.screen, NAVY, self.sound_settings_rect, width=2, border_radius=10
        )
        settings_label = self.small_font.render("Sound settings", True, NAVY)
        self.screen.blit(
            settings_label,
            settings_label.get_rect(center=self.sound_settings_rect.center),
        )
        self._draw_board(state, cursor)
        self._draw_player_panels(state, camera_frames, camera_messages, camera_indices)
        if cursor is not None:
            pygame.draw.circle(self.screen, ACCENT, cursor, 8, 2)
        if state.winner is not None:
            self._draw_congratulations(state.winner)
        if self.sound_settings_open:
            self._draw_sound_settings()

    def draw_start_screen(
        self,
        cursor: tuple[int, int] | None = None,
    ) -> None:
        self.screen.blit(self.backgrounds["start"], (0, 0))
        self.screen.blit(self.background_details, (0, 0))

        panel = pygame.Rect(0, 0, 1040, 600)
        panel.center = self.screen.get_rect().center

        title = self.cover_title_font.render("TIGER vs COW", True, NAVY)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + 93)))
        subtitle = self.cover_subtitle_font.render(
            "A strategy game for two players", True, MUTED
        )
        self.screen.blit(
            subtitle,
            subtitle.get_rect(center=(panel.centerx, panel.top + 150)),
        )

        character_size = (156, 156)
        tiger = pygame.transform.smoothscale(self.images["tiger"], character_size)
        cow = pygame.transform.smoothscale(self.images["cow"], character_size)
        for player, offset, color, pale in (
            ("tiger", -250, TIGER_COLOR, TIGER_PALE),
            ("cow", 250, COW_COLOR, COW_PALE),
        ):
            center = (panel.centerx + offset, panel.top + 258)
            pygame.draw.circle(self.screen, pale, center, 100)
            pygame.draw.circle(self.screen, color, center, 100, width=5)
            portrait = tiger if player == "tiger" else cow
            self.screen.blit(portrait, portrait.get_rect(center=center))

        self._draw_name_fields()
        self._draw_versus_badge((panel.centerx, panel.top + 258))

        instructions = self.body_font.render(
            "Click a name box and type. Press Tab to switch between players.",
            True,
            MUTED,
        )
        self.screen.blit(
            instructions,
            instructions.get_rect(center=(panel.centerx, panel.top + 414)),
        )

        pygame.draw.rect(
            self.screen, ACCENT, self.start_button_rect, border_radius=18
        )
        pygame.draw.rect(
            self.screen, NAVY, self.start_button_rect, width=3, border_radius=18
        )
        start_label = self.cover_subtitle_font.render("Start Game", True, WHITE)
        self.screen.blit(
            start_label,
            start_label.get_rect(center=self.start_button_rect.center),
        )
        hint = self.small_font.render(
            "Press Enter or click Start Game when both names are ready.",
            True,
            MUTED,
        )
        self.screen.blit(
            hint,
            hint.get_rect(center=(panel.centerx, panel.bottom - 24)),
        )
        if cursor is not None:
            pygame.draw.circle(self.screen, ACCENT, cursor, 23, 3)
            pygame.draw.circle(self.screen, WHITE, cursor, 7)

    def _draw_versus_badge(self, center: tuple[int, int]) -> None:
        badge = pygame.Rect(0, 0, 112, 112)
        badge.center = center
        pygame.draw.circle(
            self.screen,
            (174, 184, 194),
            (center[0] + 4, center[1] + 6),
            57,
        )
        pygame.draw.circle(self.screen, NAVY, center, 56)
        pygame.draw.circle(self.screen, (255, 248, 226), center, 50)
        pygame.draw.arc(self.screen, TIGER_COLOR, badge, 0.75, 2.45, width=7)
        pygame.draw.arc(self.screen, COW_COLOR, badge, 3.9, 5.6, width=7)

        shadow = self.versus_font.render("VS", True, (181, 190, 199))
        self.screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 3)))
        label = self.versus_font.render("VS", True, NAVY)
        self.screen.blit(label, label.get_rect(center=center))

    def _draw_name_fields(self) -> None:
        for player, rect in self.name_field_rects.items():
            color, pale = (
                (TIGER_COLOR, TIGER_PALE)
                if player == "tiger"
                else (COW_COLOR, COW_PALE)
            )
            pygame.draw.rect(self.screen, pale, rect, border_radius=12)
            pygame.draw.rect(
                self.screen,
                color if self.active_name_field == player else NAVY,
                rect,
                width=3 if self.active_name_field == player else 2,
                border_radius=12,
            )
            value = self.player_name_inputs[player]
            if value:
                label = value + ("|" if self.active_name_field == player else "")
                label_color = NAVY
            else:
                label = f"Enter {player} player name"
                label_color = MUTED
            label = self._fit_text(label, self.small_font, rect.width - 24)
            text = self.small_font.render(label, True, label_color)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_music_button(self) -> None:
        pygame.draw.rect(self.screen, (255, 248, 226), self.music_rect, border_radius=10)
        pygame.draw.rect(self.screen, NAVY, self.music_rect, width=2, border_radius=10)
        label_text = self.music_label
        while self.small_font.size(label_text)[0] > self.music_rect.width - 12:
            label_text = label_text[:-4] + "..."
        label = self.small_font.render(label_text, True, NAVY)
        self.screen.blit(label, label.get_rect(center=self.music_rect.center))

    def _draw_music_toggle_button(self) -> None:
        pygame.draw.rect(
            self.screen, (255, 248, 226), self.music_toggle_rect, border_radius=10
        )
        pygame.draw.rect(
            self.screen, NAVY, self.music_toggle_rect, width=2, border_radius=10
        )
        label = self.small_font.render(
            "Play" if self.music_paused else "Pause", True, NAVY
        )
        self.screen.blit(label, label.get_rect(center=self.music_toggle_rect.center))

    def _draw_sound_settings(self) -> None:
        veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        veil.fill((22, 34, 51, 155))
        self.screen.blit(veil, (0, 0))
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            self.settings_panel_rect,
            border_radius=22,
        )
        pygame.draw.rect(
            self.screen,
            (246, 190, 67),
            self.settings_panel_rect,
            width=5,
            border_radius=22,
        )
        title = self.congratulations_font.render("SOUND SETTINGS", True, NAVY)
        self.screen.blit(
            title,
            title.get_rect(center=(self.settings_panel_rect.centerx, self.settings_panel_rect.top + 54)),
        )
        self._settings_button(
            self.settings_tiger_rect,
            f"Tiger: {self.player_sound_labels['tiger']}",
        )
        self._settings_button(
            self.settings_cow_rect,
            f"Cow: {self.player_sound_labels['cow']}",
        )
        self._text(
            f"Volume: {round(self.sound_volume * 100)}%",
            self.settings_panel_rect.left + 205,
            self.settings_panel_rect.top + 230,
            self.body_font,
            NAVY,
        )
        self._settings_button(self.settings_volume_down_rect, "-")
        self._settings_button(self.settings_volume_up_rect, "+")
        self._settings_button(
            self.settings_mute_rect,
            "Unmute" if self.sound_muted else "Mute",
        )
        self._settings_button(self.settings_close_rect, "Close")
        help_text = self.small_font.render(
            "Choose a WAV, OGG, or MP3 sound file", True, MUTED
        )
        self.screen.blit(
            help_text,
            help_text.get_rect(center=(self.settings_panel_rect.centerx, self.settings_panel_rect.top + 178)),
        )

    def _settings_button(self, rect: pygame.Rect, text: str) -> None:
        pygame.draw.rect(self.screen, (255, 248, 226), rect, border_radius=10)
        pygame.draw.rect(self.screen, NAVY, rect, width=2, border_radius=10)
        label_text = text
        while self.small_font.size(label_text)[0] > rect.width - 12:
            label_text = label_text[:-4] + "..."
        label = self.small_font.render(label_text, True, NAVY)
        self.screen.blit(label, label.get_rect(center=rect.center))

    def _draw_pawprint(self, center: tuple[int, int]) -> None:
        x, y = center
        pygame.draw.ellipse(
            self.background_details,
            TRACK_COLOR,
            pygame.Rect(x - 18, y - 2, 36, 29),
        )
        for toe_x, toe_y in ((-17, -13), (-6, -22), (7, -22), (18, -13)):
            pygame.draw.circle(
                self.background_details,
                TRACK_COLOR,
                (x + toe_x, y + toe_y),
                8,
            )

    def _draw_congratulations(self, winner: str) -> None:
        veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        veil.fill((22, 34, 51, 155))
        self.screen.blit(veil, (0, 0))

        panel = pygame.Rect(0, 0, 520, 370)
        panel.center = self.screen.get_rect().center
        pygame.draw.rect(self.screen, (255, 255, 255), panel, border_radius=24)
        pygame.draw.rect(self.screen, (246, 190, 67), panel, width=6, border_radius=24)

        for x, y, color in (
            (-55, 54, (246, 190, 67)),
            (panel.width + 38, 82, (61, 133, 205)),
            (-42, panel.height - 68, (242, 143, 160)),
            (panel.width + 50, panel.height - 58, (93, 172, 112)),
        ):
            pygame.draw.circle(
                self.screen,
                color,
                (panel.left + x, panel.top + y),
                10,
            )

        if winner != "draw":
            portrait = pygame.transform.smoothscale(self.images[winner], (112, 112))
            self.screen.blit(
                portrait,
                portrait.get_rect(center=(panel.centerx, panel.top + 91)),
            )

        heading_text = "IT'S A DRAW!" if winner == "draw" else "CONGRATULATIONS!"
        heading = self.congratulations_font.render(heading_text, True, NAVY)
        self.screen.blit(
            heading,
            heading.get_rect(center=(panel.centerx, panel.top + 177)),
        )
        winner_name = self.player_names.get(winner, winner.title())
        result_text = (
            "Neither side can move."
            if winner == "draw"
            else f"{winner_name} wins!"
        )
        winner_color = COW_COLOR if winner == "cow" else TIGER_COLOR
        result = self.body_font.render(result_text, True, winner_color)
        self.screen.blit(
            result,
            result.get_rect(center=(panel.centerx, panel.top + 225)),
        )
        prompt = self.small_font.render(
            "Press R or click Restart to play again", True, MUTED
        )
        self.screen.blit(
            prompt,
            prompt.get_rect(center=(panel.centerx, panel.top + 286)),
        )

    def _draw_header(self, state: GameState) -> None:
        title = self.title_font.render("TIGER vs COW", True, NAVY)
        self.screen.blit(title, (BOARD_LEFT, 34))
        subtitle = self.small_font.render("4 Tigers vs 12 Cows", True, MUTED)
        self.screen.blit(subtitle, (BOARD_LEFT + 2, 79))
        if state.winner == "tiger":
            if state.cows_captured >= TIGER_WIN_CAPTURES:
                reason = f"ate all {TIGER_WIN_CAPTURES} Cows"
            else:
                reason = "the last Cow cannot move"
            status = f"{self.player_names['tiger']} wins - {reason}!"
            status_color = TIGER_COLOR
        elif state.winner == "cow":
            status = f"{self.player_names['cow']} wins - all Tigers trapped!"
            status_color = COW_COLOR
        elif state.winner == "draw":
            status = "Draw - neither side can move!"
            status_color = NAVY
        elif state.current_turn is not None:
            player = state.current_turn
            hand = "RIGHT" if player == "tiger" else "LEFT"
            status = f"{self.player_names[player].upper()}'S TURN - USE {hand} HAND"
            status_color = COW_COLOR if player == "cow" else TIGER_COLOR
        else:
            status = "Game over"
            status_color = NAVY
        status_font = (
            self.body_font
            if self.body_font.size(status)[0] <= self.board_rect.width - 24
            else self.small_font
        )
        status = self._fit_text(status, status_font, self.board_rect.width - 24)
        status_surface = status_font.render(status, True, status_color)
        status_position = status_surface.get_rect(center=(self.board_rect.centerx, 125))
        if state.current_turn is not None:
            banner = status_position.inflate(24, 12)
            banner_color = (225, 239, 251) if state.current_turn == "cow" else (255, 239, 218)
            pygame.draw.rect(self.screen, banner_color, banner, border_radius=12)
            pygame.draw.rect(self.screen, status_color, banner, width=2, border_radius=12)
        self.screen.blit(status_surface, status_position)
        self.screen.blit(self.images["restart"], self.restart_rect)
        self.screen.blit(self.images["close"], self.close_rect)

    def _draw_board(self, state: GameState, cursor: tuple[int, int] | None) -> None:
        pygame.draw.rect(self.screen, NAVY, self.board_rect, border_radius=13)
        hovered = self.cell_at(cursor) if cursor is not None else None
        movable_tigers = {
            tiger_index
            for tiger_index, piece in enumerate(state.board)
            if piece == "tiger" and legal_tiger_moves(state.board, tiger_index)
        }
        movable_cows = {
            cow_index
            for cow_index, piece in enumerate(state.board)
            if piece == "cow" and legal_cow_moves(state.board, cow_index)
        }
        cow_destinations = (
            set(legal_cow_moves(state.board, state.selected_cow))
            if state.selected_cow is not None
            else set()
        )
        tiger_destinations = (
            set(legal_tiger_moves(state.board, state.selected_tiger))
            if state.selected_tiger is not None
            else set()
        )
        for index, token in enumerate(state.board):
            row, col = divmod(index, BOARD_SIZE)
            cell = pygame.Rect(
                BOARD_LEFT + col * CELL_SIZE + 4,
                BOARD_TOP + row * CELL_SIZE + 4,
                CELL_SIZE - 8,
                CELL_SIZE - 8,
            )
            shade = CELL_LIGHT if (row + col) % 2 == 0 else CELL_DARK
            pygame.draw.rect(self.screen, shade, cell, border_radius=8)
            if token is not None:
                icon = self.images[token]
                self.screen.blit(icon, icon.get_rect(center=cell.center))
                if (
                    token == "tiger"
                    and state.current_turn == "tiger"
                    and index in movable_tigers
                ):
                    pygame.draw.rect(
                        self.screen,
                        TIGER_COLOR if index == state.selected_tiger else MUTED,
                        cell,
                        width=4 if index == state.selected_tiger else 2,
                        border_radius=8,
                    )
                elif (
                    token == "cow"
                    and state.current_turn == "cow"
                    and state.cows_placed >= TOTAL_COWS
                    and index in movable_cows
                ):
                    pygame.draw.rect(
                        self.screen,
                        COW_COLOR if index == state.selected_cow else MUTED,
                        cell,
                        width=4 if index == state.selected_cow else 2,
                        border_radius=8,
                    )
            elif (
                state.current_turn == "cow"
                and (
                    index == hovered
                    or index in cow_destinations
                    or (
                        state.cows_placed >= TOTAL_COWS
                        and state.selected_cow is None
                        and index == hovered
                    )
                )
            ) or (
                state.current_turn == "tiger"
                and (index in tiger_destinations or (
                    state.selected_tiger is None and index == hovered
                ))
            ):
                self.screen.blit(self.images["frame"], cell.topleft)

    def _draw_player_panels(
        self,
        state: GameState,
        camera_frames: Mapping[str, MatLike | None],
        camera_messages: Mapping[str, str | None],
        camera_indices: Mapping[str, int | None],
    ) -> None:
        cow_action_instructions = (
            ("Pinch a Cow, point at an", "adjacent empty square to move it.")
            if state.cows_placed >= TOTAL_COWS
            else ("Pinch, point at empty square,", "then release to place Cow.")
        )
        panels = (
            (
                "tiger",
                f"TIGER: {self.player_names['tiger']}",
                (
                    "Use RIGHT hand only.",
                    "Pinch, hold, move, then release.",
                    "Jump a Cow to eat it.",
                    f"Win by eating all {TIGER_WIN_CAPTURES} Cows.",
                ),
            ),
            (
                "cow",
                f"COW: {self.player_names['cow']}",
                (
                    "Use LEFT hand only.",
                    *cow_action_instructions,
                    "Mouse: click an empty square.",
                    f"Cows placed: {state.cows_placed}/{TOTAL_COWS}.",
                    f"Cows eaten: {state.cows_captured}.",
                    "Cow wins by trapping Tigers.",
                ),
            ),
        )
        for player, label, instructions in panels:
            preview = self.camera_rects[player]
            player_color = TIGER_COLOR if player == "tiger" else COW_COLOR
            label = self._fit_text(label, self.small_font, preview.width)
            self._text(label, preview.left, 196, self.small_font, player_color)
            device_index = camera_indices[player]
            camera_name = (
                f"Camera {device_index}"
                if device_index is not None
                else "Camera not connected"
            )
            if player == "cow":
                tiger_index = camera_indices["tiger"]
                if device_index is not None and device_index == tiger_index:
                    camera_name += " | shared camera"
            self._text(camera_name, preview.left, 224, self.small_font, MUTED)
            pygame.draw.rect(self.screen, NAVY, preview, border_radius=8)
            camera_frame = camera_frames[player]
            if camera_frame is not None:
                rgb = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
                surface = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
                surface = pygame.transform.smoothscale(surface, preview.size)
                self.screen.blit(surface, preview)
            else:
                self._text("No camera feed", preview.left + 42, 317, self.small_font, MUTED)
            pygame.draw.rect(
                self.screen,
                player_color,
                preview,
                width=3,
                border_radius=8,
            )
            message = camera_messages[player]
            if message:
                short_message = "Camera unavailable; use mouse."
                self._draw_wrapped_text(
                    short_message,
                    preview.left,
                    425,
                    preview.width,
                    self.small_font,
                    (171, 73, 58),
                )
            for line_index, line in enumerate(instructions):
                self._draw_wrapped_text(
                    line,
                    preview.left,
                    478 + line_index * 27,
                    preview.width,
                    self.small_font,
                    MUTED,
                )
        self._text("R: restart     Esc: quit", BOARD_LEFT, 700, self.small_font, MUTED)
        pygame.draw.rect(self.screen, (255, 248, 226), self.home_rect, border_radius=10)
        pygame.draw.rect(self.screen, NAVY, self.home_rect, width=2, border_radius=10)
        home_label = self.small_font.render("Back to Start", True, NAVY)
        self.screen.blit(home_label, home_label.get_rect(center=self.home_rect.center))

    def _fit_text(
        self,
        text: str,
        font: pygame.font.Font,
        max_width: int,
    ) -> str:
        if font.size("...")[0] > max_width:
            while text and font.size(text)[0] > max_width:
                text = text[:-1]
            return text
        while text and font.size(text)[0] > max_width:
            text = text[:-4] + "..."
        return text

    def _text(
        self, text: str, x: int, y: int, font: pygame.font.Font, color: tuple[int, int, int]
    ) -> None:
        self.screen.blit(font.render(text, True, color), (x, y))

    def _draw_wrapped_text(
        self,
        text: str,
        x: int,
        y: int,
        max_width: int,
        font: pygame.font.Font,
        color: tuple[int, int, int],
    ) -> None:
        line = ""
        for word in text.split():
            candidate = f"{line} {word}".strip()
            if line and font.size(candidate)[0] > max_width:
                self._text(line, x, y, font, color)
                y += font.get_linesize()
                line = word
            else:
                line = candidate
        if line:
            self._text(line, x, y, font, color)
