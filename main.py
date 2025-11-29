import pygame
import random
import math
import sys
import os
import asyncio

# ---- Settings & Polish ----
WIDTH, HEIGHT = 800, 600
FPS = 60

# ---- Palette (Sky Force Style) ----
NEON_BLUE = (50, 200, 255)
NEON_RED = (255, 50, 80)
NEON_GREEN = (50, 255, 100)
NEON_ORANGE = (255, 180, 50)
NEON_PURPLE = (180, 50, 255)  # For Ace Enemies
NEON_CYAN = (0, 255, 255)     # For Shield
NEON_YELLOW = (255, 255, 0)   # For Speed
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---- Asset System ----
class AssetManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}

    def load_image(self, name, size=None):
        if name in self.images: return self.images[name]
        try:
            path = os.path.join(os.path.dirname(__file__), name)
            img = pygame.image.load(path).convert_alpha()
            if size: img = pygame.transform.scale(img, size)
            self.images[name] = img
            return img
        except: return None

    def load_sound(self, name):
        if name in self.sounds: return self.sounds[name]
        try:
            path = os.path.join(os.path.dirname(__file__), name)
            snd = pygame.mixer.Sound(path)
            self.sounds[name] = snd
            return snd
        except: return None

    def play(self, name, vol=0.5):
        s = self.load_sound(name)
        if s: 
            s.set_volume(vol)
            s.play()

assets = AssetManager()

# ---- VFX ----
class TrailParticle:
    def __init__(self, x, y, color=NEON_BLUE):
        self.x = x
        self.y = y
        self.size = random.randint(4, 8)
        self.life = 20
        self.vel_y = random.uniform(2, 4)
        self.vel_x = random.uniform(-1, 1)
        self.color = color

    def update(self):
        self.y += self.vel_y
        self.x += self.vel_x
        self.life -= 1
        self.size -= 0.2

    def draw(self, surface, ox, oy):
        if self.life > 0:
            alpha = int((self.life / 20) * 100)
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
            surface.blit(s, (self.x + ox - self.size, self.y + oy - self.size))

class Explosion:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.life = 15
        self.radius = 5

    def update(self):
        self.life -= 1
        self.radius += 2

    def draw(self, surface, ox, oy):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x + ox), int(self.y + oy)), int(self.radius), width=3)
            pygame.draw.circle(surface, WHITE, (int(self.x + ox), int(self.y + oy)), int(self.radius/2))

class ScreenShake:
    def __init__(self):
        self.timer = 0
        self.intensity = 0
    def trigger(self, amount, time):
        self.intensity = amount
        self.timer = time
    def get_offset(self):
        if self.timer > 0:
            self.timer -= 1
            return random.randint(-self.intensity, self.intensity), random.randint(-self.intensity, self.intensity)
        return 0, 0

