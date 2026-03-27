import pygame
import random
import time
import math

pygame.font.init()

# Premium Color Palette
ROAD_COLOR = (45, 48, 54)
GRASS_COLOR = (40, 110, 50)
SHOULDER_COLOR = (100, 100, 110)
WHITE_LINE = (240, 240, 250)
YELLOW_LINE = (255, 204, 0)

# Car Colors
PLAYER_COLOR = (220, 20, 60) # Crimson Red
GLASS_COLOR = (30, 35, 40)
OBSTACLE_COLORS = [(30, 144, 255), (255, 140, 0), (138, 43, 226), (46, 139, 87), (200, 200, 200)]

# UI Colors
TEXT_COLOR = (250, 250, 250)
HIGHLIGHT = (0, 255, 127)

WIDTH, HEIGHT = 400, 600

# Fonts (Premium modern fallback)
try:
    FONT_SM = pygame.font.SysFont("segoeui", 22, bold=True)
    FONT_MD = pygame.font.SysFont("segoeui", 32, bold=True)
    FONT_LG = pygame.font.SysFont("segoeui", 54, bold=True)
except:
    FONT_SM = pygame.font.Font(None, 24)
    FONT_MD = pygame.font.Font(None, 36)
    FONT_LG = pygame.font.Font(None, 64)

def draw_car(surface, x, y, width, height, color):
    # Body shadow
    s_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(s_surface, (0, 0, 0, 80), (4, 4, width, height), border_radius=12)
    surface.blit(s_surface, (x, y))
    
    # Wheels
    wheel_w, wheel_h = 8, 16
    pygame.draw.rect(surface, (10, 10, 10), (x - 2, y + 10, wheel_w, wheel_h), border_radius=3)
    pygame.draw.rect(surface, (10, 10, 10), (x + width - wheel_w + 2, y + 10, wheel_w, wheel_h), border_radius=3)
    pygame.draw.rect(surface, (10, 10, 10), (x - 2, y + height - 26, wheel_w, wheel_h), border_radius=3)
    pygame.draw.rect(surface, (10, 10, 10), (x + width - wheel_w + 2, y + height - 26, wheel_w, wheel_h), border_radius=3)

    # Main Body
    pygame.draw.rect(surface, color, (x, y, width, height), border_radius=12)
    
    # Roof/Cabin reflection (lighter shade)
    lighter = (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 40))
    pygame.draw.rect(surface, lighter, (x + 8, y + 18, width - 16, height - 36), border_radius=8)
    
    # Windshields
    pygame.draw.polygon(surface, GLASS_COLOR, [(x + 10, y + 26), (x + width - 10, y + 26), (x + width - 6, y + 14), (x + 6, y + 14)])
    pygame.draw.polygon(surface, GLASS_COLOR, [(x + 10, y + height - 26), (x + width - 10, y + height - 26), (x + width - 6, y + height - 14), (x + 6, y + height - 14)])
    
    # Headlights
    pygame.draw.ellipse(surface, (255, 255, 220), (x + 4, y + 2, 10, 6))
    pygame.draw.ellipse(surface, (255, 255, 220), (x + width - 14, y + 2, 10, 6))
    
    # Taillights
    pygame.draw.ellipse(surface, (255, 50, 50), (x + 4, y + height - 8, 12, 6))
    pygame.draw.ellipse(surface, (255, 50, 50), (x + width - 16, y + height - 8, 12, 6))

class Particle:
    def __init__(self, x, y, dx, dy, color, life):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.color = color
        self.life = life
        self.initial_life = life

