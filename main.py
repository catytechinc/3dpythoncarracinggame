import random
import noise
import math
import json
import os
from PIL import Image  # For procedural texture generation
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import basic_lighting_shader

# Leaderboard file path
LEADERBOARD_FILE = "leaderboard.json"

class Car(Entity):
    def __init__(self, position=(0,0,0), color=color.red, is_player=False, texture=None):
        super().__init__()
        self.model = "cube"
        self.scale = (1.5, 1, 3)
        self.position = position
        if texture:
            self.texture = texture
        else:
            self.color = color
        self.collider = "box"
        self.speed = 0
        self.max_speed = 20
        self.rotation_speed = 60
        self.is_player = is_player
        
        if is_player:
            self.shader = basic_lighting_shader
            # Create camera as child of car
            self.camera_pivot = Entity(parent=self, position=(0, 5, -10))
            camera.parent = self.camera_pivot
            camera.position = (0, 0, 0)
            camera.rotation_x = 20
            
    def update(self):
        if self.is_player:
            # Player controls
            if held_keys['w'] or held_keys['arrow_up']:
                self.speed = lerp(self.speed, self.max_speed, time.dt)
            elif held_keys['s'] or held_keys['arrow_down']:
                self.speed = lerp(self.speed, -self.max_speed/2, time.dt)
            else:
                self.speed = lerp(self.speed, 0, time.dt * 3)
                
            if held_keys['a'] or held_keys['arrow_left']:
                self.rotation_y -= self.rotation_speed * time.dt
            if held_keys['d'] or held_keys['arrow_right']:
                self.rotation_y += self.rotation_speed * time.dt
                
            self.position += self.forward * self.speed * time.dt
        else:
            # AI behavior - simple path following
            if self.z < 20:
                self.position += self.forward * self.max_speed * 0.8 * time.dt
                # Random steering
                if random.random() < 0.1:
                    self.rotation_y += random.uniform(-10, 10)
            else:
                self.z = -20

class Leaderboard:
    def __init__(self):
        self.scores = []
        self.load()
        
    def load(self):
        """Load leaderboard from file"""
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE, 'r') as f:
                    self.scores = json.load(f)
            except:
                self.scores = []
        else:
            self.scores = []
            
        # Sort by score descending
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        
    def save(self):
        """Save leaderboard to file"""
        with open(LEADERBOARD_FILE, 'w') as f:
            json.dump(self.scores, f)
            
    def add_score(self, name, level, coins, score):
        """Add new score to leaderboard"""
        self.scores.append({
            'name': name,
            'level': level,
            'coins': coins,
            'score': score
        })
        # Sort and keep top 10
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        self.scores = self.scores[:10]
        self.save()