# ---- Game Entities ----
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction=None, is_enemy=False):
        super().__init__()
        self.is_enemy = is_enemy
        self.rect = pygame.Rect(x-3, y, 6, 20)
        self.speed = 12 if not is_enemy else 7
        self.color = NEON_RED if is_enemy else NEON_BLUE
        # If direction is provided (Vector2), use it. Otherwise go straight.
        self.direction = direction if direction else pygame.Vector2(0, 1 if is_enemy else -1)

    def update(self):
        self.rect.x += self.direction.x * self.speed
        self.rect.y += self.direction.y * self.speed

    def draw(self, surface, ox, oy):
        start = (self.rect.centerx + ox, self.rect.top + oy)
        end = (self.rect.centerx + ox, self.rect.bottom + oy)
        pygame.draw.line(surface, self.color, start, end, 5)
        pygame.draw.line(surface, WHITE, start, end, 2)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, w, h, difficulty=1.0):
        super().__init__()
        self.image = assets.load_image("enemy_plane.png", (50, 50))
        self.rect = pygame.Rect(random.randint(50, w-50), -60, 50, 50)
        
        # Determine Enemy Type based on randomness and difficulty
        roll = random.random()
        if roll < 0.2 and difficulty > 1.2:
            self.type = "KAMIKAZE" # Fast, rams player
            self.hp = 20 * difficulty
            self.speed = 4 * difficulty
            self.color_tint = NEON_RED
        elif roll < 0.4 and difficulty > 1.5:
            self.type = "ACE" # Aimed shots
            self.hp = 60 * difficulty
            self.speed = 2 * difficulty
            self.color_tint = NEON_PURPLE
        else:
            self.type = "STANDARD"
            self.hp = 30 * difficulty
            self.speed = 3 * difficulty
            self.color_tint = WHITE

        self.max_hp = self.hp
        self.start_x = self.rect.x
        self.t = random.uniform(0, 360) 
        
    def update(self, bullets, player_rect):
        # AI Behavior
        if self.type == "STANDARD":
            self.rect.y += self.speed
            self.t += 0.05
            self.rect.x = self.start_x + math.sin(self.t) * 50
            # Shoot down
            if random.random() < 0.01:
                bullets.append(Bullet(self.rect.centerx, self.rect.bottom, is_enemy=True))

        elif self.type == "KAMIKAZE":
            # Move towards player aggressively
            dx = player_rect.centerx - self.rect.centerx
            dy = player_rect.centery - self.rect.centery
            angle = math.atan2(dy, dx)
            self.rect.x += math.cos(angle) * self.speed
            self.rect.y += math.sin(angle) * self.speed

        elif self.type == "ACE":
            self.rect.y += self.speed
            # Shoot aimed bullets
            if random.random() < 0.03:
                # Calculate vector to player
                vec = pygame.Vector2(player_rect.centerx - self.rect.centerx, player_rect.centery - self.rect.centery)
                if vec.length() > 0: vec = vec.normalize()
                bullets.append(Bullet(self.rect.centerx, self.rect.bottom, direction=vec, is_enemy=True))

    def draw(self, surface, ox, oy):
        x, y = self.rect.x + ox, self.rect.y + oy
        if self.image:
            # Simple tinting by drawing a colored rect with multiply blend mode could go here
            # But for simplicity, we just draw the image
            surface.blit(self.image, (x, y))
            # Draw an indicator for special enemies
            if self.type != "STANDARD":
                pygame.draw.circle(surface, self.color_tint, (int(x+25), int(y+25)), 10, 2)
        else:
            pygame.draw.rect(surface, self.color_tint, (x, y, 50, 50))
            
        pct = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surface, self.color_tint, (x, y-5, 50*pct, 3))

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, p_type):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.type = p_type
        self.pulse = 0
        
    def update(self):
        self.rect.y += 2
        self.pulse += 0.2
        
    def draw(self, surface, ox, oy):
        size_off = math.sin(self.pulse) * 3
        r = pygame.Rect(self.rect.x + ox - size_off, self.rect.y + oy - size_off, 25 + size_off*2, 25 + size_off*2)
        
        # Color Coding
        if self.type == "HP": color = NEON_GREEN
        elif self.type == "TRIPLE": color = NEON_ORANGE
        elif self.type == "SHIELD": color = NEON_CYAN
        elif self.type == "SPEED": color = NEON_YELLOW
        elif self.type == "BOMB": color = NEON_RED
        else: color = WHITE

        pygame.draw.rect(surface, color, r, border_radius=4)
        pygame.draw.rect(surface, WHITE, r, 2, border_radius=4)
        
        # Simple Text Icon
        # (Ideally use an icon image, but shapes work for code-only)

