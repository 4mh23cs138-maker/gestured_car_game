import pygame
import random
import time
import math
from database import save_score, get_top_scores

pygame.font.init()

# Window
WIDTH, HEIGHT = 800, 600

# City Colors
ROAD_COLOR = (50, 52, 58)
SIDEWALK_COLOR = (130, 128, 120)
GRASS_COLOR = (40, 115, 50)
BUILDING_COLORS = [(70,80,100),(90,75,85),(60,70,90),(80,90,80),(100,85,75),(75,65,95),(55,80,95),(95,70,70)]
WINDOW_LIT = (200, 220, 255)
WINDOW_OFF = (35, 45, 65)
YELLOW_LINE = (255, 200, 40)
WHITE_LINE = (220, 220, 230)
CROSSWALK = (225, 225, 225)
TREE_COLORS = [(35,130,55),(45,150,60),(30,110,45)]

# Car
PLAYER_COLOR = (220, 30, 55)
GLASS_COLOR = (30, 40, 55)
NPC_COLORS = [(40,120,220),(240,150,20),(130,50,200),(50,140,90),(190,190,200),(220,180,40),(255,255,255),(30,30,30)]

TEXT_COLOR = (250, 250, 250)
HIGHLIGHT = (0, 255, 127)

# City layout
ROAD_W = 80
BLOCK_SIZE = 220
CELL = BLOCK_SIZE + ROAD_W
GRID = 7

try:
    FONT_SM = pygame.font.SysFont("segoeui", 20, bold=True)
    FONT_MD = pygame.font.SysFont("segoeui", 30, bold=True)
    FONT_LG = pygame.font.SysFont("segoeui", 50, bold=True)
except:
    FONT_SM = pygame.font.Font(None, 24)
    FONT_MD = pygame.font.Font(None, 36)
    FONT_LG = pygame.font.Font(None, 64)


class Building:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = random.choice(BUILDING_COLORS)
        self.roof = tuple(min(255, c+25) for c in self.color)
        self.shadow = random.randint(3, 7)
        self.height = random.randint(40, 160)
        self.windows = []
        ws = 8
        # Store relative window positions for 3D roof rendering
        for wx in range(12, w-12, ws+5):
            for wy in range(12, h-12, ws+5):
                self.windows.append((wx, wy, ws, ws, random.random() > 0.4))


class Particle:
    def __init__(self, x, y, dx, dy, color, life):
        self.x, self.y, self.dx, self.dy = x, y, dx, dy
        self.color, self.life, self.initial_life = color, life, life


class TrafficCar:
    def __init__(self, x, y, angle, speed, color):
        self.x, self.y, self.angle, self.speed = x, y, angle, speed
        self.color = color
        self.w, self.h = 36, 70


