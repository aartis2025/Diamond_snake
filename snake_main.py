import pygame as pg
import sys
import math
import random
from snake_settings import *
from snake_logic import Snake, Food
from snake_ai import bfs, get_safe_move
import snake_vfx

class Game:
    def __init__(self):
        pg.init()
        pg.mixer.init()
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        pg.display.set_caption("AI Snake: Realistic Reptile 💎🐍")
        self.clock = pg.time.Clock()
        self.mini_font = pg.font.SysFont("Courier New", 14, bold=True)
        self.font = pg.font.SysFont("Courier New", 18, bold=True)
        self.stat_font = pg.font.SysFont("Courier New", 18, bold=True)
        self.title_font = pg.font.SysFont("Courier New", 24, bold=True)
        
        self.current_fps = FPS_MEDIUM
        self.difficulty = "MEDIUM"
        self.load_assets()
        self.vfx = snake_vfx.VFXManager()
        self.state = STATE_MENU
        self.auto_mode = True
        self.pulse_val = 0
        self.frame_count = 0
        self.reset()

    def load_assets(self):
        class DummySound:
            def play(self): pass
            def set_volume(self, vol): pass

        # Initialize with dummy sounds first to prevent AttributeError if loading fails
        self.eat_snd = DummySound()
        self.crash_snd = DummySound()
        self.toggle_snd = DummySound()
        self.head_img = pg.Surface((GRID_SIZE, GRID_SIZE))

        try:
            if pg.image.get_extended():
                self.head_img = pg.image.load(HEAD_IMG).convert() 
                self.head_img.set_colorkey((255, 255, 255))
                self.head_img = self.head_img.convert_alpha() 
                self.head_img = pg.transform.scale(self.head_img, (GRID_SIZE, GRID_SIZE))
            
            self.eat_snd = pg.mixer.Sound("assets/eat_soft.wav")
            self.eat_snd.set_volume(0.12)
            self.crash_snd = pg.mixer.Sound(CRASH_SFX)
            self.crash_snd.set_volume(0.2)
            self.toggle_snd = pg.mixer.Sound(TOGGLE_SFX)
            self.toggle_snd.set_volume(0.12)
        except Exception as e:
            print(f"Note: Some assets could not be loaded ({e}). Game will continue without them.")

    def reset(self):
        self.snake = Snake()
        self.food = Food(self.snake.body)
        self.game_over = False

    def set_difficulty(self, level):
        self.difficulty = level
        if level == "EASY": self.current_fps = FPS_EASY
        elif level == "MEDIUM": self.current_fps = FPS_MEDIUM
        elif level == "HARD": self.current_fps = FPS_HARD
        self.toggle_snd.play()

    def draw_organic_segment(self, surface, pos, color, radius, is_head=False):
        """Draws a segment with realistic spotted textures and gloss."""
        # 1. Base Layer (Body)
        for r in range(radius, 2, -2):
            alpha = int(240 * (1 - (r / radius) * 0.4))
            pg.draw.circle(surface, (*color, alpha), pos, r)
        
        # 2. Spotted Texture (Realistic reptilian spots)
        if not is_head:
            # Draw 3-4 small spots of varying size
            offsets = [(0, -radius//3), (-radius//3, radius//4), (radius//3, radius//4)]
            for ox, oy in offsets:
                s_radius = max(1, radius // 5)
                pg.draw.circle(surface, SCALE_COLOR, (pos[0]+ox, pos[1]+oy), s_radius)
                # Subtle center highlight for each spot
                pg.draw.circle(surface, (255, 255, 255, 50), (pos[0]+ox, pos[1]+oy), 1)

        # 3. Specular High-End Gloss (3D light glint)
        gloss_pos = (pos[0] - radius//3, pos[1] - radius//3)
        pg.draw.circle(surface, (255, 255, 255, GLOSS_ALPHA), gloss_pos, radius//3)
        # Tiny bright core
        pg.draw.circle(surface, (255, 255, 255, 200), (gloss_pos[0]-1, gloss_pos[1]-1), 1)

    def draw_crystal_frog(self, surface, center):
        """Draws a refined procedural frog."""
        pulse = (math.sin(self.pulse_val * 4) + 1) / 2
        radius = int(GRID_SIZE // 2.8)
        color = (80, 220, 80)
        
        snake_vfx.draw_soft_glow(surface, center, (100, 255, 100), int(radius * (1.6 + 0.2 * pulse)))
        
        # Hind Legs
        pg.draw.ellipse(surface, (50, 150, 50), (center[0]-radius-2, center[1], radius, radius//1.2))
        pg.draw.ellipse(surface, (50, 150, 50), (center[0]+2, center[1], radius, radius//1.2))
        
        # Body
        pg.draw.ellipse(surface, color, (center[0]-radius, center[1]-radius, radius*2, radius*1.5))
        pg.draw.ellipse(surface, (180, 255, 180), (center[0]-radius//1.5, center[1]-radius//4, radius*1.3, radius//1.5))
        
        # Eyes
        for side in [-1, 1]:
            ex, ey = center[0] + (side * 6), center[1] - (radius // 1.4)
            pg.draw.circle(surface, color, (ex, ey), 5)
            pg.draw.circle(surface, (255, 255, 255), (ex, ey), 4)
            pg.draw.circle(surface, (0, 0, 0), (ex, ey), 2)

    def draw_header(self):
        header_rect = pg.Rect(0, 0, WIDTH, HEADER_HEIGHT)
        snake_vfx.draw_glass_rect(self.screen, header_rect, (20, 20, 35), alpha=245)
        pg.draw.line(self.screen, SNAKE_START, (0, HEADER_HEIGHT-1), (WIDTH, HEADER_HEIGHT-1), 3)

        self.pulse_val += 0.05
        glow = int(180 + 75 * math.sin(self.pulse_val))
        title_surf = self.title_font.render("DIAMOND SNAKE", True, (0, glow, glow))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 70))
        self.screen.blit(title_surf, title_rect)

        mode_text = "MODE: AI AUTO" if self.auto_mode else "MODE: MANUAL"
        mode_surf = self.stat_font.render(mode_text, True, SNAKE_START if self.auto_mode else SNAKE_END)
        self.screen.blit(mode_surf, (30, 45))
        
        score_surf = self.stat_font.render(f"SCORE: {self.snake.score:03d}", True, TEXT_COLOR)
        self.screen.blit(score_surf, (30, 85))

        diff_label = self.mini_font.render("SYSTEM DIFFICULTY:", True, YELLOW)
        self.screen.blit(diff_label, (WIDTH - 180, 45))
        
        btn_w, btn_h = 45, 28
        self.btn_easy = pg.Rect(WIDTH - 180, 80, btn_w, btn_h)
        self.btn_medium = pg.Rect(WIDTH - 128, 80, btn_w, btn_h)
        self.btn_hard = pg.Rect(WIDTH - 76, 80, btn_w, btn_h)

        mpos = pg.mouse.get_pos()
        self.draw_button(self.btn_easy, "E", (40, 40, 50), self.btn_easy.collidepoint(mpos), mini=True)
        self.draw_button(self.btn_medium, "M", (40, 40, 50), self.btn_medium.collidepoint(mpos), mini=True)
        self.draw_button(self.btn_hard, "H", (40, 40, 50), self.btn_hard.collidepoint(mpos), mini=True)

    def draw_footer(self):
        footer_y = HEIGHT - FOOTER_HEIGHT
        footer_rect = pg.Rect(0, footer_y, WIDTH, FOOTER_HEIGHT)
        pg.draw.rect(self.screen, (10, 10, 15), footer_rect)
        pg.draw.line(self.screen, GRID_COLOR, (0, footer_y), (WIDTH, footer_y), 2)

        btn_w, btn_h = 100, 38
        start_x = WIDTH // 2 - (btn_w * 4 + 18 * 3) // 2
        
        self.btn_start = pg.Rect(start_x, footer_y + 40, btn_w, btn_h)
        self.btn_pause = pg.Rect(start_x + btn_w + 18, footer_y + 40, btn_w, btn_h)
        self.btn_mode = pg.Rect(start_x + (btn_w + 18) * 2, footer_y + 40, btn_w * 1.5, btn_h)
        self.btn_stop = pg.Rect(start_x + (btn_w + 18) * 3 + btn_w//2, footer_y + 40, btn_w, btn_h)

        mpos = pg.mouse.get_pos()
        mode_btn_text = "HUMAN MODE" if self.auto_mode else "AI MODE"
        
        self.draw_button(self.btn_start, "START", (30, 60, 30), self.btn_start.collidepoint(mpos))
        self.draw_button(self.btn_pause, "PAUSE", (60, 60, 30), self.btn_pause.collidepoint(mpos))
        self.draw_button(self.btn_mode, mode_btn_text, (40, 50, 90), self.btn_mode.collidepoint(mpos))
        self.draw_button(self.btn_stop, "QUIT", (80, 40, 40), self.btn_stop.collidepoint(mpos))

    def draw_button(self, rect, text, color, hover=False, mini=False):
        btn_color = (color[0]+20, color[1]+20, color[2]+20) if hover else color
        is_active = (mini and ((text=="E" and self.difficulty=="EASY") or (text=="M" and self.difficulty=="MEDIUM") or (text=="H" and self.difficulty=="HARD")))
        if is_active: pg.draw.rect(self.screen, SNAKE_START, rect.inflate(4, 4), width=2, border_radius=8)
        snake_vfx.draw_glass_rect(self.screen, rect, btn_color, alpha=230)
        font = self.mini_font if mini else (self.mini_font if len(text) > 8 else self.font)
        text_surf = font.render(text, True, WHITE)
        self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    def draw_game(self):
        game_surf = pg.Surface((GAME_WIDTH, GAME_HEIGHT), pg.SRCALPHA)
        game_surf.fill(BG_COLOR)
        
        for x in range(0, GAME_WIDTH, GRID_SIZE): pg.draw.line(game_surf, (20, 20, 35), (x, 0), (x, GAME_HEIGHT))
        for y in range(0, GAME_HEIGHT, GRID_SIZE): pg.draw.line(game_surf, (20, 20, 35), (0, y), (GAME_WIDTH, y))

        fx, fy = self.food.pos[0] * GRID_SIZE, self.food.pos[1] * GRID_SIZE
        self.draw_crystal_frog(game_surf, (fx + GRID_SIZE//2, fy + GRID_SIZE//2))

        # HYPER-REALISTIC Smooth Rendering
        # We use sub-stepping between segments to create a solid curved body
        body = self.snake.body
        for i in range(len(body)):
            # Tapering radius
            taper_factor = (len(body) - i) / len(body)
            radius = int(GRID_SIZE//2.2 * (0.6 + 0.6 * taper_factor))
            
            # Color gradient
            factor = i / max(1, len(body) - 1)
            color = tuple(int(SNAKE_START[j] + (SNAKE_END[j] - SNAKE_START[j]) * factor) for j in range(3))
            
            curr_pos = (body[i][0] * GRID_SIZE + GRID_SIZE//2, body[i][1] * GRID_SIZE + GRID_SIZE//2)
            
            # Fill gaps between segments for SMOOTHNESS
            if i < len(body) - 1:
                next_pos = (body[i+1][0] * GRID_SIZE + GRID_SIZE//2, body[i+1][1] * GRID_SIZE + GRID_SIZE//2)
                # Draw 3 intermediate circles to bridge the gap
                for step in range(1, 4):
                    inter_pos = (
                        int(curr_pos[0] + (next_pos[0] - curr_pos[0]) * (step / 4)),
                        int(curr_pos[1] + (next_pos[1] - curr_pos[1]) * (step / 4))
                    )
                    inter_radius = int(radius - (radius - int(GRID_SIZE//2.2 * (0.6 + 0.6 * ((len(body) - (i+1)) / len(body))))) * (step / 4))
                    self.draw_organic_segment(game_surf, inter_pos, color, inter_radius)

            # Draw the main segment
            if i == 0:
                self.draw_organic_segment(game_surf, curr_pos, color, int(GRID_SIZE//1.8), is_head=True)
                # Eyes and Tongue
                dir = self.snake.direction
                eye_dist = 5
                eyes = []
                if dir == UP: eyes = [(-eye_dist, -3), (eye_dist, -3)]
                elif dir == DOWN: eyes = [(-eye_dist, 3), (eye_dist, 3)]
                elif dir == LEFT: eyes = [(-3, -eye_dist), (-3, eye_dist)]
                elif dir == RIGHT: eyes = [(3, -eye_dist), (3, eye_dist)]
                
                for ex, ey in eyes:
                    pg.draw.circle(game_surf, WHITE, (curr_pos[0] + ex, curr_pos[1] + ey), 3)
                    pg.draw.circle(game_surf, (0, 0, 0), (curr_pos[0] + ex, curr_pos[1] + ey), 2)
                
                if (self.frame_count // 10) % 2 == 0:
                    t_color, t_len = (255, 50, 50), 8
                    tip = None
                    if dir == UP: tip = (0, -GRID_SIZE//2 - t_len)
                    elif dir == DOWN: tip = (0, GRID_SIZE//2 + t_len)
                    elif dir == LEFT: tip = (-GRID_SIZE//2 - t_len, 0)
                    elif dir == RIGHT: tip = (GRID_SIZE//2 + t_len, 0)
                    if tip: pg.draw.line(game_surf, t_color, (curr_pos[0], curr_pos[1]), (curr_pos[0]+tip[0], curr_pos[1]+tip[1]), 2)
            else:
                self.draw_organic_segment(game_surf, curr_pos, color, radius)

        self.screen.blit(game_surf, (0, HEADER_HEIGHT))
        self.vfx.draw(self.screen)

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_game()
        self.draw_header()
        self.draw_footer()
        if self.state == STATE_GAMEOVER:
            overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA); overlay.fill((0, 0, 0, 210))
            self.screen.blit(overlay, (0, 0))
            self.screen.blit(self.title_font.render("REBOOT REQUIRED", True, FOOD_COLOR), (WIDTH // 2 - 160, HEIGHT // 2 - 20))
        pg.display.flip()

    def update(self):
        self.frame_count += 1
        if self.state != STATE_PLAYING: 
            self.vfx.update(); return
        self.vfx.update()
        next_pos = None
        if self.auto_mode:
            path = bfs(self.snake.body, self.food.pos)
            if not path: path = get_safe_move(self.snake.body)
            if path: next_pos = path[0]
        head = self.snake.move(next_pos)
        if head == self.food.pos:
            self.eat_snd.play(); self.snake.grow(); self.food.respawn(self.snake.body)
            self.vfx.create_burst((head[0]*GRID_SIZE + GRID_SIZE//2, head[1]*GRID_SIZE + GRID_SIZE//2 + HEADER_HEIGHT), FOOD_COLOR)
        else: self.snake.shrink()
        if not self.snake.alive: self.crash_snd.play(); self.state = STATE_GAMEOVER

    def run(self):
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT: pg.quit(); sys.exit()
                if event.type == pg.MOUSEBUTTONDOWN:
                    mpos = pg.mouse.get_pos()
                    if self.btn_easy.collidepoint(mpos): self.set_difficulty("EASY")
                    elif self.btn_medium.collidepoint(mpos): self.set_difficulty("MEDIUM")
                    elif self.btn_hard.collidepoint(mpos): self.set_difficulty("HARD")
                    elif self.btn_start.collidepoint(mpos): self.toggle_snd.play(); self.reset(); self.state = STATE_PLAYING
                    elif self.btn_pause.collidepoint(mpos):
                        self.state = STATE_PAUSED if self.state == STATE_PLAYING else STATE_PLAYING
                        self.toggle_snd.play()
                    elif self.btn_mode.collidepoint(mpos): self.auto_mode = not self.auto_mode; self.toggle_snd.play()
                    elif self.btn_stop.collidepoint(mpos): self.toggle_snd.play(); pg.quit(); sys.exit()
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_SPACE:
                        if self.state == STATE_GAMEOVER: self.reset(); self.state = STATE_PLAYING
                        else: self.auto_mode = not self.auto_mode; self.toggle_snd.play()
                    if not self.auto_mode and self.state == STATE_PLAYING:
                        if event.key in [pg.K_UP, pg.K_w] and self.snake.direction != DOWN: self.snake.next_direction = UP
                        elif event.key in [pg.K_DOWN, pg.K_s] and self.snake.direction != UP: self.snake.next_direction = DOWN
                        elif event.key in [pg.K_LEFT, pg.K_a] and self.snake.direction != RIGHT: self.snake.next_direction = LEFT
                        elif event.key in [pg.K_RIGHT, pg.K_d] and self.snake.direction != LEFT: self.snake.next_direction = RIGHT
            self.update(); self.draw(); self.clock.tick(self.current_fps)

if __name__ == "__main__":
    game = Game(); game.run()
