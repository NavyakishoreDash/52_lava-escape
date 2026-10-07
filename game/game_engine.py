import pygame
import math
from game.player import Player
from game.world import generate_platforms, draw_lava

WIDTH, HEIGHT = 500, 640
FPS = 60
BG = (20, 15, 30)
GROUND_Y = HEIGHT - 40

# Surge cycle constants (in frames at 60 FPS)
SURGE_CYCLE_TOTAL = 650     # ~10.8s total cycle
WARNING_START = 490         # Warning starts at ~8.2s (lasts ~1.0s)
SURGE_START = 550           # Surge starts at ~9.2s (lasts ~1.6s)
SURGE_SPEED_MULT = 2.8      # Lava ascent multiplier during burst surge


class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Lava Escape")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 18, bold=True)
        self.hud_font = pygame.font.SysFont("monospace", 13, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 38, bold=True)
        self.reset()

    def reset(self):
        self.platforms = generate_platforms(WIDTH, GROUND_Y)
        # Spawn player safely standing on top of the ground platform
        self.player = Player(WIDTH // 2 - 16, GROUND_Y - 32)
        self.player.on_ground = True
        self.cam_y = 0.0
        self.lava_y = float(GROUND_Y + 50)
        self.base_lava_rise = 0.4
        self.current_lava_rise = 0.4
        self.surge_timer = 0
        self.surge_state = "NORMAL"  # "NORMAL", "WARNING", "SURGE"
        self.score = 0
        self.game_over = False
        self.won = False
        self.top_y = self.platforms[-1].y
        self.frame = 0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset()
        return True

    def update(self):
        if self.game_over or self.won:
            return

        keys = pygame.key.get_pressed()

        # Update all platforms (crumbling countdown, debris, spring animations)
        for p in self.platforms:
            if hasattr(p, 'update'):
                p.update()

        # Update player with one-way landing collision logic
        self.player.update(keys, self.platforms, WIDTH)

        # Smooth upward camera tracking
        target = self.player.rect.centery - HEIGHT // 2
        if target < self.cam_y:
            self.cam_y = target

        # Lava Surge phase management (Task 4)
        self.surge_timer = (self.surge_timer + 1) % SURGE_CYCLE_TOTAL

        if self.surge_timer >= SURGE_START:
            self.surge_state = "SURGE"
            speed_multiplier = SURGE_SPEED_MULT
        elif self.surge_timer >= WARNING_START:
            self.surge_state = "WARNING"
            speed_multiplier = 1.0
        else:
            self.surge_state = "NORMAL"
            speed_multiplier = 1.0

        # Base lava rise increases slowly over time
        self.base_lava_rise = min(1.2, self.base_lava_rise + 0.00025)
        self.current_lava_rise = self.base_lava_rise * speed_multiplier
        self.lava_y -= self.current_lava_rise

        # Progress score & win/loss conditions
        self.score = max(0, int((GROUND_Y - self.player.rect.bottom) // 10))
        self.frame += 1

        if self.player.rect.bottom >= self.lava_y:
            self.game_over = True
        if self.player.rect.top <= self.top_y - 20:
            self.won = True

    def _draw_danger_hud(self):
        """Draws the Rising Danger HUD meter and surge warning status (Task 4)."""
        hud_w = 175
        hud_h = 42
        hud_x = WIDTH - hud_w - 10
        hud_y = 10

        # Background container
        hud_surface = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        hud_surface.fill((25, 20, 30, 210))
        self.screen.blit(hud_surface, (hud_x, hud_y))
        pygame.draw.rect(self.screen, (70, 60, 80), (hud_x, hud_y, hud_w, hud_h), width=1, border_radius=4)

        # Calculate danger ratio (0.0 to 1.0)
        max_possible_speed = 1.2 * SURGE_SPEED_MULT
        danger_ratio = min(1.0, max(0.0, self.current_lava_rise / max_possible_speed))

        # Status text & danger color based on surge state
        if self.surge_state == "SURGE":
            # Flashing red/white alert
            flash = (self.frame // 8) % 2 == 0
            label_color = (255, 60, 50) if flash else (255, 220, 100)
            status_text = "SURGE ACTIVE!"
            bar_color = (255, 40, 20)
        elif self.surge_state == "WARNING":
            # Flashing yellow warning
            flash = (self.frame // 12) % 2 == 0
            label_color = (255, 180, 20) if flash else (255, 120, 10)
            status_text = "SURGE WARNING!"
            bar_color = (255, 160, 30)
        else:
            label_color = (200, 190, 210)
            status_text = f"{self.current_lava_rise:.1f}x SPEED"
            if danger_ratio < 0.35:
                bar_color = (80, 210, 110)
            elif danger_ratio < 0.65:
                bar_color = (230, 180, 40)
            else:
                bar_color = (230, 90, 30)

        # Danger HUD label
        lbl = self.hud_font.render(f"LAVA DANGER: {status_text}", True, label_color)
        self.screen.blit(lbl, (hud_x + 8, hud_y + 5))

        # Danger gauge bar
        bar_bg_rect = pygame.Rect(hud_x + 8, hud_y + 24, hud_w - 16, 12)
        pygame.draw.rect(self.screen, (45, 35, 50), bar_bg_rect, border_radius=3)
        fill_w = int((hud_w - 16) * danger_ratio)
        if fill_w > 0:
            bar_fill_rect = pygame.Rect(hud_x + 8, hud_y + 24, fill_w, 12)
            pygame.draw.rect(self.screen, bar_color, bar_fill_rect, border_radius=3)
        pygame.draw.rect(self.screen, (90, 80, 100), bar_bg_rect, width=1, border_radius=3)

        # Full-screen edge danger vignette during surge or warning
        if self.surge_state == "SURGE":
            alpha = int(45 + 30 * math.sin(self.frame * 0.25))
            vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            vignette.fill((255, 20, 0, max(0, alpha)))
            # Cut out center so only borders glow
            center_rect = pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 40)
            pygame.draw.rect(vignette, (0, 0, 0, 0), center_rect)
            self.screen.blit(vignette, (0, 0))
        elif self.surge_state == "WARNING":
            alpha = int(25 + 20 * math.sin(self.frame * 0.15))
            vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            vignette.fill((255, 140, 0, max(0, alpha)))
            center_rect = pygame.Rect(15, 15, WIDTH - 30, HEIGHT - 30)
            pygame.draw.rect(vignette, (0, 0, 0, 0), center_rect)
            self.screen.blit(vignette, (0, 0))

    def draw(self):
        self.screen.fill(BG)

        # Draw platforms (with crumbly shaking and spring bounce animations)
        for p in self.platforms:
            p.draw(self.screen, self.cam_y)

        # Draw player
        self.player.draw(self.screen, self.cam_y)

        # Draw lava with surge wave dynamics (Task 4)
        is_surge = (self.surge_state == "SURGE")
        draw_lava(self.screen, self.lava_y, self.cam_y, WIDTH, HEIGHT, self.frame, is_surge=is_surge)

        # Top-left HUD: Height & Controls
        sc = self.font.render(f"Height: {self.score}m", True, (240, 220, 200))
        self.screen.blit(sc, (12, 10))
        sub = self.hud_font.render("[R] Restart", True, (160, 150, 170))
        self.screen.blit(sub, (12, 32))

        # Top-right HUD: Rising Danger Meter (Task 4)
        self._draw_danger_hud()

        # Game Over / Victory state overlays
        if self.game_over:
            self._msg("LAVA GOT YOU!", (240, 70, 40))
        if self.won:
            self._msg("ESCAPED!", (80, 230, 120))

        pygame.display.flip()

    def _msg(self, text, color):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))

        card = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 75, 360, 150)
        pygame.draw.rect(self.screen, (35, 28, 45), card, border_radius=10)
        pygame.draw.rect(self.screen, (80, 70, 95), card, width=2, border_radius=10)

        m = self.big_font.render(text, True, color)
        s = self.font.render("Press R to Play Again", True, (210, 200, 220))
        final_score = self.hud_font.render(f"Final Height: {self.score}m", True, (180, 170, 190))

        self.screen.blit(m, (WIDTH // 2 - m.get_width() // 2, HEIGHT // 2 - 50))
        self.screen.blit(final_score, (WIDTH // 2 - final_score.get_width() // 2, HEIGHT // 2))
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 + 30))

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
