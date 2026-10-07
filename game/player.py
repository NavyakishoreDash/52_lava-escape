import pygame

SPEED = 4


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.y = float(y)
        self.vel_y = 0.0
        self.on_ground = False
        self.color = (60, 160, 220)
        self.facing_right = True

    def update(self, keys, platforms, width):
        # 1. Horizontal movement
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = SPEED
            self.facing_right = True

        # 2. Jump input
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y = -13.0
            self.on_ground = False

        # 3. Apply gravity
        self.vel_y = min(self.vel_y + 0.55, 12.0)

        # 4. Integrate horizontal position with screen boundary clamping
        self.rect.x = max(0, min(width - self.rect.width, self.rect.x + dx))

        # 5. Record previous vertical bottom position BEFORE moving
        # Crucial for true one-way platform resolution (Task 1)
        prev_bottom = self.rect.bottom

        # 6. Integrate vertical position
        self.y += self.vel_y
        self.rect.y = int(self.y)
        self.on_ground = False

        # 7. One-way platform landing collision resolution (Task 1)
        # Landing resolution ONLY triggers when descending (vel_y >= 0)
        # and strictly clears the platform's upper edge (prev_bottom was at or above p.top)
        if self.vel_y >= 0:
            for p in platforms:
                # Disintegrated / broken crumbling platforms cannot be landed on (Task 2)
                if getattr(p, 'is_broken', False):
                    continue

                p_top = getattr(p, 'top', p.rect.top if hasattr(p, 'rect') else p.top)
                p_bottom = getattr(p, 'bottom', p.rect.bottom if hasattr(p, 'rect') else p.bottom)
                p_left = getattr(p, 'left', p.rect.left if hasattr(p, 'rect') else p.left)
                p_right = getattr(p, 'right', p.rect.right if hasattr(p, 'rect') else p.right)

                # Strict conditions for landing:
                # a) Player's feet were strictly at or above the platform's top edge before movement
                # b) Player's feet have reached or crossed the platform's top edge this frame
                # c) Player's feet have not completely plunged below the platform
                # d) Player overlaps horizontally with the platform ledge
                if (prev_bottom <= p_top + 2 and
                        self.rect.bottom >= p_top and
                        self.rect.bottom <= p_bottom + int(self.vel_y) + 4 and
                        self.rect.right > p_left and
                        self.rect.left < p_right):

                    if hasattr(p, 'on_land'):
                        p.on_land(self)
                    else:
                        self.rect.bottom = p_top
                        self.y = float(self.rect.y)
                        self.vel_y = 0.0
                        self.on_ground = True
                    break

    def draw(self, screen, cam_y):
        dr = self.rect.move(0, -int(cam_y))

        # Player body with rounded corners
        pygame.draw.rect(screen, self.color, dr, border_radius=6)
        # Inner highlight
        inner = pygame.Rect(dr.x + 3, dr.y + 3, dr.width - 6, dr.height - 6)
        pygame.draw.rect(screen, (90, 185, 240), inner, border_radius=4)

        # Player head / face circle
        head_cx = dr.centerx + (3 if self.facing_right else -3)
        head_cy = dr.top + 10
        pygame.draw.circle(screen, (255, 220, 180), (head_cx, head_cy), 8)

        # Eyes facing movement direction
        eye_offset = 2 if self.facing_right else -2
        pygame.draw.circle(screen, (30, 30, 40), (head_cx + eye_offset, head_cy - 1), 2)
