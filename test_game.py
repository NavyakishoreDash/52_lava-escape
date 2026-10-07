import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame
import unittest
from game.player import Player
from game.world import (
    Platform, NormalPlatform, CrumblingPlatform, SpringPlatform,
    generate_platforms, draw_lava
)
from game.game_engine import (
    GameEngine, WIDTH, HEIGHT, GROUND_Y,
    WARNING_START, SURGE_START, SURGE_CYCLE_TOTAL, SURGE_SPEED_MULT
)


class TestLavaEscape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((WIDTH, HEIGHT))

    # =========================================================================
    # Task 1: Platform Underside Collision Snapping Bug Fix
    # =========================================================================
    def test_task1_jumping_up_through_platform_does_not_snap(self):
        """Player jumping up from beneath platform must pass cleanly through without snapping to top."""
        plat = NormalPlatform(100, 300, 150, 16)
        # Player right below platform jumping up
        player = Player(150, 320)
        player.vel_y = -8.0  # Ascending

        keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_a: False,
                pygame.K_d: False, pygame.K_SPACE: False, pygame.K_w: False, pygame.K_UP: False}

        # Step 1: Upward motion
        player.update(keys, [plat], WIDTH)
        # Player bottom moved up to 320 - 8 + 32 = 344
        self.assertFalse(player.on_ground, "Player should not be on ground when ascending")
        self.assertNotEqual(player.rect.bottom, plat.top, "Player should not snap to top when ascending")

    def test_task1_apex_inside_platform_does_not_snap(self):
        """When player is descending but feet were inside the platform (did not clear upper edge), do not snap."""
        plat = NormalPlatform(100, 300, 150, 16)
        # Position player so feet are at y=308 (inside the 300-316 platform range)
        player = Player(150, 308 - 32)
        player.vel_y = 0.5  # Descending, but feet were already below plat.top (300)

        keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_a: False,
                pygame.K_d: False, pygame.K_SPACE: False, pygame.K_w: False, pygame.K_UP: False}

        player.update(keys, [plat], WIDTH)
        self.assertFalse(player.on_ground, "Player must not snap to top if feet did not clear the upper edge")
        self.assertNotEqual(player.rect.bottom, plat.top)

    def test_task1_descending_from_above_lands_cleanly(self):
        """Player falling onto platform from above must land securely on the upper edge."""
        plat = NormalPlatform(100, 300, 150, 16)
        # Player feet at 296 (above plat.top at 300)
        player = Player(150, 296 - 32)
        player.vel_y = 6.0  # Descending: next position would be 296 + 6 = 302

        keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_a: False,
                pygame.K_d: False, pygame.K_SPACE: False, pygame.K_w: False, pygame.K_UP: False}

        player.update(keys, [plat], WIDTH)
        self.assertTrue(player.on_ground, "Player should land when descending onto platform from above")
        self.assertEqual(player.rect.bottom, plat.top, "Player feet should be exactly aligned to platform top")
        self.assertEqual(player.vel_y, 0.0, "Vertical velocity should reset to 0 upon landing")

    # =========================================================================
    # Task 2: Crumbling Platform Hazards
    # =========================================================================
    def test_task2_crumbling_platform_triggers_on_land(self):
        """Crumbling platform begins crumbling state upon player landing."""
        crumb = CrumblingPlatform(100, 300, 150, 16)
        self.assertEqual(crumb.state, "idle")
        self.assertFalse(crumb.is_broken)

        player = Player(150, 298 - 32)
        player.vel_y = 4.0

        keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_a: False,
                pygame.K_d: False, pygame.K_SPACE: False, pygame.K_w: False, pygame.K_UP: False}

        player.update(keys, [crumb], WIDTH)
        self.assertEqual(crumb.state, "crumbling", "State should transition to crumbling when landed on")
        self.assertEqual(player.rect.bottom, crumb.top)
        self.assertTrue(player.on_ground)

    def test_task2_crumbling_platform_disintegrates_and_drops_player(self):
        """After countdown, crumbling platform breaks and player falls through."""
        crumb = CrumblingPlatform(100, 300, 150, 16)
        player = Player(150, 300 - 32)
        crumb.on_land(player)
        self.assertEqual(crumb.state, "crumbling")

        # Advance frames past crumbling timer
        for _ in range(crumb.max_timer + 2):
            crumb.update()

        self.assertEqual(crumb.state, "broken")
        self.assertTrue(crumb.is_broken)

        # Player update with broken platform: player should fall through
        keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_a: False,
                pygame.K_d: False, pygame.K_SPACE: False, pygame.K_w: False, pygame.K_UP: False}
        player.update(keys, [crumb], WIDTH)
        self.assertFalse(player.on_ground, "Player must fall through broken platform")
        self.assertGreater(player.vel_y, 0, "Gravity should accelerate player downwards")

    # =========================================================================
    # Task 3: High-Velocity Spring Platforms
    # =========================================================================
    def test_task3_spring_platform_launches_with_bonus_velocity(self):
        """Spring platform must launch the player upward with bonus vertical velocity (-20.0)."""
        spring = SpringPlatform(100, 300, 150, 16)
        player = Player(150, 298 - 32)
        player.vel_y = 4.0

        keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_a: False,
                pygame.K_d: False, pygame.K_SPACE: False, pygame.K_w: False, pygame.K_UP: False}

        player.update(keys, [spring], WIDTH)
        self.assertEqual(player.vel_y, -20.0, "Spring must launch with -20.0 velocity")
        self.assertFalse(player.on_ground, "Player should be airborne after spring launch")
        self.assertGreater(spring.spring_anim, 0, "Spring animation should be triggered")

    # =========================================================================
    # Task 4: Rising Danger HUD & Lava Burst Surges
    # =========================================================================
    def test_task4_surge_cycle_transitions(self):
        """Game engine must cycle through NORMAL -> WARNING -> SURGE phases."""
        engine = GameEngine()

        # Phase 1: NORMAL
        engine.surge_timer = 100
        engine.update()
        self.assertEqual(engine.surge_state, "NORMAL")
        self.assertAlmostEqual(engine.current_lava_rise, engine.base_lava_rise, places=3)

        # Phase 2: WARNING
        engine.surge_timer = WARNING_START
        engine.update()
        self.assertEqual(engine.surge_state, "WARNING")

        # Phase 3: SURGE
        engine.surge_timer = SURGE_START
        engine.update()
        self.assertEqual(engine.surge_state, "SURGE")
        self.assertAlmostEqual(engine.current_lava_rise, engine.base_lava_rise * SURGE_SPEED_MULT, places=3)

    def test_task4_danger_hud_rendering_and_reset(self):
        """GameEngine draw loop and reset function work flawlessly without exceptions."""
        engine = GameEngine()
        # Draw during normal
        engine.draw()

        # Draw during warning
        engine.surge_timer = WARNING_START + 5
        engine.update()
        engine.draw()

        # Draw during surge
        engine.surge_timer = SURGE_START + 5
        engine.update()
        engine.draw()

        # Reset
        engine.reset()
        self.assertEqual(engine.surge_timer, 0)
        self.assertEqual(engine.surge_state, "NORMAL")
        self.assertFalse(engine.game_over)
        self.assertFalse(engine.won)

    # =========================================================================
    # Additional Verification: Initial Visibility & Reachability
    # =========================================================================
    def test_player_initially_visible_on_screen(self):
        """Player avatar must be clearly visible within the screen viewport at game start."""
        engine = GameEngine()
        dr = engine.player.rect.move(0, -int(engine.cam_y))
        self.assertGreaterEqual(dr.y, 0, "Player must not be above the screen")
        self.assertLessEqual(dr.bottom, HEIGHT, "Player must not be below the screen")
        self.assertTrue(engine.player.on_ground, "Player must start standing on solid ground")

    def test_all_generated_platforms_reachable(self):
        """All procedural platform pairs must be physically reachable within jump trajectory limits."""
        import math
        plats = generate_platforms(WIDTH, GROUND_Y, 35)
        for i in range(len(plats) - 1):
            p1, p2 = plats[i], plats[i + 1]
            dy = p1.top - p2.top
            is_spring = isinstance(p1, SpringPlatform)
            v0 = 20.0 if is_spring else 13.0
            g = 0.55
            apex = (v0 ** 2) / (2 * g)
            self.assertLess(dy, apex, f"Platform {i}->{i+1} height difference {dy} exceeds max jump {apex}")
            t_up = v0 / g
            t_down = math.sqrt(2 * (apex - dy) / g)
            max_dist = (t_up + t_down) * 4.0
            gap = max(0, p2.left - p1.right, p1.left - p2.right)
            self.assertLessEqual(gap, max_dist, f"Platform {i}->{i+1} horizontal gap {gap} exceeds reach {max_dist}")


if __name__ == '__main__':
    unittest.main()

