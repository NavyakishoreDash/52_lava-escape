import pygame
import random
import math

PLATFORM_COLOR = (100, 80, 50)
LAVA_COLOR = (220, 60, 20)
LAVA_SURGE_COLOR = (255, 45, 10)
LAVA_CREST_COLOR = (255, 150, 30)


class Platform:
    """Base class for all platforms."""
    def __init__(self, x, y, width, height=16, kind="normal"):
        self.rect = pygame.Rect(x, y, width, height)
        self.kind = kind
        self.is_broken = False

    @property
    def top(self):
        return self.rect.top

    @property
    def bottom(self):
        return self.rect.bottom

    @property
    def left(self):
        return self.rect.left

    @property
    def right(self):
        return self.rect.right

    @property
    def x(self):
        return self.rect.x

    @property
    def y(self):
        return self.rect.y

    @property
    def width(self):
        return self.rect.width

    @property
    def height(self):
        return self.rect.height

    def colliderect(self, other):
        return self.rect.colliderect(other)

    def move(self, dx, dy):
        return self.rect.move(dx, dy)

    def on_land(self, player):
        """Called when a player lands on this platform from above."""
        player.rect.bottom = self.rect.top
        player.y = float(player.rect.y)
        player.vel_y = 0
        player.on_ground = True

    def update(self):
        pass

    def draw(self, screen, cam_y):
        dr = self.rect.move(0, -int(cam_y))
        pygame.draw.rect(screen, PLATFORM_COLOR, dr, border_radius=4)