class Game:
    def __init__(self, surface):
        self.surface = surface
        self.width = WIDTH
        self.height = HEIGHT
        
        # Road layout
        self.road_w = int(self.width * 0.70)
        self.road_x = (self.width - self.road_w) // 2
        
        # Car specifics
        self.car_width = 46
        self.car_height = 88
        self.car_x = self.width // 2 - self.car_width // 2
        self.car_y = self.height - self.car_height - 40
        
        # Physics & Speed
        self.speed_multiplier = 0.0
        self.target_speed_multiplier = 0.0
        self.max_game_speed = 18.0
        
        # Steer smoothing
        self.target_x = self.car_x
        
        self.obstacles = []
        self.particles = []
        self.road_offset = 0.0
        
        # Stats
        self.score = 0
        self.start_time = time.time()
        self.difficulty = 1.0
        self.game_over = False
        
        # Lanes centers
        lane_w = self.road_w / 3
        self.lanes = [self.road_x + lane_w * 0.5 - self.car_width / 2,
                      self.road_x + lane_w * 1.5 - self.car_width / 2,
                      self.road_x + lane_w * 2.5 - self.car_width / 2]
                      
    def reset(self):
        self.__init__(self.surface)

    def handle_input(self, gesture, hand_x_normalized):
        if self.game_over:
            if gesture == "accelerate": # Open palm to restart
                self.reset()
            return

        # Steer Logic using Absolute Mapping
        if hand_x_normalized is not None:
            # Clip hand X to a comfortable center playing area
            usable_min = 0.25
            usable_max = 0.75
            clipped_x = max(usable_min, min(hand_x_normalized, usable_max))
            
            # Map this clipped playing area from exactly 0.0 to 1.0
            mapped_ratio = (clipped_x - usable_min) / (usable_max - usable_min)
            
            # Target becomes an absolute position on the road
            safe_left = self.road_x + 5
            safe_right = self.road_x + self.road_w - self.car_width - 5
            self.target_x = safe_left + (mapped_ratio * (safe_right - safe_left))
                
        # Clamp target strictly
        self.target_x = max(self.road_x, min(self.target_x, self.road_x + self.road_w - self.car_width))

        # Speed Control
        if gesture == "accelerate":
            self.target_speed_multiplier = 1.0
        elif gesture == "brake":
            self.target_speed_multiplier = -0.5 # Braking slows you down fast
        else:
            self.target_speed_multiplier = 0.3 # Coasting

    def _spawn_explosion(self, x, y):
        for _ in range(40):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 15)
            life = random.uniform(10, 30)
            color = random.choice([(255, 100, 0), (255, 200, 0), (50, 50, 50)])
            self.particles.append(Particle(x, y, math.cos(angle)*speed, math.sin(angle)*speed, color, life))

    def update(self):
        if self.game_over:
            # Update particles
            for p in self.particles[:]:
                p.x += p.dx
                p.y += p.dy
                p.life -= 1
                if p.life <= 0:
                    self.particles.remove(p)
            return
            
        # Smooth interpolation to target speed
        self.speed_multiplier += (self.target_speed_multiplier - self.speed_multiplier) * 0.05
        self.speed_multiplier = max(0.0, min(1.0, self.speed_multiplier))
        
        # Smooth Steering
        self.car_x += (self.target_x - self.car_x) * 0.2
            
        elapsed = time.time() - self.start_time
        self.difficulty = 1.0 + (elapsed / 30.0)
        
        # Actual game travel speed
        current_speed = 5.0 + (self.max_game_speed * self.speed_multiplier * self.difficulty)
        
        # Exhaust particles
        if self.speed_multiplier > 0.5 and random.random() < 0.3:
            self.particles.append(Particle(self.car_x + self.car_width/2, self.car_y + self.car_height, 
                                           random.uniform(-1, 1), random.uniform(2, 5), (200, 200, 200), 15))
        
        self.road_offset += current_speed
        if self.road_offset > 80:
            self.road_offset -= 80
            
        self.score += current_speed / 60.0 # Score goes up faster when going fast
        
        # Update particles (exhaust)
        for p in self.particles[:]:
            p.x += p.dx
            p.y += p.dy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Update obstacles
        for obs in self.obstacles:
            # relative speed = my speed - obstacle speed
            relative_speed = current_speed - obs['speed']
            obs['y'] += relative_speed
            
        self.obstacles = [obs for obs in self.obstacles if -300 < obs['y'] < self.height + 100]
        
        # Spawn
        max_obs = 2 + int(self.difficulty * 0.7)
        if len(self.obstacles) < max_obs and random.random() < 0.05 * self.difficulty:
            lane = random.choice(self.lanes)
            # Check spacing
            valid = True
            for obs in self.obstacles:
                if abs(obs['x'] - lane) < 10 and obs['y'] < 250:
                    valid = False
            if valid:
                self.obstacles.append({
                    'x': lane,
                    'y': -self.car_height - 20,
                    'color': random.choice(OBSTACLE_COLORS),
                    'speed': random.uniform(3.0 * self.difficulty, 7.0 * self.difficulty) # Other cars
                })
                
        # Collision Check using smaller hitboxes for forgiving UX
        hitbox_margin = 8
        car_rect = pygame.Rect(self.car_x + hitbox_margin, self.car_y + hitbox_margin, 
                               self.car_width - 2*hitbox_margin, self.car_height - 2*hitbox_margin)
        for obs in self.obstacles:
            obs_rect = pygame.Rect(obs['x'] + hitbox_margin, obs['y'] + hitbox_margin, 
                                   self.car_width - 2*hitbox_margin, self.car_height - 2*hitbox_margin)
            if car_rect.colliderect(obs_rect):
                self.game_over = True
                self._spawn_explosion(self.car_x + self.car_width/2, self.car_y + 20)
                
    def draw(self):
        # Background Grass
        self.surface.fill(GRASS_COLOR)
        
        # Road Base
        pygame.draw.rect(self.surface, SHOULDER_COLOR, (self.road_x - 10, 0, self.road_w + 20, self.height))
        pygame.draw.rect(self.surface, ROAD_COLOR, (self.road_x, 0, self.road_w, self.height))
        
        # Outer Yellow Lines
        pygame.draw.line(self.surface, YELLOW_LINE, (self.road_x, 0), (self.road_x, self.height), 4)
        pygame.draw.line(self.surface, YELLOW_LINE, (self.road_x + self.road_w, 0), (self.road_x + self.road_w, self.height), 4)
        
        # Dashed Lane Dividers
        lane_w = self.road_w / 3
        for i in range(1, 3):
            lx = self.road_x + i * lane_w
            for y_dash in range(-100, self.height + 100, 80):
                dy = y_dash + self.road_offset
                if dy > -40 and dy < self.height + 40:
                    pygame.draw.line(self.surface, WHITE_LINE, (lx, dy), (lx, dy + 40), 4)
        
        # Draw Obstacle Cars
        for obs in self.obstacles:
            draw_car(self.surface, obs['x'], obs['y'], self.car_width, self.car_height, obs['color'])
            
        # Draw Player
        if not self.game_over:
            draw_car(self.surface, self.car_x, self.car_y, self.car_width, self.car_height, PLAYER_COLOR)
            
        # Draw Particles
        for p in self.particles:
            alpha = int(255 * (p.life / p.initial_life))
            size = max(1, int(p.life / 3))
            pygame.draw.circle(self.surface, p.color, (int(p.x), int(p.y)), size)

        # --- Premium HUD UI ---
        
        # RPM/Speedometer Arc effect (Visual)
        hud_margin = 20
        # Draw Score panel
        pygame.draw.rect(self.surface, (0, 0, 0, 150), (hud_margin, hud_margin, 120, 70), border_radius=10)
        score_lbl = FONT_SM.render("SCORE", True, (150, 150, 150))
        score_val = FONT_MD.render(f"{int(self.score * 10)}", True, HIGHLIGHT)
        self.surface.blit(score_lbl, (hud_margin + 10, hud_margin + 10))
        self.surface.blit(score_val, (hud_margin + 10, hud_margin + 30))
        
        # Draw Speed panel
        disp_speed = int(self.speed_multiplier * 220) # Max 220 km/h
        pygame.draw.rect(self.surface, (0, 0, 0, 150), (self.width - 140 - hud_margin, hud_margin, 140, 70), border_radius=10)
        spd_lbl = FONT_SM.render("SPEED", True, (150, 150, 150))
        spd_val = FONT_MD.render(f"{disp_speed} km/h", True, (255, 100, 100) if disp_speed > 160 else (255, 255, 255))
        self.surface.blit(spd_lbl, (self.width - 130 - hud_margin, hud_margin + 10))
        self.surface.blit(spd_val, (self.width - 130 - hud_margin, hud_margin + 30))
        
        if self.game_over:
            # Cinematic Dark Overlay
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.surface.blit(overlay, (0, 0))
            
            # Crash Text
            over_text = FONT_LG.render("CRASHED!", True, (255, 50, 50))
            restart_text = FONT_MD.render("Open Palm to Restart", True, TEXT_COLOR)
            
            self.surface.blit(over_text, (self.width // 2 - over_text.get_width() // 2, self.height // 2 - 60))
            self.surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2, self.height // 2 + 20))
