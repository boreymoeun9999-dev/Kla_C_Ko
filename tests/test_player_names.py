import unittest

import pygame

from src.renderer import Renderer


class PlayerNameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = Renderer.__new__(Renderer)
        self.renderer.name_field_rects = {
            "tiger": pygame.Rect(0, 0, 100, 40),
            "cow": pygame.Rect(120, 0, 100, 40),
        }
        self.renderer.player_name_inputs = {"tiger": "", "cow": ""}
        self.renderer.active_name_field = None

    def test_default_names_are_used_for_empty_fields(self) -> None:
        self.assertEqual(
            self.renderer.player_names,
            {"tiger": "Tiger Player", "cow": "Cow Player"},
        )

    def test_names_can_be_entered_edited_and_trimmed(self) -> None:
        self.assertTrue(self.renderer.focus_name_field((50, 20)))
        self.renderer.handle_name_input(
            pygame.event.Event(
                pygame.TEXTINPUT,
                text=" Ari ",
            )
        )
        self.renderer.handle_name_input(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_BACKSPACE,
                unicode="",
            )
        )

        self.assertEqual(self.renderer.player_names["tiger"], "Ari")

    def test_tab_moves_focus_to_the_other_player(self) -> None:
        self.renderer.focus_name_field((50, 20))
        self.renderer.handle_name_input(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, unicode="\t")
        )
        self.renderer.handle_name_input(
            pygame.event.Event(pygame.TEXTINPUT, text="M")
        )

        self.assertEqual(self.renderer.active_name_field, "cow")
        self.assertEqual(self.renderer.player_names["cow"], "M")

    def test_clicking_either_name_box_selects_that_player_for_typing(self) -> None:
        for player, position in (("tiger", (50, 20)), ("cow", (170, 20))):
            with self.subTest(player=player):
                self.assertTrue(self.renderer.focus_name_field(position))
                self.renderer.handle_name_input(
                    pygame.event.Event(pygame.TEXTINPUT, text="Name")
                )
                self.assertEqual(self.renderer.player_names[player], "Name")
                self.renderer.player_name_inputs[player] = ""

    def test_keydown_text_fallback_accepts_typed_name(self) -> None:
        self.renderer.focus_name_field((50, 20))
        self.renderer.handle_name_input(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="A")
        )

        self.assertEqual(self.renderer.player_names["tiger"], "A")

    def test_enter_finishes_editing_without_losing_the_name(self) -> None:
        self.renderer.focus_name_field((50, 20))
        self.renderer.handle_name_input(
            pygame.event.Event(pygame.TEXTINPUT, text="Ari")
        )
        self.renderer.handle_name_input(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
        )

        self.assertIsNone(self.renderer.active_name_field)
        self.assertEqual(self.renderer.player_names["tiger"], "Ari")


if __name__ == "__main__":
    unittest.main()