class NormalPlatform(Platform):
    """Solid, durable stone platform."""
    def __init__(self, x, y, width, height=16):
        super().__init__(x, y, width, height, kind="normal")

    def draw(self, screen, cam_y):
        dr = self.rect.move(0, -int(cam_y))
        # Base platform body
        pygame.draw.rect(screen, (95, 75, 55), dr, border_radius=4)
        # Top highlight edge
        top_strip = pygame.Rect(dr.x, dr.y, dr.width, max(3, dr.height // 4))
        pygame.draw.rect(screen, (140, 115, 80), top_strip, border_top_left_radius=4, border_top_right_radius=4)
        # Bottom shadow line
        pygame.draw.line(screen, (60, 45, 30), (dr.left + 2, dr.bottom - 1), (dr.right - 2, dr.bottom - 1), 1)


class CrumblingPlatform(Platform):
    """
    Fragile platform that starts shaking when stepped on and disintegrates
    after a short timer, forcing the player to keep moving upward.
    """
    def __init__(self, x, y, width, height=16):
        super().__init__(x, y, width, height, kind="crumbling")
        self.state = "idle"  # "idle", "crumbling", "broken"
        self.max_timer = 45   # ~0.75 seconds at 60 FPS
        self.timer = self.max_timer
        self.shake_offset = [0, 0]
        self.particles = []   # Debris particles [x, y, vx, vy, color, life, max_life]

    def on_land(self, player):
        if self.is_broken:
            return
        # Standard landing physics
        player.rect.bottom = self.rect.top
        player.y = float(player.rect.y)
        player.vel_y = 0
        player.on_ground = True
        # Trigger crumble sequence on first step
        if self.state == "idle":
            self.state = "crumbling"

    def update(self):
        # Update active falling debris particles
        for p in self.particles:
            p[0] += p[2]  # x += vx
            p[1] += p[3]  # y += vy
            p[3] += 0.35  # gravity on debris
            p[5] -= 1     # decrement life
        self.particles = [p for p in self.particles if p[5] > 0]

        if self.state == "crumbling":
            self.timer -= 1
            # Violent shaking as it nears destruction
            intensity = 2 if self.timer > 15 else 4
            self.shake_offset = [
                random.randint(-intensity, intensity),
                random.randint(-1, 1)
            ]
            # Occasional dust / pebble emissions while crumbling
            if random.random() < 0.4:
                px = self.rect.left + random.randint(4, max(5, self.rect.width - 4))
                py = self.rect.bottom
                self.particles.append([
                    px, py,
                    random.uniform(-1.0, 1.0),
                    random.uniform(0.5, 2.0),
                    (175, 115, 65),
                    25, 25
                ])

            if self.timer <= 0:
                self.state = "broken"
                self.is_broken = True
                self.shake_offset = [0, 0]
                # Burst of falling rubble when disintegrated
                for _ in range(16):
                    px = self.rect.left + random.randint(2, max(3, self.rect.width - 2))
                    py = self.rect.top + random.randint(2, max(3, self.rect.height - 2))
                    self.particles.append([
                        px, py,
                        random.uniform(-2.5, 2.5),
                        random.uniform(-2.0, 3.5),
                        random.choice([(160, 100, 50), (130, 80, 40), (200, 130, 70)]),
                        random.randint(30, 50),
                        50
                    ])

    def draw(self, screen, cam_y):
        # Draw rubble debris particles
        for p in self.particles:
            px = int(p[0])
            py = int(p[1] - cam_y)
            alpha_ratio = p[5] / p[6]
            size = max(2, int(4 * alpha_ratio))
            pygame.draw.rect(screen, p[4], (px, py, size, size))

        if self.is_broken:
            return

        dr = self.rect.move(self.shake_offset[0], self.shake_offset[1] - int(cam_y))

        # Color changes based on urgency
        if self.state == "crumbling":
            # Blinks orange/rust when close to breaking
            ratio = self.timer / self.max_timer
            body_color = (
                int(165 + (1 - ratio) * 60),
                int(110 * ratio + 30),
                int(60 * ratio + 20)
            )
        else:
            body_color = (165, 110, 65)

        # Platform base
        pygame.draw.rect(screen, body_color, dr, border_radius=4)
        # Top cracked rim
        rim_color = (200, 140, 90) if self.state == "idle" else (240, 160, 70)
        pygame.draw.rect(screen, rim_color, (dr.x, dr.y, dr.width, 3), border_top_left_radius=4, border_top_right_radius=4)

        # Draw visible stress cracks
        crack_color = (80, 45, 25) if self.state == "idle" else (255, 80, 20)
        cx = dr.centerx
        pygame.draw.line(screen, crack_color, (cx - 15, dr.top + 2), (cx - 5, dr.bottom - 4), 2)
        pygame.draw.line(screen, crack_color, (cx - 5, dr.bottom - 4), (cx + 10, dr.bottom - 2), 2)
        if dr.width > 100:
            pygame.draw.line(screen, crack_color, (dr.left + 25, dr.top + 2), (dr.left + 35, dr.bottom - 3), 1)
            pygame.draw.line(screen, crack_color, (dr.right - 25, dr.top + 3), (dr.right - 35, dr.bottom - 2), 1)


class SpringPlatform(Platform):
    """
    High-velocity spring platform that launches the player upward with
    bonus vertical velocity (-20.0 instead of standard -13.0) when touched.
    """
    def __init__(self, x, y, width, height=16):
        super().__init__(x, y, width, height, kind="spring")
        self.bounce_vel = -20.0
        self.spring_anim = 0   # Countdown timer for bounce visual effect
        self.particles = []    # Burst particles [x, y, vx, vy, color, life, max_life]

    def on_land(self, player):
        # Position player right on the spring plate
        player.rect.bottom = self.rect.top
        player.y = float(player.rect.y)
        # Launch player upward with high-powered velocity
        player.vel_y = self.bounce_vel
        player.on_ground = False
        # Trigger visual spring reaction
        self.spring_anim = 16
        # Spawn glowing emerald spark particles
        for _ in range(12):
            self.particles.append([
                self.rect.centerx + random.randint(-self.rect.width // 3, self.rect.width // 3),
                self.rect.top - 2,
                random.uniform(-3.0, 3.0),
                random.uniform(-5.0, -1.0),
                random.choice([(60, 255, 120), (120, 255, 180), (220, 255, 100)]),
                random.randint(18, 30),
                30
            ])

    def update(self):
        if self.spring_anim > 0:
            self.spring_anim -= 1

        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.2  # Gravity
            p[5] -= 1
        self.particles = [p for p in self.particles if p[5] > 0]

    def draw(self, screen, cam_y):
        dr = self.rect.move(0, -int(cam_y))

        # Draw spark particles
        for p in self.particles:
            px = int(p[0])
            py = int(p[1] - cam_y)
            pygame.draw.circle(screen, p[4], (px, py), 3)

        # Base platform body (metallic high-tech slate)
        pygame.draw.rect(screen, (50, 60, 75), dr, border_radius=4)
        pygame.draw.rect(screen, (80, 95, 115), dr, width=1, border_radius=4)

        # Coiled spring / bouncy pad on top
        spring_color = (50, 230, 110)
        coil_h = 4 if self.spring_anim > 8 else (8 if self.spring_anim > 0 else 6)
        
        # Spring mount pad
        pad_rect = pygame.Rect(dr.centerx - 22, dr.top - coil_h, 44, coil_h + 2)
        pygame.draw.rect(screen, spring_color, pad_rect, border_radius=3)
        # Spring coil zigzag marks
        pygame.draw.line(screen, (30, 160, 70), (pad_rect.left + 6, pad_rect.centery), (pad_rect.right - 6, pad_rect.centery), 2)
        # Glow edge
        pygame.draw.rect(screen, (150, 255, 180), pad_rect, width=1, border_radius=3)


def generate_platforms(width, base_y, count=35):
    """
    Generates an ascending procedural course of platforms where EVERY platform
    is guaranteed to be comfortably reachable within the player's jump physics.
    - Ground floor: Spans the full width
    - First platform: Centered and close to ground for a smooth start
    - Subsequent platforms: Constrained horizontal and vertical offsets guaranteeing reachability
    - Balanced distribution of Normal, Crumbling (never 2 consecutive), and Spring platforms
    - Top platform: Always sturdy goal platform
    """
    plats = [NormalPlatform(0, base_y, width, 30)]  # Ground floor

    # First platform above ground is always centered, wide, and close
    prev_y = base_y - 75
    prev_w = random.randint(130, 170)
    prev_x = (width - prev_w) // 2
    plats.append(NormalPlatform(prev_x, prev_y, prev_w, 16))

    prev_cx = prev_x + prev_w // 2
    consecutive_crumbling = 0
    prev_was_spring = False

    for i in range(2, count):
        w = random.randint(105, 160)

        # Vertical spacing: standard jump reaches ~153px.
        # We use 68-86px for normal jumps so the player has plenty of headroom.
        # If previous was a spring (360px launch), we can give a slightly higher tier.
        if prev_was_spring:
            dy = random.randint(75, 95)
        else:
            dy = random.randint(68, 86)
        y = prev_y - dy

        # Horizontal placement: ensure the gap between platforms NEVER exceeds 60px.
        # Shift target center by 50-110px left or right.
        shift = random.randint(50, 110) * random.choice([-1, 1])

        # If previous platform was close to screen edge, direct it inwards
        if prev_cx < 130:
            shift = random.randint(60, 110)
        elif prev_cx > width - 130:
            shift = -random.randint(60, 110)

        cx = prev_cx + shift
        # Clamp within screen bounds with padding
        margin = w // 2 + 15
        cx = max(margin, min(width - margin, cx))
        x = int(cx - w / 2)

        # Platform type selection
        # First 3 platforms and the final platform are always sturdy normal platforms
        if i < 3 or i >= count - 2:
            plat = NormalPlatform(x, y, w, 16)
            consecutive_crumbling = 0
            prev_was_spring = False
        else:
            roll = random.random()
            # Crumbling platform: 28% chance, but NEVER allow 2 consecutive crumbling platforms
            if roll < 0.28 and consecutive_crumbling < 1 and not prev_was_spring:
                plat = CrumblingPlatform(x, y, w, 16)
                consecutive_crumbling += 1
                prev_was_spring = False
            # Spring platform: 22% chance
            elif roll < 0.50:
                plat = SpringPlatform(x, y, w, 16)
                consecutive_crumbling = 0
                prev_was_spring = True
            else:
                plat = NormalPlatform(x, y, w, 16)
                consecutive_crumbling = 0
                prev_was_spring = False

        plats.append(plat)
        prev_x = x
        prev_y = y
        prev_w = w
        prev_cx = cx

    return plats


def draw_lava(screen, lava_y, cam_y, width, height, frame, is_surge=False):
    """
    Renders dynamic multi-layered animated lava waves, surface crests,
    and glowing heat haze with violent surges during surge phases.
    """
    ly = int(lava_y - cam_y)
    if ly < height:
        wave_amp = 14 if is_surge else 8
        wave_speed = 0.18 if is_surge else 0.10
        base_color = LAVA_SURGE_COLOR if is_surge else LAVA_COLOR

        # 1. Main lava body polygon
        pts = [(0, ly)]
        for x in range(0, width + 20, 16):
            wave1 = math.sin(x * 0.07 + frame * wave_speed) * wave_amp
            wave2 = math.cos(x * 0.04 - frame * (wave_speed * 0.7)) * (wave_amp * 0.5)
            pts.append((x, ly + int(wave1 + wave2)))
        pts.append((width, height))
        pts.append((0, height))
        pygame.draw.polygon(screen, base_color, pts)

        # 2. Glowing crest wave line
        crest_pts = []
        for x in range(0, width + 20, 16):
            wave1 = math.sin(x * 0.07 + frame * wave_speed) * wave_amp
            wave2 = math.cos(x * 0.04 - frame * (wave_speed * 0.7)) * (wave_amp * 0.5)
            crest_pts.append((x, ly + int(wave1 + wave2) - 1))
        if len(crest_pts) > 1:
            pygame.draw.lines(screen, LAVA_CREST_COLOR, False, crest_pts, 3 if is_surge else 2)

        # 3. Ambient heat glow gradient
        glow_h = 45 if is_surge else 25
        s = pygame.Surface((width, glow_h), pygame.SRCALPHA)
        max_alpha = 110 if is_surge else 65
        for i in range(glow_h):
            alpha = max(0, int(max_alpha * (1.0 - i / glow_h)))
            glow_color = (255, 90, 0, alpha) if not is_surge else (255, 40, 0, alpha)
            pygame.draw.line(s, glow_color, (0, glow_h - 1 - i), (width, glow_h - 1 - i), 1)
        screen.blit(s, (0, ly - glow_h))

        # 4. Magma splash bubbles during surge
        if is_surge:
            for i in range(6):
                spark_x = (frame * 31 + i * 83) % width
                spark_y = ly - 4 - ((frame * 3 + i * 19) % 28)
                pygame.draw.circle(screen, (255, 230, 100), (spark_x, spark_y), 3)