class CarRacingGame(Entity):
    def __init__(self):
        super().__init__()
        
        # Game state
        self.game_state = "title"  # title, playing, paused
        self.difficulty = "medium"
        self.coins = 0
        self.level = 1
        self.total_coins = 0
        self.score = 0
        
        # Initialize auto-save timer
        self.auto_save_timer = 0
        
        # Setup window
        window.title = "3D Autorennen"
        window.borderless = False
        window.fullscreen = False
        
        # Leaderboard
        self.leaderboard = Leaderboard()
        
        # Initialize textures to None
        self.textures = None
        
        # Setup scene
        self.setup_title_screen()
        
    def generate_ground_texture(self, seed=None):
        """Generate procedural asphalt texture using Pillow"""
        from PIL import Image as PILImage
        size = 512
        img = PILImage.new('RGB', (size, size))
        pixels = img.load()
        
        # Use seed for reproducibility
        if seed is None:
            seed = random.randint(0, 1000000)
        random.seed(seed)
        
        for y in range(size):
            for x in range(size):
                # Generate noise pattern
                n = noise.pnoise2(x/100, y/100, octaves=4, persistence=0.5)
                # Dark gray with noise variation
                gray = 50 + int(n * 30)
                # Set pixel color
                pixels[x, y] = (gray, gray, gray)
        
        # Save texture
        filename = f"assets/ground_texture_{seed}.png"
        img.save(filename)
        return Texture(filename)
    
    def generate_wall_texture(self, seed=None):
        """Generate wall texture with red-white pattern using Pillow"""
        from PIL import Image as PILImage
        size = 256
        img = PILImage.new('RGB', (size, size))
        pixels = img.load()
        
        # Use seed for reproducibility
        if seed is None:
            seed = random.randint(0, 1000000)
        random.seed(seed)
        
        stripe_height = 20
        for y in range(size):
            for x in range(size):
                # Red and white stripes
                if (y // stripe_height) % 2 == 0:
                    pixels[x, y] = (255, 0, 0)  # Red
                else:
                    pixels[x, y] = (255, 255, 255)  # White
        
        # Save texture
        filename = f"assets/wall_texture_{seed}.png"
        img.save(filename)
        return Texture(filename)
    
    def generate_coin_texture(self, seed=None):
        """Generate shiny coin texture using Pillow"""
        from PIL import Image as PILImage
        size = 128
        img = PILImage.new('RGBA', (size, size))
        pixels = img.load()
        center = size // 2
        
        # Use seed for reproducibility
        if seed is None:
            seed = random.randint(0, 1000000)
        random.seed(seed)
        
        for y in range(size):
            for x in range(size):
                dist = math.sqrt((x-center)**2 + (y-center)**2)
                # Create circular coin
                if dist < center:
                    # Gold color with gradient
                    intensity = 200 - int(dist/center * 100)
                    pixels[x, y] = (255, 215, intensity, 255)
                else:
                    pixels[x, y] = (0, 0, 0, 0)  # Transparent
        
        # Save texture
        filename = f"assets/coin_texture_{seed}.png"
        img.save(filename)
        return Texture(filename)
    
    def generate_car_texture(self, color, seed=None):
        """Generate car texture with given color"""
        from PIL import Image as PILImage
        size = 128
        img = PILImage.new('RGBA', (size, size))
        pixels = img.load()
        
        # Use seed for reproducibility
        if seed is None:
            seed = random.randint(0, 1000000)
        random.seed(seed)
        
        # Create car body with gradient
        for y in range(size):
            for x in range(size):
                # Create oval shape
                if abs(x - size//2) < size//3 and abs(y - size//2) < size//4:
                    # Add gradient effect
                    intensity = 150 + int(noise.pnoise2(x/50, y/50) * 50)
                    r = min(255, color[0] + intensity)
                    g = min(255, color[1] + intensity)
                    b = min(255, color[2] + intensity)
                    pixels[x, y] = (r, g, b, 255)
                else:
                    pixels[x, y] = (0, 0, 0, 0)  # Transparent
        
        # Save texture
        filename = f"assets/car_texture_{seed}.png"
        img.save(filename)
        return Texture(filename)
    
    def setup_title_screen(self):
        """Create title screen UI with save/load options"""
        self.title_entity = Entity(parent=camera.ui)
        Text(parent=self.title_entity, text="3D AUTORENNEN", scale=2, y=0.3, origin=(0,0), color=color.gold)
        
        # Difficulty buttons
        self.difficulty_text = Text(parent=self.title_entity, text=f"Schwierigkeit: {self.difficulty}", y=0.1, scale=1.2)
        
        Button(parent=self.title_entity, text="Einfach", y=-0.05, scale=(0.25, 0.08),
               on_click=Func(self.set_difficulty, "easy"))
        Button(parent=self.title_entity, text="Mittel", y=-0.15, scale=(0.25, 0.08),
               on_click=Func(self.set_difficulty, "medium"))
        Button(parent=self.title_entity, text="Schwer", y=-0.25, scale=(0.25, 0.08),
               on_click=Func(self.set_difficulty, "hard"))
        
        # Game buttons
        Button(parent=self.title_entity, text="Neues Spiel", y=-0.4, scale=(0.3, 0.1),
               color=color.green, on_click=Func(self.start_game, False))
        Button(parent=self.title_entity, text="Spiel laden", y=-0.55, scale=(0.3, 0.1),
               color=color.yellow, on_click=Func(self.start_game, True))
        Button(parent=self.title_entity, text="Bestenliste", y=-0.7, scale=(0.3, 0.1),
               color=color.blue, on_click=self.show_leaderboard)
        Button(parent=self.title_entity, text="Beenden", y=-0.85, scale=(0.3, 0.1),
               color=color.red, on_click=application.quit)
        
        # Controls hint
        Text(parent=self.title_entity, text="Steuerung: WASD oder Pfeiltasten | M: Karte | ESC: Menü", y=-0.95, scale=0.7, color=color.gray)
    
    def show_leaderboard(self):
        """Display leaderboard screen"""
        destroy(self.title_entity)
        self.leaderboard_screen = Entity(parent=camera.ui)
        
        Text(parent=self.leaderboard_screen, text="BESTENLISTE", scale=2, y=0.4, origin=(0,0), color=color.gold)
        
        # Display top 10 scores
        y_pos = 0.3
        for i, score in enumerate(self.leaderboard.scores[:10]):
            Text(parent=self.leaderboard_screen,
                 text=f"{i+1}. {score['name']}: Level {score['level']}, Münzen {score['coins']}, Punkte {score['score']}",
                 y=y_pos, scale=1.0)
            y_pos -= 0.07
        
        # Back button
        Button(parent=self.leaderboard_screen, text="Zurück", y=-0.4, scale=(0.3, 0.1),
               on_click=self.back_to_title)
    
    def back_to_title(self):
        """Return to title screen from leaderboard"""
        destroy(self.leaderboard_screen)
        self.setup_title_screen()
    
    def set_difficulty(self, difficulty):
        """Set game difficulty"""
        self.difficulty = difficulty
        self.difficulty_text.text = f"Schwierigkeit: {self.difficulty}"
        
        # Adjust difficulty parameters
        if difficulty == "easy":
            self.ai_speed_factor = 0.7
        elif difficulty == "medium":
            self.ai_speed_factor = 0.9
        else:  # hard
            self.ai_speed_factor = 1.2
        
        # Initialize terrain bounds
        self.min_generated_z = -50
        self.max_generated_z = 50
        
        # Initialize auto-save timer
        self.auto_save_timer = 0
    
    def start_game(self, load_save=False):
        """Initialize game scene, optionally loading from save"""
        destroy(self.title_entity)
        self.game_state = "playing"
        self.score = 0
        
        if not load_save:
            # Generate new world with random seed
            self.world_seed = random.randint(0, 1000000)
            random.seed(self.world_seed)
            
            # Generate textures
            self.textures = {
                "ground": self.generate_ground_texture(self.world_seed),
                "wall": self.generate_wall_texture(self.world_seed),
                "coin": self.generate_coin_texture(self.world_seed)
            }
            
            # Initialize coin_entities before creating track
            self.coin_entities = []
            
            # Create track
            self.create_track()
            
            # Create AI cars
            self.ai_cars = []
            self.spawn_ai_cars()
            
            # Create player car
            self.player = Car(
                position=(0, 0, 0),
                is_player=True,
                texture=self.generate_car_texture((255, 0, 0), self.world_seed)
            )
        else:
            # Load saved game
            self.load_game()
        
        # Create dashboard
        self.create_dashboard()
        
        # Map system
        self.map_visible = False
        self.minimap = None
        self.minimap_camera = None
        
        # Reset camera
        if self.player:
            self.player.camera_pivot.position = (0, 5, -10)
            camera.rotation_x = 20
        
    def create_track(self):
        """Generate procedural track with textures"""
        # Ground with generated texture
        Entity(model="plane", scale=100, texture=self.textures["ground"], texture_scale=(10,10))
        
        # Create lists to store walls and obstacles
        self.walls = []
        self.obstacles = []
        
        # Initialize the generated z boundaries
        self.min_generated_z = -50
        self.max_generated_z = 50
        
        # Generate the initial track segment
        self.generate_track_segment(self.min_generated_z, self.max_generated_z)
        
    def generate_track_segment(self, start_z, end_z):
        """Generate a segment of track between start_z and end_z"""
        try:
            # Generate walls
            step = 2
            z = start_z
            while z <= end_z:
                # Only generate walls if not already existing at this position
                if not any(abs(wall.z - z) < 0.1 for wall in self.walls):
                    wall_left = Entity(model="cube", position=(15,0.5,z), scale=(0.5,1,2),
                                      texture=self.textures["wall"])
                    wall_left.collider = "box"
                    self.walls.append(wall_left)
                    
                    wall_right = Entity(model="cube", position=(-15,0.5,z), scale=(0.5,1,2),
                                       texture=self.textures["wall"])
                    wall_right.collider = "box"
                    self.walls.append(wall_right)
                z += step
        except Exception as e:
            print(f"Error generating track segment: {e}")
        
        # Generate obstacles
        num_obstacles = max(5, int((end_z - start_z) / 10))
        for i in range(num_obstacles):
            obstacle = Entity(model="cube",
                             position=(random.uniform(-12,12), 1, random.uniform(start_z, end_z)),
                             scale=(2,2,2), texture=self.textures["wall"])
            obstacle.collider = "box"
            self.obstacles.append(obstacle)
        
        # Generate coins in this segment
        num_coins = max(10, int((end_z - start_z) / 5))
        for i in range(num_coins):
            coin = Entity(model="sphere",
                         position=(random.uniform(-12,12), 1, random.uniform(start_z, end_z)),
                         scale=0.8, texture=self.textures["coin"])
            coin.collider = "sphere"
            self.coin_entities.append(coin)
            self.total_coins += 1
    
    def spawn_coins(self):
        """Generate coins around the track (now handled in generate_track_segment)"""
        pass
    
    def spawn_ai_cars(self):
        """Create AI opponent cars with generated textures"""
        colors = [(0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 165, 0)]  # RGB values
        for i in range(4):
            car = Car(
                position=(random.uniform(-10,10), 0, random.uniform(-20,-40)),
                is_player=False,
                texture=self.generate_car_texture(colors[i % len(colors)], self.world_seed + i)
            )
            car.max_speed *= self.ai_speed_factor
            self.ai_cars.append(car)
    
    def create_dashboard(self):
        """Create in-game UI dashboard"""
        self.dashboard = Entity(parent=camera.ui)
        
        # Speedometer
        self.speed_text = Text(parent=self.dashboard, text="Geschw.: 0 km/h",
                              position=(-0.8, 0.45), scale=1.2)
        
        # Coin counter
        self.coin_text = Text(parent=self.dashboard, text=f"Münzen: {self.coins}/{self.total_coins}",
                             position=(-0.8, 0.4), scale=1.2)
        
        # Level display
        self.level_text = Text(parent=self.dashboard, text=f"Level: {self.level}",
                              position=(-0.8, 0.35), scale=1.2)
        
        # Score display
        self.score_text = Text(parent=self.dashboard, text=f"Punkte: {self.score}",
                              position=(-0.8, 0.3), scale=1.2)
        
        # Minimap toggle hint
        self.map_hint = Text(parent=self.dashboard, text="[M] Karte",
                            position=(0.75, -0.45), scale=0.8, color=color.gray)
    
    def toggle_map(self):
        """Toggle minimap visibility"""
        self.map_visible = not self.map_visible
        if self.map_visible:
            self.create_minimap()
            self.map_hint.text = "[M] Karte schließen"
        else:
            destroy(self.minimap)
            destroy(self.minimap_camera)
            self.map_hint.text = "[M] Karte"
    
    def create_minimap(self):
        """Create minimap display"""
        self.minimap = Entity(parent=camera.ui, model="quad", scale=(0.4, 0.4),
                             position=(0.7, 0.4), texture=self.textures["ground"])
        
        # Create a camera for the minimap
        self.minimap_camera = EditorCamera(parent=self.minimap, enabled=False)
        self.minimap_camera.position = (0, 50, 0)
        self.minimap_camera.rotation_x = 90
        
        # Add player, AI, and obstacle indicators
        self.player_indicator = Entity(parent=self.minimap, model="circle",
                                      scale=0.05, color=color.red,
                                      position=(0,0,0))
        
        self.ai_indicators = []
        for car in self.ai_cars:
            indicator = Entity(parent=self.minimap, model="circle",
                              scale=0.04, color=car.color,
                              position=(car.x/50, car.z/50, 0))
            self.ai_indicators.append(indicator)
            
        self.obstacle_indicators = []
        for obstacle in self.obstacles:
            indicator = Entity(parent=self.minimap, model="circle",
                              scale=0.03, color=color.gray,
                              position=(obstacle.x/50, obstacle.z/50, 0))
            self.obstacle_indicators.append(indicator)
    
    def update_minimap(self):
        """Update minimap indicators"""
        if self.map_visible:
            self.player_indicator.position = (self.player.x/50, self.player.z/50, 0)
            
            for i, car in enumerate(self.ai_cars):
                if i < len(self.ai_indicators):
                    self.ai_indicators[i].position = (car.x/50, car.z/50, 0)
    
    def collect_coin(self, coin):
        """Handle coin collection"""
        destroy(coin)
        self.coins += 1
        self.score += 100 * self.level
        self.coin_text.text = f"Münzen: {self.coins}/{self.total_coins}"
        self.score_text.text = f"Punkte: {self.score}"
        
        # Check if all coins collected
        if self.coins >= self.total_coins:
            self.level_up()
    
    def level_up(self):
        """Advance to next level"""
        try:
            self.level += 1
            self.score += 1000 * self.level
            self.level_text.text = f"Level: {self.level}"
            self.score_text.text = f"Punkte: {self.score}"
            
            # Reset coin count for new level (coins remain in world)
            self.coins = 0
            if hasattr(self, 'coin_text'):
                self.coin_text.text = f"Münzen: {self.coins}/{self.total_coins}"
            
            # Make AI faster
            for car in self.ai_cars:
                car.max_speed *= 1.1
        except Exception as e:
            print(f"Fehler beim Level-Aufstieg: {e}")
        finally:
            # Ensure coin text is updated even if error occurs
            if hasattr(self, 'coin_text'):
                self.coin_text.text = f"Münzen: {self.coins}/{self.total_coins}"
    
    def input(self, key):
        """Handle keyboard input"""
        if key == "m":
            self.toggle_map()
        elif key == "escape":
            if self.game_state == "playing":
                self.toggle_pause()
            elif self.game_state == "paused":
                self.save_and_quit()
    
    def save_game(self):
        """Save current game state including generated terrain bounds"""
        save_data = {
            'world_seed': self.world_seed,
            'min_generated_z': self.min_generated_z,
            'max_generated_z': self.max_generated_z,
            'player': {
                'position': tuple(self.player.position),
                'rotation': tuple(self.player.rotation),
                'speed': self.player.speed,
                'max_speed': self.player.max_speed,
                'rotation_speed': self.player.rotation_speed
            },
            'coins': [coin.position for coin in self.coin_entities if coin.enabled],
            'ai_cars': [{
                'position': tuple(car.position),
                'rotation': tuple(car.rotation),
                'speed': car.speed,
                'max_speed': car.max_speed
            } for car in self.ai_cars],
            'game_state': {
                'score': self.score,
                'level': self.level,
                'coins': self.coins,
                'total_coins': self.total_coins,
                'difficulty': self.difficulty
            }
        }
        
        with open("savegame.json", "w") as f:
            json.dump(save_data, f)
            
        print("Spiel gespeichert!")
    
    def load_game(self):
        """Load game state from save file including terrain bounds"""
        if not os.path.exists("savegame.json"):
            print("Kein Speicherstand gefunden!")
            return
            
        with open("savegame.json", "r") as f:
            save_data = json.load(f)
            
        # Clear existing game objects safely
        if hasattr(self, 'coin_entities'):
            for coin in self.coin_entities:
                if coin: destroy(coin)
        if hasattr(self, 'ai_cars'):
            for car in self.ai_cars:
                if car: destroy(car)
        if hasattr(self, 'walls'):
            for wall in self.walls:
                if wall: destroy(wall)
        if hasattr(self, 'obstacles'):
            for obstacle in self.obstacles:
                if obstacle: destroy(obstacle)
        if hasattr(self, 'player') and self.player:
            destroy(self.player)
        
        # Set world seed
        self.world_seed = save_data['world_seed']
        random.seed(self.world_seed)
        
        # Recreate textures
        self.textures = {
            "ground": self.generate_ground_texture(self.world_seed),
            "wall": self.generate_wall_texture(self.world_seed),
            "coin": self.generate_coin_texture(self.world_seed)
        }
        
        # Set terrain bounds
        self.min_generated_z = save_data['min_generated_z']
        self.max_generated_z = save_data['max_generated_z']
        
        # Recreate track for entire generated area
        self.create_track()
        
        # Recreate coins
        self.coin_entities = []
        self.total_coins = 0
        for coin_pos in save_data['coins']:
            coin = Entity(model="sphere", position=coin_pos,
                         scale=0.8, texture=self.textures["coin"])
            coin.collider = "sphere"
            self.coin_entities.append(coin)
            self.total_coins += 1
        
        # Recreate AI cars
        self.ai_cars = []
        colors = [(0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 165, 0)]
        for i, car_data in enumerate(save_data['ai_cars']):
            car = Car(
                position=car_data['position'],
                is_player=False,
                texture=self.generate_car_texture(colors[i % len(colors)], self.world_seed + i)
            )
            car.max_speed = car_data['max_speed']
            car.speed = car_data['speed']
            car.rotation = car_data['rotation']
            self.ai_cars.append(car)
        
        # Create player car
        player_data = save_data['player']
        self.player = Car(
            position=player_data['position'],
            is_player=True,
            texture=self.generate_car_texture((255, 0, 0), self.world_seed)
        )
        self.player.speed = player_data['speed']
        self.player.max_speed = player_data['max_speed']
        self.player.rotation_speed = player_data['rotation_speed']
        self.player.rotation = player_data['rotation']
        
        # Restore game state
        game_state = save_data['game_state']
        self.score = game_state['score']
        self.level = game_state['level']
        self.coins = game_state['coins']
        self.difficulty = game_state['difficulty']
    
    def save_and_quit(self):
        """Save score and return to title screen"""
        self.save_game()
        self.leaderboard.add_score("Player", self.level, self.coins, self.score)
        self.back_to_title()
    
    def toggle_pause(self):
        """Pause/unpause game"""
        self.game_state = "paused" if self.game_state == "playing" else "playing"
        mouse.locked = self.game_state == "playing"
        
        # Show/hide pause menu
        if hasattr(self, "pause_menu"):
            destroy(self.pause_menu)
        if self.game_state == "paused":
            self.pause_menu = Entity(parent=camera.ui)
            Text(parent=self.pause_menu, text="PAUSE", scale=2, y=0.2)
            Button(parent=self.pause_menu, text="Weiter", y=-0.1,
                  on_click=self.toggle_pause)
            Button(parent=self.pause_menu, text="Spiel speichern", y=-0.25,
                  on_click=self.save_game)
            Button(parent=self.pause_menu, text="Spiel laden", y=-0.4,
                  on_click=self.load_game)
            Button(parent=self.pause_menu, text="Beenden", y=-0.55,
                  on_click=self.save_and_quit)
    
    def update(self):
        """Game loop"""
        try:
            if self.game_state != "playing":
                return
            
            # Update speed display
            speed_kmh = abs(int(self.player.speed * 3.6))
            self.speed_text.text = f"Geschw.: {speed_kmh} km/h"
            
            # Update minimap
            self.update_minimap()
            
            # Check coin collisions
            for coin in self.coin_entities:
                if hasattr(coin, 'enabled') and coin.enabled and coin.intersects(self.player).hit:
                    self.collect_coin(coin)
            
            # Check wall and obstacle collisions
            for entity in self.walls + self.obstacles:
                if self.player.intersects(entity).hit:
                    # Bounce back on collision
                    self.player.position -= self.player.forward * self.player.speed * time.dt * 2
                    self.player.speed *= -0.5
                    self.score = max(0, self.score - 10)
            
            # Check AI car collisions
            for car in self.ai_cars:
                if car.intersects(self.player).hit:
                    # Slow down on collision
                    self.player.speed *= 0.5
                    self.score = max(0, self.score - 50)
                    
            # Infinite terrain generation and auto-saving
            if abs(self.player.z) > 150:
                self.generate_more_terrain()
                
                # Auto-save every 60 seconds (safer implementation)
                if hasattr(self, 'auto_save_timer'):
                    self.auto_save_timer += time.dt
                    if self.auto_save_timer >= 60:
                        self.save_game()
                        print("Spiel automatisch gespeichert!")
                        self.auto_save_timer = 0
                else:
                    self.auto_save_timer = 0
        except Exception as e:
            print(f"Fehler im Spielupdate: {e}")

    def generate_more_terrain(self):
        """Generate new terrain segments as player moves"""
        # Extend terrain in both directions
        if self.player.z > self.max_generated_z - 50:
            new_min = self.max_generated_z
            self.max_generated_z += 50
            self.generate_track_segment(new_min, self.max_generated_z)
            
        if self.player.z < self.min_generated_z + 50:
            new_max = self.min_generated_z
            self.min_generated_z -= 50
            self.generate_track_segment(self.min_generated_z, new_max)
            
        # Reset player position to center to avoid floating point precision issues
        if abs(self.player.z) > 1000:
            offset = self.player.z
            self.player.z = 0
            # Move all track elements back by offset
            for wall in self.walls:
                wall.z -= offset
            for obstacle in self.obstacles:
                obstacle.z -= offset
            for coin in self.coin_entities:
                coin.z -= offset
            for car in self.ai_cars:
                car.z -= offset

# Start the game
if __name__ == "__main__":
    app = Ursina()
    game = CarRacingGame()
    app.run()