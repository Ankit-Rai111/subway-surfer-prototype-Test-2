import tkinter as tk
import random
import math
import time
import os

# --- Config ---
WIDTH, HEIGHT = 800, 500
FPS = 60
FOV = 400
CAMERA_Y = 120
GROUND_Y = 300

PLAYER_X = 0
PLAYER_Z = 0
LANE_WIDTH = 1.2

OBSTACLE_SPEED_START = 6.0
OBSTACLE_SPEED_MAX = 14.0
SPEED_INCREMENT = 0.0015

OBSTACLE_SPAWN_Z_START = 2000
OBSTACLE_SPAWN_INTERVAL_Z_BASE = 350

MOVE_SPEED = 0.12
JUMP_SPEED = 9.0
GRAVITY = 0.45
DUCK_FACTOR = 0.5

ANIM_FPS = 10

# Obstacle types
TYPE_BLOCK_GROUND = "block_ground"
TYPE_BLOCK_FLYING = "block_flying"
TYPE_TRAIN = "train"
TYPE_BARRIER = "barrier"

class SubwayGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Subway Surfer - Arrow keys / Numpad / Touch")
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#87CEEB")
        self.canvas.pack()

        # Player
        self.player_x = 0.0
        self.player_y = 0.0
        self.player_vy = 0.0
        self.is_ducking = False

        # World
        self.obstacles = []
        self.coins = []
        self.next_spawn_z = OBSTACLE_SPAWN_Z_START
        self.next_coin_spawn_z = OBSTACLE_SPAWN_Z_START + 150

        self.score = 0
        self.coin_count = 0
        self.distance = 0
        self.game_over = False
        self.speed = OBSTACLE_SPEED_START

        # High score
        self.high_score = self.load_high_score()

        # Controls
        self.keys_pressed = set()
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)

        self.create_touch_buttons()

        # Animation
        self.anim_counter = 0
        self.anim_frame = 0

        self.last_time = None
        self.root.after(16, self.loop)

    def create_touch_buttons(self):
        btn_size = 50
        margin = 10

        self.btn_left = self.canvas.create_rectangle(
            margin, HEIGHT - margin - btn_size,
            margin + btn_size, HEIGHT - margin,
            fill="#444444", outline="white"
        )
        self.btn_left_text = self.canvas.create_text(
            margin + btn_size/2, HEIGHT - margin - btn_size/2,
            text="◀", fill="white", font="Arial 18"
        )

        self.btn_right = self.canvas.create_rectangle(
            WIDTH - margin - btn_size, HEIGHT - margin - btn_size,
            WIDTH - margin, HEIGHT - margin,
            fill="#444444", outline="white"
        )
        self.btn_right_text = self.canvas.create_text(
            WIDTH - margin - btn_size/2, HEIGHT - margin - btn_size/2,
            text="▶", fill="white", font="Arial 18"
        )

        self.btn_down = self.canvas.create_rectangle(
            WIDTH/2 - btn_size/2, HEIGHT - margin - btn_size,
            WIDTH/2 + btn_size/2, HEIGHT - margin,
            fill="#444444", outline="white"
        )
        self.btn_down_text = self.canvas.create_text(
            WIDTH/2, HEIGHT - margin - btn_size/2,
            text="▼", fill="white", font="Arial 18"
        )

        self.btn_up = self.canvas.create_rectangle(
            WIDTH/2 - btn_size/2, HEIGHT - margin - 2*btn_size - 5,
            WIDTH/2 + btn_size/2, HEIGHT - margin - btn_size - 5,
            fill="#444444", outline="white"
        )
        self.btn_up_text = self.canvas.create_text(
            WIDTH/2, HEIGHT - margin - 1.5*btn_size - 5,
            text="▲", fill="white", font="Arial 18"
        )

        for tag, key in [
            ("btn_left", "Left"),
            ("btn_right", "Right"),
            ("btn_up", "Up"),
            ("btn_down", "Down"),
            ("btn_left_text", "Left"),
            ("btn_right_text", "Right"),
            ("btn_up_text", "Up"),
            ("btn_down_text", "Down"),
        ]:
            self.canvas.tag_bind(tag, "<ButtonPress-1>", lambda e, k=key: self.simulate_key(k, True))
            self.canvas.tag_bind(tag, "<ButtonRelease-1>", lambda e, k=key: self.simulate_key(k, False))

    def simulate_key(self, key, pressed):
        if key == "Left":
            code = "Left"
        elif key == "Right":
            code = "Right"
        elif key == "Up":
            code = "Up"
        elif key == "Down":
            code = "Down"
        else:
            return
        if pressed:
            self.keys_pressed.add(code)
        else:
            self.keys_pressed.discard(code)

    def on_key_down(self, event):
        key = event.keysym
        if key in ("Left", "Right", "Up", "Down"):
            self.keys_pressed.add(key)
        if key in ("4", "KP_4"):
            self.keys_pressed.add("Left")
        if key in ("6", "KP_6"):
            self.keys_pressed.add("Right")
        if key in ("8", "KP_8"):
            self.keys_pressed.add("Up")
        if key in ("2", "KP_2"):
            self.keys_pressed.add("Down")

        if self.game_over and key == "space":
            self.restart()

    def on_key_up(self, event):
        key = event.keysym
        if key in ("Left", "Right", "Up", "Down"):
            self.keys_pressed.discard(key)
        if key in ("4", "KP_4"):
            self.keys_pressed.discard("Left")
        if key in ("6", "KP_6"):
            self.keys_pressed.discard("Right")
        if key in ("8", "KP_8"):
            self.keys_pressed.discard("Up")
        if key in ("2", "KP_2"):
            self.keys_pressed.discard("Down")

    def restart(self):
        self.player_x = 0.0
        self.player_y = 0.0
        self.player_vy = 0.0
        self.is_ducking = False
        self.obstacles = []
        self.coins = []
        self.next_spawn_z = OBSTACLE_SPAWN_Z_START
        self.next_coin_spawn_z = OBSTACLE_SPAWN_Z_START + 150
        self.score = 0
        self.coin_count = 0
        self.distance = 0
        self.game_over = False
        self.speed = OBSTACLE_SPEED_START
        self.keys_pressed.clear()
        self.anim_counter = 0
        self.anim_frame = 0

    def load_high_score(self):
        path = self.get_highscore_path()
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    val = int(f.read().strip())
                    return val
        except Exception:
            pass
        return 0

    def save_high_score(self, value):
        path = self.get_highscore_path()
        try:
            with open(path, "w") as f:
                f.write(str(value))
        except Exception:
            pass

    def get_highscore_path(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "highscore.txt")

    def update(self, dt):
        if self.game_over:
            return

        if self.speed < OBSTACLE_SPEED_MAX:
            self.speed += SPEED_INCREMENT

        # Horizontal
        if "Left" in self.keys_pressed:
            self.player_x -= MOVE_SPEED
        if "Right" in self.keys_pressed:
            self.player_x += MOVE_SPEED

        self.player_x = max(-2.0, min(2.0, self.player_x))

        # Jump / gravity
        if "Up" in self.keys_pressed and self.player_y <= 0.1:
            self.player_vy = JUMP_SPEED

        # Duck
        if "Down" in self.keys_pressed:
            self.is_ducking = True
        else:
            self.is_ducking = False

        self.player_vy -= GRAVITY
        self.player_y += self.player_vy
        if self.player_y < 0:
            self.player_y = 0
            self.player_vy = 0

        # Move world
        self.distance += self.speed
        self.score = int(self.distance / 10)

        # Spawn obstacles
        if self.next_spawn_z > 0:
            self.next_spawn_z -= self.speed
        if self.next_spawn_z <= 0:
            self.spawn_obstacle()
            interval = OBSTACLE_SPAWN_INTERVAL_Z_BASE * (OBSTACLE_SPEED_START / self.speed)
            self.next_spawn_z = max(180, interval)

        # Spawn coins
        if self.next_coin_spawn_z > 0:
            self.next_coin_spawn_z -= self.speed
        if self.next_coin_spawn_z <= 0:
            self.spawn_coin()
            self.next_coin_spawn_z = OBSTACLE_SPAWN_INTERVAL_Z_BASE * 0.7

        # Update obstacles
        for obs in self.obstacles:
            obs["z"] -= self.speed
        self.obstacles = [o for o in self.obstacles if o["z"] > -200]

        # Update coins
        for c in self.coins:
            c["z"] -= self.speed
        self.coins = [c for c in self.coins if c["z"] > -200]

        # Collision
        if self.check_obstacle_collision():
            self.game_over = True
            current_total = self.score + self.coin_count * 5
            if current_total > self.high_score:
                self.high_score = current_total
                self.save_high_score(self.high_score)

        # Coin collection
        self.check_coin_collection()

        # Animation
        self.anim_counter += 1
        if self.anim_counter >= ANIM_FPS:
            self.anim_counter = 0
            self.anim_frame = (self.anim_frame + 1) % 2

    def spawn_obstacle(self):
        lane = random.choice([-1, 0, 1])
        x = lane * LANE_WIDTH

        choice = random.random()
        if choice < 0.35:
            obs = self.make_block_ground(x)
        elif choice < 0.55:
            obs = self.make_block_flying(x)
        elif choice < 0.80:
            obs = self.make_train(x)
        else:
            obs = self.make_barrier(x)

        self.obstacles.append(obs)

    def make_block_ground(self, x):
        y = 0
        h = random.uniform(40, 80)
        w = random.uniform(40, 70)
        d = random.uniform(40, 70)
        color = random.choice(["#cc0000", "#aa00aa", "#0066cc"])
        return {
            "type": TYPE_BLOCK_GROUND,
            "x": x, "y": y, "z": OBSTACLE_SPAWN_Z_START,
            "w": w, "h": h, "d": d, "color": color
        }

    def make_block_flying(self, x):
        y = random.uniform(50, 100)
        h = random.uniform(30, 60)
        w = random.uniform(40, 70)
        d = random.uniform(40, 70)
        color = random.choice(["#cc0000", "#aa00aa", "#0066cc"])
        return {
            "type": TYPE_BLOCK_FLYING,
            "x": x, "y": y, "z": OBSTACLE_SPAWN_Z_START,
            "w": w, "h": h, "d": d, "color": color
        }

    def make_train(self, x):
        y = 0
        h = random.uniform(120, 160)
        w = random.uniform(90, 120)
        d = random.uniform(180, 260)
        color = "#555555"
        return {
            "type": TYPE_TRAIN,
            "x": x, "y": y, "z": OBSTACLE_SPAWN_Z_START,
            "w": w, "h": h, "d": d, "color": color
        }

    def make_barrier(self, x):
        y = 0
        h = random.uniform(25, 40)
        w = random.uniform(70, 100)
        d = random.uniform(20, 35)
        color = "#884400"
        return {
            "type": TYPE_BARRIER,
            "x": x, "y": y, "z": OBSTACLE_SPAWN_Z_START,
            "w": w, "h": h, "d": d, "color": color
        }

    def spawn_coin(self):
        lane = random.choice([-1, 0, 1])
        x = lane * LANE_WIDTH

        if random.random() < 0.6:
            y = random.uniform(10, 40)
        else:
            y = random.uniform(60, 100)

        r = random.uniform(12, 18)

        self.coins.append({
            "x": x, "y": y, "z": OBSTACLE_SPAWN_Z_START, "r": r
        })

    def check_obstacle_collision(self):
        px = self.player_x
        py = self.player_y
        pw = 0.4
        ph_base = 1.2
        ph = ph_base * (DUCK_FACTOR if self.is_ducking else 1.0)

        for o in self.obstacles:
            ox = o["x"]
            oy = o["y"]
            oz = o["z"]
            ow = o["w"] / 100.0
            oh = o["h"] / 100.0
            od = o["d"] / 100.0

            pz_min = -0.5
            pz_max = 0.5
            oz_min = (oz - od/2) / 100.0
            oz_max = (oz + od/2) / 100.0

            if not (px + pw/2 < ox - ow/2 or px - pw/2 > ox + ow/2):
                if not (py < oy or py + ph < oy - oh):
                    if not (pz_max < oz_min or pz_min > oz_max):
                        if o["type"] == TYPE_BARRIER:
                            if py > (oy - oh) + 0.2:
                                continue
                        return True
        return False

    def check_coin_collection(self):
        px = self.player_x
        py = self.player_y
        pr = 0.25

        for c in self.coins[:]:
            cx = c["x"]
            cy = c["y"]
            cz = c["z"] / 100.0

            if abs(cz) < 0.6:
                dx = px - cx
                dy = (py - 0.6) - (cy / 100.0)
                if dx*dx + dy*dy < pr*pr:
                    self.coins.remove(c)
                    self.coin_count += 1

    def project(self, x, y, z):
        cam_z = -FOV
        rel_z = z - cam_z
        if rel_z <= 0:
            return None
        scale = FOV / rel_z
        sx = WIDTH/2 + x * scale * 100
        sy = GROUND_Y - (y - CAMERA_Y) * scale
        return sx, sy, scale

    def draw(self):
        self.canvas.delete("all")

        # Sky / ground
        self.canvas.create_rectangle(0, 0, WIDTH, GROUND_Y, fill="#87CEEB", outline="")
        self.canvas.create_rectangle(0, GROUND_Y, WIDTH, HEIGHT, fill="#6b6b6b", outline="")

        # Obstacles
        sorted_obs = sorted(self.obstacles, key=lambda o: o["z"], reverse=True)
        for o in sorted_obs:
            self.draw_obstacle(o)

        # Coins
        sorted_coins = sorted(self.coins, key=lambda c: c["z"], reverse=True)
        for c in sorted_coins:
            self.draw_coin(c)

        # Player
        self.draw_player()

        # Score, coins, high score
        current_total = self.score + self.coin_count * 5
        self.canvas.create_text(
            10, 10, anchor="nw",
            text=f"Score: {self.score}   Coins: {self.coin_count}   Total: {current_total}   High: {self.high_score}",
            fill="black", font="Consolas 16"
        )

        if self.game_over:
            # Fixed: use solid color instead of rgba
            self.canvas.create_rectangle(
                WIDTH/2 - 200, HEIGHT/2 - 80,
                WIDTH/2 + 200, HEIGHT/2 + 80,
                fill="#222222", outline="white"
            )
            self.canvas.create_text(
                WIDTH/2, HEIGHT/2 - 25,
                text="Game Over",
                fill="white", font="Consolas 24 bold"
            )
            self.canvas.create_text(
                WIDTH/2, HEIGHT/2 + 5,
                text=f"Total: {current_total}   High Score: {self.high_score}",
                fill="white", font="Consolas 16"
            )
            self.canvas.create_text(
                WIDTH/2, HEIGHT/2 + 35,
                text="Press Space or tap to restart",
                fill="white", font="Consolas 14"
            )

    def draw_obstacle(self, o):
        x, y, z = o["x"], o["y"], o["z"]
        w, h, d = o["w"], o["h"], o["d"]

        p1 = self.project(x - w/200, y - h/100, z - d/2)
        p2 = self.project(x + w/200, y - h/100, z - d/2)
        p3 = self.project(x + w/200, y, z - d/2)
        p4 = self.project(x - w/200, y, z - d/2)

        q1 = self.project(x - w/200, y - h/100, z + d/2)
        q2 = self.project(x + w/200, y - h/100, z + d/2)
        q3 = self.project(x + w/200, y, z + d/2)
        q4 = self.project(x - w/200, y, z + d/2)

        if any(p is None for p in [p1,p2,p3,p4,q1,q2,q3,q4]):
            return

        color = o["color"]

        # Front
        self.canvas.create_polygon(
            p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1],
            fill=color, outline="black"
        )
        # Top
        self.canvas.create_polygon(
            p1[0], p1[1], p2[0], p2[1], q2[0], q2[1], q1[0], q1[1],
            fill=self.lighten(color, 0.2), outline="black"
        )
        # Side
        self.canvas.create_polygon(
            p2[0], p2[1], p3[0], p3[1], q3[0], q3[1], q2[0], q2[1],
            fill=self.darken(color, 0.2), outline="black"
        )

        if o["type"] == TYPE_TRAIN:
            cx, cy, _ = self.project(x, y - h/200, z)
            if cx is not None:
                self.canvas.create_text(
                    cx, cy,
                    text="TRAIN",
                    fill="white", font="Consolas 10 bold"
                )

    def draw_coin(self, c):
        x, y, z = c["x"], c["y"], c["z"]
        r = c["r"]

        p_center = self.project(x, y - r/100, z)
        if p_center is None:
            return
        cx, cy, scale = p_center
        screen_r = r * scale

        self.canvas.create_oval(
            cx - screen_r, cy - screen_r,
            cx + screen_r, cy + screen_r,
            fill="#ffd700", outline="#b8860b", width=2
        )
        self.canvas.create_oval(
            cx - screen_r*0.4, cy - screen_r*0.4,
            cx - screen_r*0.1, cy - screen_r*0.1,
            fill="#fffacd", outline=""
        )

    def draw_player(self):
        x = self.player_x
        y = self.player_y
        ph_base = 1.2
        ph = ph_base * (DUCK_FACTOR if self.is_ducking else 1.0)

        head_r = 0.15
        body_w = 0.25
        body_h = ph * 0.45
        limb_w = 0.08
        limb_h = ph * 0.35

        head_y = y - ph + head_r
        body_top = y - ph
        body_bottom = body_top + body_h

        if self.is_ducking:
            leg_offset = 0.0
        else:
            leg_offset = 0.12 if self.anim_frame == 0 else -0.12

        def draw_box(xc, yc, w, h, color):
            z = 0
            p1 = self.project(xc - w/2, yc, z - 0.05)
            p2 = self.project(xc + w/2, yc, z - 0.05)
            p3 = self.project(xc + w/2, yc - h, z - 0.05)
            p4 = self.project(xc - w/2, yc - h, z - 0.05)
            if any(p is None for p in [p1,p2,p3,p4]):
                return
            self.canvas.create_polygon(
                p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1],
                fill=color, outline="black"
            )

        # Legs
        leg_y = y
        left_leg_x = x - 0.08 + leg_offset
        right_leg_x = x + 0.08 - leg_offset
        draw_box(left_leg_x, leg_y, limb_w, limb_h, "#333333")
        draw_box(right_leg_x, leg_y, limb_w, limb_h, "#333333")

        # Body
        draw_box(x, body_top + body_h/2, body_w, body_h, "#2266cc")

        # Arms
        if not self.is_ducking:
            arm_y = body_top + body_h * 0.2
            arm_offset = 0.12 if self.anim_frame == 0 else -0.12
            left_arm_x = x - 0.18 - arm_offset
            right_arm_x = x + 0.18 + arm_offset
            draw_box(left_arm_x, arm_y, limb_w, limb_h*0.9, "#2266cc")
            draw_box(right_arm_x, arm_y, limb_w, limb_h*0.9, "#2266cc")

        # Head
        draw_box(x, head_y + head_r, head_r*2, head_r*2, "#ffccaa")

    def lighten(self, hex_color, factor):
        return self.adjust_color(hex_color, factor)

    def darken(self, hex_color, factor):
        return self.adjust_color(hex_color, -factor)

    def adjust_color(self, hex_color, factor):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        def clamp(v):
            return max(0, min(255, int(v)))

        r = clamp(r + 255 * factor)
        g = clamp(g + 255 * factor)
        b = clamp(b + 255 * factor)

        return f"#{r:02x}{g:02x}{b:02x}"

    def loop(self):
        now = time.time()
        if self.last_time is None:
            dt = 1.0 / FPS
        else:
            dt = min(0.05, now - self.last_time)
        self.last_time = now

        self.update(dt)
        self.draw()

        self.root.after(16, self.loop)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    game = SubwayGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()