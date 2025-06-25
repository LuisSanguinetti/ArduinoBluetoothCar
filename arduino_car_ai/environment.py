import numpy as np
import pygame
import math
import random

class CarSimulatorEnv:
    """Simulated environment for the Arduino car"""
    
    def __init__(self, render=False):
        self.render_mode = render
        self.width = 800
        self.height = 600
        self.car_size = 30
        self.sensor_range = 200
        self.max_speed = 5
        self.min_speed = 1
        
        # Initialize pygame components
        self.screen = None
        self.clock = None
        self.font = None
        
        # Initialize pygame if rendering
        if self.render_mode:
            self.init_pygame()
        
        # Obstacles
        self.obstacles = []
        self.generate_obstacles()
        
        self.reset()
    
    def init_pygame(self):
        """Initialize pygame components"""
        if not pygame.get_init():
            pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Arduino Car Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
    def generate_obstacles(self):
        """Generate random obstacles in the environment"""
        self.obstacles = []
        # Border walls
        self.obstacles.extend([
            pygame.Rect(0, 0, self.width, 10),
            pygame.Rect(0, 0, 10, self.height),
            pygame.Rect(0, self.height-10, self.width, 10),
            pygame.Rect(self.width-10, 0, 10, self.height)
        ])
        
        # Random obstacles
        for _ in range(8):
            x = random.randint(100, self.width-100)
            y = random.randint(100, self.height-100)
            w = random.randint(40, 100)
            h = random.randint(40, 100)
            self.obstacles.append(pygame.Rect(x, y, w, h))
    
    def reset(self):
        """Reset the environment"""
        # Car state
        self.car_x = self.width // 2
        self.car_y = self.height // 2
        self.car_angle = random.uniform(0, 2 * math.pi)
        self.car_speed = 3  # Speed level 1-5
        self.car_velocity = 0  # Actual velocity
        
        # Movement tracking
        self.steps = 0
        self.total_distance = 0
        self.last_position = (self.car_x, self.car_y)
        self.stationary_steps = 0
        
        return self.get_state()
    
    def get_distances(self):
        """Get distances in three directions like the Arduino"""
        distances = []
        # Left (-60°), Center (0°), Right (+60°)
        for angle_offset in [-math.pi/3, 0, math.pi/3]:
            angle = self.car_angle + angle_offset
            distance = self.cast_ray(angle)
            distances.append(min(distance, 200) / 200.0)  # Normalize to 0-1
        return distances
    
    def cast_ray(self, angle):
        """Cast a ray and return distance to nearest obstacle"""
        for dist in range(1, self.sensor_range):
            x = self.car_x + dist * math.cos(angle)
            y = self.car_y + dist * math.sin(angle)
            
            # Check boundaries
            if x < 0 or x > self.width or y < 0 or y > self.height:
                return dist
                
            # Check obstacles
            point = pygame.Rect(x-1, y-1, 2, 2)
            for obstacle in self.obstacles:
                if obstacle.colliderect(point):
                    return dist
                    
        return self.sensor_range
    
    def get_state(self):
        """Get current state (3 distances + speed)"""
        distances = self.get_distances()
        return np.array(distances + [self.car_speed / 5.0])
    
    def step(self, action):
        """Execute action and return new state, reward, done"""
        self.steps += 1
        old_x, old_y = self.car_x, self.car_y
        
        # Check if we need to initialize pygame (when switching render modes)
        if self.render_mode and self.screen is None:
            self.init_pygame()
        
        # Map action to command
        # Actions: 0=Forward, 1=Left, 2=Right, 3=Backward, 4-8=Speed 1-5
        if action == 0:  # Forward
            self.car_velocity = 2 * self.car_speed
        elif action == 1:  # Rotate Left
            self.car_angle -= 0.1
            self.car_velocity = 0.5 * self.car_speed
        elif action == 2:  # Rotate Right  
            self.car_angle += 0.1
            self.car_velocity = 0.5 * self.car_speed
        # elif action == 3:  # Backward changed to otherr numbers so that backwards stops used
        #    self.car_velocity = -1.5 * self.car_speed
        elif action >= 3 and action <= 7:  # Speed change
            self.car_speed = action - 2
            self.car_velocity = 1 * self.car_speed
        
        # Update position
        self.car_x += self.car_velocity * math.cos(self.car_angle)
        self.car_y += self.car_velocity * math.sin(self.car_angle)
        
        # Check collision
        collision = self.check_collision()
        if collision:
            self.car_x, self.car_y = old_x, old_y
        
        # Calculate reward
        distance_moved = math.sqrt((self.car_x - old_x)**2 + (self.car_y - old_y)**2)
        self.total_distance += distance_moved
        
        # Check if stationary
        if distance_moved < 0.5:
            self.stationary_steps += 1
        else:
            self.stationary_steps = 0
        
        # Reward calculation
        reward = 0
        
        # Positive reward for movement
        reward += distance_moved * 0.1
        
        # Negative reward for being too close to walls
        min_distance = min(self.get_distances())
        if min_distance < 0.2:
            reward -= (0.2 - min_distance) * 5
        
        # Negative reward for collision
        if collision:
            reward -= 10
        
        # Negative reward for being stationary
        if self.stationary_steps > 10:
            reward -= 1
        
        # Bonus for maintaining good speed
        if self.car_speed >= 3:
            reward += 0.1
        
        # Episode ends if collision or too many steps
        done = collision or self.steps > 1000 or self.stationary_steps > 50
        
        if self.render_mode:
            self.render()
        
        return self.get_state(), reward, done, {}
    
    def check_collision(self):
        """Check if car collides with obstacles"""
        car_rect = pygame.Rect(
            self.car_x - self.car_size//2,
            self.car_y - self.car_size//2,
            self.car_size,
            self.car_size
        )
        
        # Check boundaries
        if (self.car_x < self.car_size//2 or 
            self.car_x > self.width - self.car_size//2 or
            self.car_y < self.car_size//2 or 
            self.car_y > self.height - self.car_size//2):
            return True
        
        # Check obstacles
        for obstacle in self.obstacles:
            if car_rect.colliderect(obstacle):
                return True
                
        return False
    
    def render(self):
        """Render the environment"""
        if not self.render_mode or self.screen is None:
            return
            
        self.screen.fill((240, 240, 240))
        
        # Draw obstacles
        for obstacle in self.obstacles:
            pygame.draw.rect(self.screen, (100, 100, 100), obstacle)
        
        # Draw sensor rays
        for angle_offset, color in [(-math.pi/3, (255, 0, 0)), 
                                   (0, (0, 255, 0)), 
                                   (math.pi/3, (0, 0, 255))]:
            angle = self.car_angle + angle_offset
            dist = self.cast_ray(angle) 
            end_x = self.car_x + dist * math.cos(angle)
            end_y = self.car_y + dist * math.sin(angle)
            pygame.draw.line(self.screen, color, 
                           (self.car_x, self.car_y), 
                           (end_x, end_y), 2)
        
        # Draw car
        pygame.draw.circle(self.screen, (50, 50, 200), 
                         (int(self.car_x), int(self.car_y)), 
                         self.car_size//2)
        
        # Draw direction indicator
        end_x = self.car_x + self.car_size * math.cos(self.car_angle)
        end_y = self.car_y + self.car_size * math.sin(self.car_angle)
        pygame.draw.line(self.screen, (255, 255, 255),
                       (self.car_x, self.car_y),
                       (end_x, end_y), 3)
        
        # Draw info
        info_text = f"Speed: {self.car_speed} | Steps: {self.steps}"
        text = self.font.render(info_text, True, (0, 0, 0))
        self.screen.blit(text, (10, 10))
        
        pygame.display.flip()
        self.clock.tick(30)