class Player:
    def __init__(self):
        self.image = assets.load_image("plane.png", (64, 74))
        self.rect = pygame.Rect(WIDTH//2, HEIGHT-100, 60, 70)
        self.hp = 100
        self.max_hp = 100
        self.ammo = 50
        self.max_ammo = 50
        self.score = 0
        self.bombs = 1
        
        self.reloading = False
        self.reload_timer = 0
        
        # Buffs
        self.triple_shot = 0
        self.shield_timer = 0
        self.speed_timer = 0
        
    def move(self, keys):
        # Base Speed
        speed = 12 if self.speed_timer > 0 else 7
        
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1
        
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
            
        self.rect.x += dx * speed
        self.rect.y += dy * speed
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

    def update(self):
        # Timers
        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0: 
                self.reloading = False
                self.ammo = self.max_ammo
        if self.triple_shot > 0: self.triple_shot -= 1
        if self.shield_timer > 0: self.shield_timer -= 1
        if self.speed_timer > 0: self.speed_timer -= 1

    def draw(self, surface, ox, oy):
        if self.image:
            surface.blit(self.image, (self.rect.x + ox, self.rect.y + oy))
        else:
            pygame.draw.polygon(surface, NEON_BLUE, [
                (self.rect.centerx+ox, self.rect.top+oy),
                (self.rect.left+ox, self.rect.bottom+oy),
                (self.rect.right+ox, self.rect.bottom+oy)
            ])

        # Draw Shield Visual
        if self.shield_timer > 0:
            pygame.draw.circle(surface, NEON_CYAN, (self.rect.centerx + ox, self.rect.centery + oy), 45, 2)

        # Tactical Ammo Bar
        bar_w = 60
        bar_h = 4
        bar_x = self.rect.x + ox
        bar_y = self.rect.bottom + oy + 10
        pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
        ammo_pct = self.ammo / self.max_ammo
        col = NEON_BLUE if not self.reloading else NEON_RED
        if self.reloading: ammo_pct = 1.0 - (self.reload_timer / 100)
        pygame.draw.rect(surface, col, (bar_x, bar_y, bar_w * ammo_pct, bar_h))

# ---- Main Engine ----
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sky Force: WASM")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 16, bold=True)
        self.big_font = pygame.font.SysFont("arial", 40, bold=True)
        
        self.bg_img = assets.load_image("background_night.png", (WIDTH, HEIGHT))
        self.cloud_img = assets.load_image("cloud.png", (200, 100))
        self.city_img = assets.load_image("city.png", (WIDTH, 300))
        
        self.reset()
        
    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.explosions = []
        self.powerups = []
        self.shake = ScreenShake()
        self.city_scroll = 0
        self.cloud_scroll = 0
        self.game_over = False
        self.difficulty = 1.0

    def draw_transparent_rect(self, x, y, w, h, color, alpha):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((*color, alpha))
        self.screen.blit(s, (x, y))

    def update(self):
        if self.game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]: self.reset()
            return

        # ---- Difficulty Scaling ----
        # Difficulty increases by 0.1 every 500 points
        self.difficulty = 1.0 + (self.player.score / 500)

        keys = pygame.key.get_pressed()
        self.player.move(keys)
        self.player.update()
        
        # Engine Trails (Yellow if speed boosted)
        trail_col = NEON_YELLOW if self.player.speed_timer > 0 else NEON_BLUE
        self.particles.append(TrailParticle(self.player.rect.centerx - 10, self.player.rect.bottom - 10, trail_col))
        self.particles.append(TrailParticle(self.player.rect.centerx + 10, self.player.rect.bottom - 10, trail_col))

        # Shooting
        if keys[pygame.K_SPACE] and not self.player.reloading:
            if self.player.ammo > 0:
                if random.random() < 0.2: 
                    assets.play("shoot.wav", 0.2)
                    self.bullets.append(Bullet(self.player.rect.left + 10, self.player.rect.centery))
                    self.bullets.append(Bullet(self.player.rect.right - 10, self.player.rect.centery))
                    self.player.ammo -= 1
                    
                    if self.player.triple_shot > 0:
                        self.bullets.append(Bullet(self.player.rect.centerx, self.player.rect.top - 10))
                        
                    if self.player.ammo <= 0:
                        self.player.reloading = True
                        self.player.reload_timer = 100
        
        # Bomb Usage
        if keys[pygame.K_b] and self.player.bombs > 0:
            self.player.bombs -= 1
            self.shake.trigger(20, 20)
            assets.play("bomb.wav")
            for e in self.enemies:
                self.explosions.append(Explosion(e.rect.centerx, e.rect.centery, NEON_ORANGE))
                self.player.score += 50
            self.enemies = []
            self.bullets = [b for b in self.bullets if not b.is_enemy] # Clear enemy bullets

        # Spawning (Faster based on difficulty)
        spawn_chance = 0.02 * self.difficulty
        if random.random() < spawn_chance:
            self.enemies.append(Enemy(WIDTH, HEIGHT, self.difficulty))

        # Update Lists
        for p in self.particles[:]: 
            p.update()
            if p.life <= 0: self.particles.remove(p)
            
        for ex in self.explosions[:]:
            ex.update()
            if ex.life <= 0: self.explosions.remove(ex)
            
        for b in self.bullets[:]:
            b.update()
            
            # 1. Enemy Bullet Hits Player
            if b.is_enemy:
                if b.rect.colliderect(self.player.rect):
                    if self.player.shield_timer <= 0:
                        self.player.hp -= 10
                        self.shake.trigger(10, 10)
                        self.explosions.append(Explosion(b.rect.centerx, b.rect.centery, NEON_RED))
                        if self.player.hp <= 0: self.game_over = True
                    else:
                        # Shield blocked it
                        self.explosions.append(Explosion(b.rect.centerx, b.rect.centery, NEON_CYAN))
                    
                    self.bullets.remove(b)

            # 2. Player Bullet Hits Enemy
            else:
                for e in self.enemies:
                    if b.rect.colliderect(e.rect):
                        e.hp -= 10
                        self.explosions.append(Explosion(b.rect.centerx, b.rect.centery, NEON_ORANGE))
                        if b in self.bullets: self.bullets.remove(b)
                        
                        if e.hp <= 0:
                            if e in self.enemies: self.enemies.remove(e)
                            self.player.score += 100 * self.difficulty
                            assets.play("explode.wav")
                            self.shake.trigger(5, 5)
                            
                            # Drop Loot (Variety)
                            if random.random() < 0.25:
                                opts = ["HP", "TRIPLE", "SHIELD", "SPEED", "BOMB"]
                                # Weights: HP(30), TRIPLE(25), SHIELD(15), SPEED(20), BOMB(10)
                                ptype = random.choices(opts, weights=[30, 25, 15, 20, 10], k=1)[0]
                                self.powerups.append(PowerUp(e.rect.centerx, e.rect.centery, ptype))
                        break
            
            if b.rect.y < -50 or b.rect.y > HEIGHT + 50 or b.rect.x < -50 or b.rect.x > WIDTH + 50: 
                if b in self.bullets: self.bullets.remove(b)

        # Update Enemies (Pass player rect for aiming)
        for e in self.enemies[:]: 
            e.update(self.bullets, self.player.rect)
            
            # Collision: Player hits Enemy Body
            if e.rect.colliderect(self.player.rect):
                if self.player.shield_timer <= 0:
                    self.player.hp -= 30
                    self.shake.trigger(20, 10)
                    e.hp = 0 # Kamikaze successful
                else:
                    e.hp = 0 # Shield kills enemy
                
                if e.hp <= 0 and e in self.enemies:
                     self.enemies.remove(e)
                     self.explosions.append(Explosion(e.rect.centerx, e.rect.centery, NEON_ORANGE))
                
                if self.player.hp <= 0: self.game_over = True

            if e.rect.y > HEIGHT + 100: self.enemies.remove(e)
        
        # Powerup Collection
        for pu in self.powerups[:]:
            pu.update()
            if pu.rect.colliderect(self.player.rect):
                assets.play("powerup.wav")
                if pu.type == "HP": self.player.hp = min(100, self.player.hp + 30)
                elif pu.type == "TRIPLE": self.player.triple_shot = 300
                elif pu.type == "SHIELD": self.player.shield_timer = 300 # 5 Seconds
                elif pu.type == "SPEED": self.player.speed_timer = 300
                elif pu.type == "BOMB": self.player.bombs += 1
                
                self.powerups.remove(pu)
            elif pu.rect.y > HEIGHT:
                self.powerups.remove(pu)

    def draw(self):
        ox, oy = self.shake.get_offset()
        
        # Background
        if self.bg_img: self.screen.blit(self.bg_img, (ox, oy))
        else: self.screen.fill((20, 20, 40))
        
        # Clouds
        self.cloud_scroll -= 0.5
        if self.cloud_img:
            for i in range(4):
                x_pos = (self.cloud_scroll + i*300) % (WIDTH + 200) - 200
                self.screen.blit(self.cloud_img, (x_pos + ox, 100 + i*50 + oy))

        # City
        self.city_scroll -= 2 + (self.difficulty * 0.5) # Scroll faster on higher diff
        if self.city_img:
            cw = self.city_img.get_width()
            cx = self.city_scroll % cw
            self.screen.blit(self.city_img, (cx - cw + ox, HEIGHT - 300 + oy))
            self.screen.blit(self.city_img, (cx + ox, HEIGHT - 300 + oy))

        # Game Layer
        for p in self.particles: p.draw(self.screen, ox, oy)
        self.player.draw(self.screen, ox, oy)
        for e in self.enemies: e.draw(self.screen, ox, oy)
        for b in self.bullets: b.draw(self.screen, ox, oy)
        for ex in self.explosions: ex.draw(self.screen, ox, oy)
        for pu in self.powerups: pu.draw(self.screen, ox, oy)

        # UI
        # Health
        self.draw_transparent_rect(10, 10, 220, 60, BLACK, 120)
        pygame.draw.rect(self.screen, NEON_RED, (15, 25, 200 * (self.player.hp/100), 10), border_radius=5)
        self.screen.blit(self.font.render("SHIELD INTEGRITY", True, WHITE), (15, 10))
        
        # Score & Difficulty
        score_txt = self.big_font.render(f"{int(self.player.score):06d}", True, NEON_BLUE)
        self.screen.blit(score_txt, (WIDTH - score_txt.get_width() - 20, 10))
        
        diff_txt = self.font.render(f"THREAT LEVEL: {self.difficulty:.1f}", True, NEON_RED)
        self.screen.blit(diff_txt, (WIDTH - score_txt.get_width() - 20, 50))
        
        # Bombs
        bomb_txt = self.font.render(f"BOMBS: {self.player.bombs} [B]", True, NEON_ORANGE)
        self.screen.blit(bomb_txt, (15, 45))

        # Active Powerup Text
        if self.player.shield_timer > 0:
            self.screen.blit(self.font.render("SHIELD ACTIVE", True, NEON_CYAN), (WIDTH//2 - 50, HEIGHT - 80))
        if self.player.speed_timer > 0:
             self.screen.blit(self.font.render("SPEED BOOST", True, NEON_YELLOW), (WIDTH//2 - 50, HEIGHT - 60))

        if self.game_over:
            self.draw_transparent_rect(0, HEIGHT//2 - 60, WIDTH, 120, BLACK, 200)
            go_txt = self.big_font.render("MISSION FAILED", True, NEON_RED)
            re_txt = self.font.render("PRESS R TO RESTART", True, WHITE)
            self.screen.blit(go_txt, (WIDTH//2 - go_txt.get_width()//2, HEIGHT//2 - 20))
            self.screen.blit(re_txt, (WIDTH//2 - re_txt.get_width()//2, HEIGHT//2 + 30))

        pygame.display.flip()

async def main():
    pygame.init()
    pygame.mixer.init()
    game = Game()
    while True:
        game.update()
        game.draw()
        game.clock.tick(FPS)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())