class Game:
    def __init__(self, surface, username="Guest"):
        self.surface = surface
        self.width, self.height = WIDTH, HEIGHT
        self.username = username
        self.score_submitted = False
        self.top_scores = []

        # Player
        self.car_w, self.car_h = 38, 72
        start_road = 2 * CELL + ROAD_W // 2
        self.car_x = start_road
        self.car_y = start_road + CELL
        self.car_angle = 0.0
        self.car_speed = 0.0
        self.max_speed = 5.0
        self.steering = 0.0
        self.target_speed = 0.0
        self.target_steering = 0.0

        # Camera
        self.cam_x = self.car_x - self.width / 2
        self.cam_y = self.car_y - self.height / 2

        # City
        self.buildings = []
        self.trees = []
        self._generate_city()

        # Traffic
        self.traffic = []
        self._spawn_traffic()

        # 3D Constants
        self.focal_length = 400
        self.horizon = self.height // 2 - 40
        self.cam_h = 45 # Camera height from ground
        self.cam_dist = 120 # Camera distance behind car

        self.dest_dist = 10000.0 # Particular Destiny
        self.is_winner = False

        self.particles = []
        self.score = 0.0
        self.distance = 0.0
        self.start_time = time.time()
        self.game_over = False

    def _generate_city(self):
        # Generate a straight highway with buildings along the sides
        self.buildings = []
        self.trees = []
        # Large city size for the straight road
        self.road_x = (GRID * CELL) // 2
        for z in range(0, 10000, 250):
            # Left side buildings
            if random.random() > 0.3:
                self.buildings.append(Building(self.road_x - BLOCK_SIZE - 20, z, BLOCK_SIZE, 200))
            # Right side buildings
            if random.random() > 0.3:
                self.buildings.append(Building(self.road_x + ROAD_W + 20, z, BLOCK_SIZE, 200))
            # Trees
            if random.random() > 0.5:
                self.trees.append((self.road_x - 12, z + 50, 10, random.choice(TREE_COLORS)))
            if random.random() > 0.5:
                self.trees.append((self.road_x + ROAD_W + 12, z + 120, 10, random.choice(TREE_COLORS)))

    def _spawn_traffic(self):
        # Multiple racers on the same straight road
        self.traffic = []
        for i in range(12):
            lane_x = self.road_x + 10 + (i % 2) * (ROAD_W // 2)
            dist_ahead = -500 - (i * 800) # Spaced far ahead to destination
            self.traffic.append(TrafficCar(lane_x, dist_ahead, 0, random.uniform(3.0, 4.5), random.choice(NPC_COLORS)))

    def reset(self):
        self.__init__(self.surface, self.username)

    def _on_road(self, x, y):
        for g in range(GRID + 1):
            rl = g * CELL
            if rl <= x <= rl + ROAD_W:
                return True
            if rl <= y <= rl + ROAD_W:
                return True
        return False

    def handle_input(self, gesture, hand_x_normalized):
        if self.game_over or self.is_winner:
            if gesture == "accelerate":
                self.reset()
            return

        if hand_x_normalized is not None:
            lo, hi = 0.25, 0.75
            c = max(lo, min(hand_x_normalized, hi))
            self.target_steering = ((c - lo) / (hi - lo)) * 2 - 1

        if gesture == "accelerate":
            self.target_speed = self.max_speed
        elif gesture == "brake":
            self.target_speed = -1.0
        else:
            self.target_speed = self.max_speed * 0.3

    def _explode(self, x, y):
        for _ in range(35):
            a = random.uniform(0, math.pi * 2)
            s = random.uniform(2, 12)
            self.particles.append(Particle(x, y, math.cos(a)*s, math.sin(a)*s,
                                           random.choice([(255,100,0),(255,200,0),(50,50,50)]),
                                           random.uniform(10, 30)))

    def update(self):
        if self.game_over:
            for p in self.particles[:]:
                p.x += p.dx; p.y += p.dy; p.life -= 1
                if p.life <= 0: self.particles.remove(p)
            return

        self.car_speed += (self.target_speed - self.car_speed) * 0.08
        self.steering += (self.target_steering - self.steering) * 0.15

        # Straight Line Only - Direction is fixed to 0
        self.car_angle = 0
        
        # Lateral movement (lane change) based on steering
        self.car_x += self.steering * 4.0 * (self.car_speed / self.max_speed)
        self.car_y -= self.car_speed # Moving forward along Y axis
        
        # Keep car on road bounds
        self.car_x = max(self.road_x + 5, min(self.road_x + ROAD_W - 5, self.car_x))

        # Reset city if we travel too far (endless)
        if self.car_y < -5000:
            self.car_y += 10000
            for b in self.buildings: b.rect.y += 10000
            for t in self.trees: pass # TBD trees reuse

        d = abs(self.car_speed)
        self.distance += d
        self.score = self.distance / 10.0

        # Check if reached destination
        if not self.game_over and not self.is_winner:
            if self.distance >= self.dest_dist:
                self.is_winner = True
                self._capture_win()

        # Update Competitor Racers
        for t in self.traffic:
            # They drive along the Y axis toward the destination
            t.y -= t.speed
            # Very simple AI: stay in lane
            t.x = max(self.road_x + 5, min(self.road_x + ROAD_W - 5, t.x))

        # Collision - racers
        if not self.game_over and not self.is_winner:
            for t in self.traffic:
                # 3D Depth collision check
                if abs(self.car_x - t.x) < 30 and abs(self.car_y - t.y) < 40:
                    self._end_game()
                    break


        # Exhaust
        if abs(self.car_speed) > 2 and random.random() < 0.3:
            ex = self.car_x + math.sin(self.car_angle) * self.car_h/2
            ey = self.car_y + math.cos(self.car_angle) * self.car_h/2
            self.particles.append(Particle(ex, ey, random.uniform(-0.5,0.5), random.uniform(-0.5,0.5), (180,180,180), 15))

        for p in self.particles[:]:
            p.x += p.dx; p.y += p.dy; p.life -= 1
            if p.life <= 0: self.particles.remove(p)



        # Collision - buildings
        if not self.game_over:
            for b in self.buildings:
                if b.rect.inflate(-10, -10).collidepoint(self.car_x, self.car_y):
                    self._end_game()
                    break

    def _capture_win(self):
        # Save score for reaching destination
        if not self.score_submitted:
            save_score(self.username, int(self.score * 12)) # Bonus for destiny
            self.top_scores = get_top_scores(5)
            self.score_submitted = True

    def _end_game(self):
        self.game_over = True
        self._explode(self.car_x, self.car_y)
        if not self.score_submitted:
            save_score(self.username, int(self.score * 10))
            self.top_scores = get_top_scores(5)
            self.score_submitted = True

    def _project(self, wx, wy, wz):
        # Local space relative to camera
        # wy is height (ground = 0)
        # wz is depth (distance from camera)
        
        # Avoid division by zero
        depth = max(1.0, wz)
        scale = self.focal_length / depth
        
        sx = self.width // 2 + (wx * scale)
        sy = self.horizon + ((self.cam_h - wy) * scale)
        
        return int(sx), int(sy), scale

    def _world_to_cam(self, wx, wy):
        # Convert absolute world coords to camera-relative coords
        # Based on car position and angle
        
        # Camera is placed behind the car
        cx = self.car_x + math.sin(self.car_angle) * self.cam_dist
        cy = self.car_y + math.cos(self.car_angle) * self.cam_dist
        
        dx = wx - cx
        dy = wy - cy
        
        # Rotate based on car angle so camera looks forward
        rx = dx * math.cos(self.car_angle) - dy * math.sin(self.car_angle)
        rz = -(dx * math.sin(self.car_angle) + dy * math.cos(self.car_angle))
        
        return rx, rz

    def draw(self):
        # Draw Background (Sky and Ground)
        pygame.draw.rect(self.surface, (30, 40, 60), (0, 0, self.width, self.horizon))
        pygame.draw.rect(self.surface, GRASS_COLOR, (0, self.horizon, self.width, self.height - self.horizon))
        
        # Atmosphere glow
        glow = pygame.Surface((self.width, 100), pygame.SRCALPHA)
        for i in range(100):
            alpha = int(100 * (1 - i/100.0))
            pygame.draw.line(glow, (100, 150, 255, alpha), (0, i), (self.width, i))
        self.surface.blit(glow, (0, self.horizon - 50))

        # We will draw elements sorted by depth (Z)
        draw_queue = []

        # -- ROAD (Single Straight Highway) --
        world_rx = self.road_x
        # Draw road segments ahead and slightly behind
        for i in range(-5, 45):
            z_start = (int(self.car_y / 250) + i) * 250
            z_end = z_start + 250
            
            rx1, rz1 = self._world_to_cam(world_rx, z_start)
            rx2, rz2 = self._world_to_cam(world_rx + ROAD_W, z_start)
            rx3, rz3 = self._world_to_cam(world_rx + ROAD_W, z_end)
            rx4, rz4 = self._world_to_cam(world_rx, z_end)
            
            if rz1 > 1 or rz3 > 1:
                p1 = self._project(rx1, 0, rz1)
                p2 = self._project(rx2, 0, rz2)
                p3 = self._project(rx3, 0, rz3)
                p4 = self._project(rx4, 0, rz4)
                
                # Checkered Finish Line at the end
                if z_start >= self.dest_dist - 200:
                    col = (255, 255, 255) if (int(z_start/50) % 2 == 0) else (30,30,30)
                else:
                    # Alternate color for speed sensation
                    col = ROAD_COLOR if (int(z_start/250) % 2 == 0) else (42, 45, 52)
                
                pygame.draw.polygon(self.surface, col, [p1[:2], p2[:2], p3[:2], p4[:2]])
                
                # Center lane markings
                mid_x = world_rx + ROAD_W // 2
                mx1, mz1 = self._world_to_cam(mid_x, z_start)
                mx2, mz2 = self._world_to_cam(mid_x, z_start + 50)
                if mz1 > 10:
                    pm1 = self._project(mx1, 0, mz1)
                    pm2 = self._project(mx2, 0, mz2)
                    pygame.draw.line(self.surface, WHITE_LINE, pm1[:2], pm2[:2], max(1, int(3 * pm1[2])))

        # Objects
        view_dist = 2200
        draw_queue = []

        # Buildings
        for b in self.buildings:
            dist = math.sqrt((b.rect.centerx - self.car_x)**2 + (b.rect.centery - self.car_y)**2)
            if dist < view_dist:
                rx_base, rz_base = self._world_to_cam(b.rect.x, b.rect.y)
                # Only if in front of camera
                if rz_base > 10:
                    draw_queue.append((rz_base, 'building', b))

        # Trees
        for (tx, ty, sz, col) in self.trees:
            dist = math.sqrt((tx - self.car_x)**2 + (ty - self.car_y)**2)
            if dist < view_dist:
                rx, rz = self._world_to_cam(tx, ty)
                if rz > 10:
                    draw_queue.append((rz, 'tree', tx, ty, sz, col))

        # Traffic
        for t in self.traffic:
            dist = math.sqrt((t.x - self.car_x)**2 + (t.y - self.car_y)**2)
            if dist < view_dist:
                rx, rz = self._world_to_cam(t.x, t.y)
                if rz > 5:
                    draw_queue.append((rz, 'traffic', t))

        # Sort draw queue by depth (descending Z - furthest first)
        draw_queue.sort(key=lambda x: x[0], reverse=True)

        # Actual Drawing
        for item in draw_queue:
            depth = item[0]
            type = item[1]
            if type == 'polygon':
                pygame.draw.polygon(self.surface, item[2], item[3])
            elif type == 'tree':
                tx, ty, sz, col = item[2], item[3], item[4], item[5]
                rx, rz = self._world_to_cam(tx, ty)
                sx, sy, sc = self._project(rx, 0, rz)
                # Tree height
                th = 40 * sc
                pygame.draw.line(self.surface, (90,60,35), (sx, sy), (sx, sy - th), max(1, int(3*sc)))
                pygame.draw.circle(self.surface, col, (sx, int(sy - th)), int(sz * sc))
            elif type == 'traffic':
                t = item[2]
                rx, rz = self._world_to_cam(t.x, t.y)
                self._draw_car_3d(rx, rz, t.angle - self.car_angle, t.w, t.h, t.color)
            elif type == 'building':
                b = item[2]
                self._draw_building_3d(b)

        # Player (Always on top, fixed position in 3D chase view)
        if not self.game_over:
            # Player is at a fixed screen position in chase view
            # Slightly above center bottom
            self._draw_car_3d(0, self.cam_dist, 0, self.car_w, self.car_h, PLAYER_COLOR, True)

        # Particles
        for p in self.particles:
            rx, rz = self._world_to_cam(p.x, p.y)
            if rz > 5:
                sx, sy, sc = self._project(rx, 0, rz)
                sz = max(1, int(p.life / 3 * sc))
                pygame.draw.circle(self.surface, p.color, (sx, sy), sz)

        self._draw_hud()
        if self.is_winner:
            self._draw_winner()
        elif self.game_over:
            self._draw_game_over()

    def _draw_building_3d(self, b):
        # Project 4 base corners
        corners = [
            (b.rect.x, b.rect.y),
            (b.rect.x + b.rect.w, b.rect.y),
            (b.rect.x + b.rect.w, b.rect.y + b.rect.h),
            (b.rect.x, b.rect.y + b.rect.h)
        ]
        
        proj_base = []
        proj_roof = []
        for (wx, wy) in corners:
            rx, rz = self._world_to_cam(wx, wy)
            if rz < 5: return # Clipping
            sx, sy, sc = self._project(rx, 0, rz)
            proj_base.append((sx, sy))
            
            # Roof corner
            sxr, syr, scr = self._project(rx, b.height, rz)
            proj_roof.append((sxr, syr))

        # Draw sides
        side_shadow = tuple(max(0, c - 40) for c in b.color)
        side_light = tuple(min(255, c + 20) for c in b.color)
        
        # Simple side drawing (back to front faces would be better but complex)
        for i in range(4):
            i2 = (i + 1) % 4
            pts = [proj_base[i], proj_base[i2], proj_roof[i2], proj_roof[i]]
            pygame.draw.polygon(self.surface, side_shadow if i % 2 == 0 else side_light, pts)

        # Draw Roof
        pygame.draw.polygon(self.surface, b.color, proj_roof)
        pygame.draw.polygon(self.surface, b.roof, proj_roof, width=2)

    def _draw_car_3d(self, rx, rz, rel_angle, w, h, color, player=False):
        # Projected dimensions
        sx, sy, sc = self._project(rx, 0, rz)
        sw = w * sc
        sh = h * sc
        ch = 22 * sc # Visual car height
        
        # Rear-view perspective box
        b1 = (sx - sw/2, sy)
        b2 = (sx + sw/2, sy)
        t1 = (sx - sw/2 * 0.9, sy - ch) # Top corners (closer to center for perspective)
        t2 = (sx + sw/2 * 0.9, sy - ch)
        
        # Colors
        darker = tuple(max(0, c - 40) for c in color)
        lighter = tuple(min(255, c + 35) for c in color)
        
        # Draw Body (Rear Face)
        pygame.draw.polygon(self.surface, darker, [b1, b2, t2, t1])
        
        # Draw Roof (Top Face)
        # We assume the car has some length, but we only see the rear/top mostly
        # Shift roof slightly "forward" into perspective
        r1 = (t1[0], t1[1] - 5*sc)
        r2 = (t2[0], t2[1] - 5*sc)
        tr1 = (sx - sw/2 * 0.7, sy - ch - 15*sc)
        tr2 = (sx + sw/2 * 0.7, sy - ch - 15*sc)
        pygame.draw.polygon(self.surface, color, [t1, t2, tr2, tr1])
        
        # Rear Window
        win_w, win_h = sw * 0.6, ch * 0.45
        pygame.draw.rect(self.surface, (30, 45, 65), (sx - win_w/2, t1[1] + 2, win_w, win_h), border_radius=int(2*sc))
        
        # Taillights (Red)
        lr_w, lr_h = sw * 0.22, ch * 0.2
        pygame.draw.rect(self.surface, (180, 0, 0), (b1[0] + 4, t1[1] + win_h + 4, lr_w, lr_h), border_radius=1)
        pygame.draw.rect(self.surface, (180, 0, 0), (b2[0] - lr_w - 4, t1[1] + win_h + 4, lr_w, lr_h), border_radius=1)
        
        # Brake Lights Glow (Only if player and target speed is braking)
        if player and self.target_speed < 0:
            pygame.draw.rect(self.surface, (255, 50, 50), (b1[0] + 4, t1[1] + win_h + 4, lr_w, lr_h), border_radius=1)
            pygame.draw.rect(self.surface, (255, 50, 50), (b2[0] - lr_w - 4, t1[1] + win_h + 4, lr_w, lr_h), border_radius=1)
            # Glow halo
            glow_surf = pygame.Surface((sw*2, ch*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 0, 0, 45), (sw, ch), int(15*sc))
            self.surface.blit(glow_surf, (sx - sw, sy - ch*1.5))
            
        # Outline
        pygame.draw.polygon(self.surface, (20, 20, 25), [b1, b2, t2, t1], 1)
        pygame.draw.polygon(self.surface, (20, 20, 25), [t1, t2, tr2, tr1], 1)

    def _draw_car(self, wx, wy, angle, w, h, color, player=False):
        pad = 24
        surf = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
        cx, cy = surf.get_width() // 2, surf.get_height() // 2
        ox, oy = cx - w // 2, cy - h // 2

        # -- Shadow under car --
        shadow = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 50), (ox - 3, oy + 2, w + 6, h + 2))
        surf.blit(shadow, (0, 0))

        # -- Headlight beams (glow forward) --
        if player or random.random() > 0.7:
            beam = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
            pygame.draw.polygon(beam, (255, 255, 180, 18), [
                (ox + 5, oy + 2), (ox + w - 5, oy + 2),
                (ox + w + 8, oy - 20), (ox - 8, oy - 20)])
            surf.blit(beam, (0, 0))

        # -- Wheels with tire + rim detail --
        wheel_positions = [
            (ox - 3, oy + 10), (ox + w - 5, oy + 10),
            (ox - 3, oy + h - 22), (ox + w - 5, oy + h - 22)]
        for (wpx, wpy) in wheel_positions:
            # Tire
            pygame.draw.rect(surf, (20, 20, 20), (wpx, wpy, 8, 14), border_radius=3)
            # Rim
            pygame.draw.rect(surf, (120, 120, 130), (wpx + 2, wpy + 3, 4, 8), border_radius=2)
            # Rim shine
            pygame.draw.line(surf, (180, 180, 190), (wpx + 3, wpy + 4), (wpx + 3, wpy + 10), 1)

        # -- Main body (contoured polygon, not rectangle) --
        body_pts = [
            (ox + 4, oy),           # front-left
            (ox + w - 4, oy),       # front-right
            (ox + w, oy + 8),       # fender-right
            (ox + w, oy + h - 8),
            (ox + w - 4, oy + h),   # rear-right
            (ox + 4, oy + h),       # rear-left
            (ox, oy + h - 8),
            (ox, oy + 8)]
        pygame.draw.polygon(surf, color, body_pts)
        # Body outline
        pygame.draw.polygon(surf, tuple(max(0, c - 35) for c in color), body_pts, 2)

        # -- Metallic shading (gradient bands) --
        darker = tuple(max(0, c - 20) for c in color)
        lighter = tuple(min(255, c + 35) for c in color)
        highlight = tuple(min(255, c + 55) for c in color)
        # Left shade
        pygame.draw.rect(surf, darker, (ox + 1, oy + 8, 5, h - 16))
        # Right shade
        pygame.draw.rect(surf, darker, (ox + w - 6, oy + 8, 5, h - 16))
        # Center highlight strip
        pygame.draw.rect(surf, lighter, (ox + w//2 - 2, oy + 6, 4, h - 12))

        # -- Hood panel --
        hood_pts = [(ox + 6, oy + 4), (ox + w - 6, oy + 4),
                    (ox + w - 8, oy + 16), (ox + 8, oy + 16)]
        pygame.draw.polygon(surf, lighter, hood_pts)
        pygame.draw.polygon(surf, tuple(max(0, c - 10) for c in color), hood_pts, 1)

        # -- Trunk panel --
        trunk_pts = [(ox + 6, oy + h - 4), (ox + w - 6, oy + h - 4),
                     (ox + w - 8, oy + h - 14), (ox + 8, oy + h - 14)]
        pygame.draw.polygon(surf, lighter, trunk_pts)

        # -- Windshield (front glass with tint) --
        ws_pts = [(ox + 6, oy + 17), (ox + w - 6, oy + 17),
                  (ox + w - 4, oy + 10), (ox + 4, oy + 10)]
        pygame.draw.polygon(surf, (40, 55, 75), ws_pts)
        # Glass reflection
        pygame.draw.line(surf, (80, 100, 140), (ox + 8, oy + 13), (ox + w//2 - 2, oy + 11), 1)

        # -- Rear window --
        rw_pts = [(ox + 7, oy + h - 17), (ox + w - 7, oy + h - 17),
                  (ox + w - 5, oy + h - 11), (ox + 5, oy + h - 11)]
        pygame.draw.polygon(surf, (35, 45, 65), rw_pts)

        # -- Roof / cabin --
        roof_pts = [(ox + 8, oy + 20), (ox + w - 8, oy + 20),
                    (ox + w - 8, oy + h - 20), (ox + 8, oy + h - 20)]
        pygame.draw.polygon(surf, highlight, roof_pts)
        pygame.draw.polygon(surf, tuple(max(0, c - 5) for c in color), roof_pts, 1)
        # Roof shine
        pygame.draw.line(surf, (255, 255, 255, 60), (cx - 1, oy + 22), (cx - 1, oy + h - 22), 1)

        # -- Side windows --
        # Left windows
        pygame.draw.rect(surf, (50, 65, 90), (ox + 2, oy + 20, 5, 12))
        pygame.draw.rect(surf, (50, 65, 90), (ox + 2, oy + h - 32, 5, 12))
        # Right windows
        pygame.draw.rect(surf, (50, 65, 90), (ox + w - 7, oy + 20, 5, 12))
        pygame.draw.rect(surf, (50, 65, 90), (ox + w - 7, oy + h - 32, 5, 12))

        # -- Door lines --
        pygame.draw.line(surf, tuple(max(0, c - 30) for c in color),
                         (ox + 8, oy + h//2), (ox + w - 8, oy + h//2), 1)

        # -- Side mirrors --
        pygame.draw.ellipse(surf, tuple(max(0, c - 15) for c in color),
                            (ox - 5, oy + 18, 6, 4))
        pygame.draw.ellipse(surf, tuple(max(0, c - 15) for c in color),
                            (ox + w - 1, oy + 18, 6, 4))

        # -- Headlights --
        pygame.draw.ellipse(surf, (255, 255, 220), (ox + 4, oy, 9, 6))
        pygame.draw.ellipse(surf, (255, 255, 220), (ox + w - 13, oy, 9, 6))
        # Inner bright
        pygame.draw.ellipse(surf, (255, 255, 255), (ox + 6, oy + 1, 5, 3))
        pygame.draw.ellipse(surf, (255, 255, 255), (ox + w - 11, oy + 1, 5, 3))

        # -- Taillights --
        pygame.draw.rect(surf, (255, 20, 20), (ox + 3, oy + h - 5, 10, 4), border_radius=2)
        pygame.draw.rect(surf, (255, 20, 20), (ox + w - 13, oy + h - 5, 10, 4), border_radius=2)
        # Brake glow
        pygame.draw.rect(surf, (255, 80, 80, 80), (ox + 2, oy + h - 6, 12, 6), border_radius=3)
        pygame.draw.rect(surf, (255, 80, 80, 80), (ox + w - 14, oy + h - 6, 12, 6), border_radius=3)

        # -- Player special effects --
        if player:
            # Glow ring under car
            glow = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 60, 60, 28), (ox - 6, oy - 4, w + 12, h + 8))
            surf.blit(glow, (0, 0))
            # Direction arrow above car
            arrow_y = oy - 12
            arrow_pts = [(cx, arrow_y - 6), (cx - 5, arrow_y + 2), (cx + 5, arrow_y + 2)]
            pygame.draw.polygon(surf, (255, 255, 100, 200), arrow_pts)

        # Rotate and blit
        rotated = pygame.transform.rotate(surf, math.degrees(angle))
        sx, sy = self._w2s(wx, wy)
        self.surface.blit(rotated, rotated.get_rect(center=(sx, sy)))

    def _draw_hud(self):
        m = 12
        # Score
        p = pygame.Surface((125, 58), pygame.SRCALPHA); p.fill((0,0,0,170))
        pygame.draw.rect(p, (100,100,255,50), (0,0,125,58), width=1, border_radius=8)
        self.surface.blit(p, (m, m))
        self.surface.blit(FONT_SM.render("SCORE", True, (140,140,170)), (m+8, m+4))
        self.surface.blit(FONT_MD.render(f"{int(self.score*10)}", True, HIGHLIGHT), (m+8, m+24))

        # Speed
        spd = int(abs(self.car_speed) / self.max_speed * 180)
        p2 = pygame.Surface((140, 58), pygame.SRCALPHA); p2.fill((0,0,0,170))
        pygame.draw.rect(p2, (100,100,255,50), (0,0,140,58), width=1, border_radius=8)
        self.surface.blit(p2, (self.width-140-m, m))
        self.surface.blit(FONT_SM.render("SPEED", True, (140,140,170)), (self.width-132-m, m+4))
        sc = (255,100,100) if spd > 140 else TEXT_COLOR
        self.surface.blit(FONT_MD.render(f"{spd} km/h", True, sc), (self.width-132-m, m+24))

        # Progress Bar to Destiny
        pb_w = 400
        pb_h = 10
        pb_x = self.width // 2 - pb_w // 2
        pb_y = 50
        pygame.draw.rect(self.surface, (0,0,0,150), (pb_x, pb_y, pb_w, pb_h), border_radius=5)
        progress = min(1.0, self.distance / self.dest_dist)
        pygame.draw.rect(self.surface, HIGHLIGHT, (pb_x, pb_y, int(pb_w * progress), pb_h), border_radius=5)
        label = FONT_SM.render("DESTINY", True, (180,180,180))
        self.surface.blit(label, (pb_x + pb_w//2 - label.get_width()//2, pb_y - 25))
        
        # Race indicator
        self.surface.blit(FONT_SM.render("MULTI-RACE MODE", True, HIGHLIGHT), (m, self.height - 40))

    def _draw_winner(self):
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0, 30, 0, 180)) # Greenish overlay for win
        self.surface.blit(ov, (0,0))
        
        t1 = FONT_LG.render("DESTINATION REACHED!", True, (100, 255, 100))
        t2 = FONT_MD.render(f"Final Score: {int(self.score * 12)}", True, (255, 255, 255))
        t3 = FONT_SM.render("Open Palm to Play Again", True, (200, 200, 200))
        
        self.surface.blit(t1, (self.width//2 - t1.get_width()//2, self.height//2 - 120))
        self.surface.blit(t2, (self.width//2 - t2.get_width()//2, self.height//2 - 40))
        self.surface.blit(t3, (self.width//2 - t3.get_width()//2, self.height//2 + 40))

    def _draw_game_over(self):
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0,0,0,200))
        self.surface.blit(ov, (0,0))

        t1 = FONT_LG.render("CRASHED!", True, (255,60,60))
        t2 = FONT_SM.render("Open Palm to Restart", True, (200,200,200))
        self.surface.blit(t1, (self.width//2 - t1.get_width()//2, self.height//2 - 190))
        self.surface.blit(t2, (self.width//2 - t2.get_width()//2, self.height//2 - 140))

        pw, ph = 340, 220
        px, py = self.width//2 - pw//2, self.height//2 - 70
        ps = pygame.Surface((pw, ph), pygame.SRCALPHA); ps.fill((30,32,38,230))
        pygame.draw.rect(ps, (100,149,237), (0,0,pw,ph), width=2, border_radius=14)
        self.surface.blit(ps, (px, py))

        lb = FONT_MD.render("LEADERBOARD", True, (240,240,240))
        self.surface.blit(lb, (self.width//2 - lb.get_width()//2, py+12))
        pygame.draw.line(self.surface, (100,149,237), (px+20, py+50), (px+pw-20, py+50), 2)

        yo = py + 62
        for i, (u, s) in enumerate(self.top_scores):
            c = (255,215,0) if i==0 else (192,192,192) if i==1 else (205,127,50) if i==2 else (170,170,170)
            self.surface.blit(FONT_SM.render(f"#{i+1}", True, c), (px+25, yo))
            fc = (255,255,255) if u == self.username else (195,195,195)
            self.surface.blit(FONT_SM.render(u, True, fc), (px+65, yo))
            sv = FONT_SM.render(str(s), True, fc)
            self.surface.blit(sv, (px+pw-25-sv.get_width(), yo))
            yo += 30
