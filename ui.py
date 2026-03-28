import pygame
import sys
from database import register_user, login_user, get_top_scores

pygame.font.init()

# Premium UI Colors
BG_COLOR = (25, 27, 33)
ACCENT_COLOR = (100, 149, 237) # Cornflower Blue
ACCENT_HOVER = (135, 206, 235) # Sky Blue
TEXT_COLOR = (240, 240, 240)
INPUT_BG = (40, 42, 48)
INPUT_ACTIVE = (55, 57, 63)
ERROR_COLOR = (255, 99, 71)

# Fonts
try:
    FONT_TITLE = pygame.font.SysFont("segoeui", 48, bold=True)
    FONT_MAIN = pygame.font.SysFont("segoeui", 28)
    FONT_SMALL = pygame.font.SysFont("segoeui", 20)
except:
    FONT_TITLE = pygame.font.Font(None, 64)
    FONT_MAIN = pygame.font.Font(None, 36)
    FONT_SMALL = pygame.font.Font(None, 24)

class TextInputBox:
    def __init__(self, x, y, w, h, placeholderText=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = INPUT_BG
        self.text = ""
        self.placeholder = placeholderText
        self.active = False
        self.is_password = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.color = INPUT_ACTIVE
            else:
                self.active = False
                self.color = INPUT_BG
        
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return "ENTER"
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
        return None

    def draw(self, screen):
        # Draw box
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
        
        # Draw border
        border_color = ACCENT_COLOR if self.active else (80, 80, 80)
        pygame.draw.rect(screen, border_color, self.rect, width=2, border_radius=8)
        
        # Render text
        display_text = self.text
        if self.is_password and len(self.text) > 0:
            display_text = "*" * len(self.text)
            
        if self.text == "":
            txt_surface = FONT_MAIN.render(self.placeholder, True, (150, 150, 150))
        else:
            txt_surface = FONT_MAIN.render(display_text, True, TEXT_COLOR)
            
        screen.blit(txt_surface, (self.rect.x + 15, self.rect.y + 10))

class Button:
    def __init__(self, x, y, w, h, text, is_secondary=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.is_secondary = is_secondary
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                return True
        return False

    def draw(self, screen):
        bg = ACCENT_HOVER if self.is_hovered else ACCENT_COLOR
        if self.is_secondary:
            bg = (70, 70, 70) if self.is_hovered else (50, 50, 50)
            
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        
        txt_surface = FONT_MAIN.render(self.text, True, TEXT_COLOR)
        txt_rect = txt_surface.get_rect(center=self.rect.center)
        screen.blit(txt_surface, txt_rect)

def run_login_flow(screen, clock):
    width, height = screen.get_size()
    
    # Position inputs closer to vertical center
    center_x = width // 2 - 150
    input_username = TextInputBox(center_x, height//2 - 90, 300, 50, "Username")
    input_password = TextInputBox(center_x, height//2 - 20, 300, 50, "Password")
    input_password.is_password = True
    
    btn_login = Button(center_x, height//2 + 60, 140, 50, "Login")
    btn_register = Button(center_x + 160, height//2 + 60, 140, 50, "Register", is_secondary=True)
    
    message = ""
    message_color = ERROR_COLOR
    
    running = True
    username_result = None
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            input_username.handle_event(event)
            if input_password.handle_event(event) == "ENTER":
                # Handle Enter naturally
                success, msg = login_user(input_username.text, input_password.text)
                if success:
                    username_result = input_username.text
                    running = False
                else:
                    message = msg
                    message_color = ERROR_COLOR
            
            if btn_login.handle_event(event):
                success, msg = login_user(input_username.text, input_password.text)
                if success:
                    username_result = input_username.text
                    running = False
                else:
                    message = msg
                    message_color = ERROR_COLOR
                    
            if btn_register.handle_event(event):
                success, msg = register_user(input_username.text, input_password.text)
                message = msg
                message_color = ACCENT_COLOR if success else ERROR_COLOR

        screen.fill(BG_COLOR)
        
        # Futuristic Pattern / Grid bg
        for i in range(0, width, 40):
            pygame.draw.line(screen, (35, 37, 43), (i, 0), (i, height), 1)
        for i in range(0, height, 40):
            pygame.draw.line(screen, (35, 37, 43), (0, i), (width, i), 1)
        
        # Draw Title
        title_surf = FONT_TITLE.render("GESTURE RACING", True, TEXT_COLOR)
        screen.blit(title_surf, (width//2 - title_surf.get_width()//2, height//2 - 180))
        
        input_username.draw(screen)
        input_password.draw(screen)
        btn_login.draw(screen)
        btn_register.draw(screen)
        
        if message:
            msg_surf = FONT_SMALL.render(message, True, message_color)
            screen.blit(msg_surf, (width//2 - msg_surf.get_width()//2, height//2 + 130))
            
        pygame.display.flip()
        clock.tick(60)
        
    return username_result
