import pygame
import math
import time

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("2D Car Driving Game")

# Colors
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
TRAFFIC_GREEN = (0, 128, 0)

# Road and lane settings
ROAD_WIDTH = 400
LANE_WIDTH = ROAD_WIDTH // 4
ROAD_LENGTH = 30000  # 30 km in meters
PIXELS_PER_METER = SCREEN_HEIGHT / 75  # Screen shows 75 meters for 4x faster scenery

# Vertical road division (10 parts)
PART_HEIGHT = SCREEN_HEIGHT / 10
MAX_PART = 7  # Car can move up to the 7th part from the bottom (y = PART_HEIGHT * 3)

# Car settings
CAR_WIDTH = 50
CAR_HEIGHT = 80
car_x = SCREEN_WIDTH // 2  # Fixed start position (middle of screen)
car_y = SCREEN_HEIGHT - CAR_HEIGHT - 20  # Fixed start position (bottom)
car_speed = 0  # Current speed in km/h
horizontal_speed = 0  # Pixels per second for left/right movement
HORIZONTAL_SPEED_MAX = LANE_WIDTH / 0.3  # Speed to cross one lane in 0.3 seconds
is_accelerating = False
is_decelerating = False
is_decelerating_smoothly = False
deceleration_start_time = 0
deceleration_initial_speed = 0
deceleration_initial_y = 0
DECELERATION_DURATION = 3.0  # 3 seconds for smooth deceleration
last_input_time = 0  # For debouncing input
INPUT_DEBOUNCE = 0.1  # 100ms debounce to prevent jitter

# Speed levels (km/h) and transition times (seconds)
SPEED_LEVELS = [(0, 8, 0, 1), (8, 20, 1, 1.85), (20, 32, 1.85, 3.0), (32, 60, 3.0, 3.5)]
current_level = 0
acceleration_start_time = 0

# Scenery settings
SCENERY_WIDTH = (SCREEN_WIDTH - ROAD_WIDTH) // 2
scenery_objects = [
    {"type": "palm", "x": 50, "y": 100, "height": 100},
    {"type": "building", "x": SCREEN_WIDTH - 100, "y": 200, "height": 150},
    {"type": "mall", "x": 50, "y": 400, "height": 80},
]

# Traffic lights settings
TRAFFIC_LIGHT_RADIUS = 15
TRAFFIC_LIGHT_SPACING = 10
TRAFFIC_LIGHT_Y = SCREEN_HEIGHT - 40
traffic_light_state = "red"  # Initial state
traffic_light_timer = time.time()
TRAFFIC_LIGHT_TIMES = {"red": 5, "green": 5, "yellow": 2}  # Seconds for each light

# Load Tesla Model S Plaid image
try:
    car_image = pygame.image.load("tesla.png")
    car_image = pygame.transform.scale(car_image, (CAR_WIDTH, CAR_HEIGHT))
except pygame.error:
    print("Error: tesla_model_s_plaid.png not found. Using fallback blue rectangle.")
    car_image = pygame.Surface((CAR_WIDTH, CAR_HEIGHT))
    car_image.fill((0, 0, 255))  # Blue rectangle as fallback

# Clock for frame rate
clock = pygame.time.Clock()

# Speed function: Linear interpolation between speed levels for acceleration
def get_speed(t):
    for i, (min_speed, max_speed, start_time, end_time) in enumerate(SPEED_LEVELS):
        if start_time <= t <= end_time:
            if i == 0 and t < start_time:
                return 0
            fraction = (t - start_time) / (end_time - start_time)
            return min_speed + (max_speed - min_speed) * fraction
    return 60  # Max speed after final level

# Convert km/h to pixels/second
def kmh_to_pixels_per_second(kmh):
    meters_per_second = kmh * 1000 / 3600
    return meters_per_second * PIXELS_PER_METER

# Map speed to vertical position (bottom to 7th part)
def speed_to_y_position(speed):
    max_speed = 60  # Maximum speed in km/h
    max_y = PART_HEIGHT * 3  # 7th part from bottom (0-based index: 10 - 7 = 3)
    min_y = SCREEN_HEIGHT - CAR_HEIGHT - 20  # Bottom position
    if speed == 0:
        return min_y
    fraction = speed / max_speed
    return min_y - (min_y - max_y) * fraction

# Main game loop
running = True
while running:
    current_time = time.time()
    # Event handling with debounce
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and current_time - last_input_time > INPUT_DEBOUNCE:
            if event.key == pygame.K_UP:
                is_accelerating = True
                is_decelerating = False
                is_decelerating_smoothly = False
                acceleration_start_time = time.time() - sum(level[3] - level[2] for level in SPEED_LEVELS[:current_level])
                last_input_time = current_time
            elif event.key == pygame.K_DOWN:
                is_decelerating = True
                is_accelerating = False
                is_decelerating_smoothly = False
                last_input_time = current_time
            elif event.key == pygame.K_LEFT:
                horizontal_speed = -HORIZONTAL_SPEED_MAX
                last_input_time = current_time
            elif event.key == pygame.K_RIGHT:
                horizontal_speed = HORIZONTAL_SPEED_MAX
                last_input_time = current_time
        elif event.type == pygame.KEYUP and current_time - last_input_time > INPUT_DEBOUNCE:
            if event.key == pygame.K_UP:
                is_accelerating = False
                if not is_decelerating:
                    is_decelerating_smoothly = True
                    deceleration_start_time = time.time()
                    deceleration_initial_speed = car_speed
                    deceleration_initial_y = car_y
                last_input_time = current_time
            elif event.key == pygame.K_DOWN:
                is_decelerating = False
                last_input_time = current_time
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                horizontal_speed = 0
                last_input_time = current_time

    # Update traffic lights
    elapsed_time = current_time - traffic_light_timer
    if traffic_light_state == "red" and elapsed_time >= TRAFFIC_LIGHT_TIMES["red"]:
        traffic_light_state = "green"
        traffic_light_timer = current_time
    elif traffic_light_state == "green" and elapsed_time >= TRAFFIC_LIGHT_TIMES["green"]:
        traffic_light_state = "yellow"
        traffic_light_timer = current_time
    elif traffic_light_state == "yellow" and elapsed_time >= TRAFFIC_LIGHT_TIMES["yellow"]:
        traffic_light_state = "red"
        traffic_light_timer = current_time

    # Update speed and position
    if is_accelerating:
        elapsed_time = current_time - acceleration_start_time
        car_speed = get_speed(elapsed_time)
        car_y = speed_to_y_position(car_speed)
        for i, (min_speed, max_speed, start_time, end_time) in enumerate(SPEED_LEVELS):
            if elapsed_time < end_time:
                current_level = i
                break
        else:
            current_level = len(SPEED_LEVELS) - 1
    elif is_decelerating:
        current_level = max(0, current_level - 1)
        min_speed, max_speed, _, _ = SPEED_LEVELS[current_level]
        car_speed = max_speed
        car_y = speed_to_y_position(car_speed)
        acceleration_start_time = current_time - sum(level[3] - level[2] for level in SPEED_LEVELS[:current_level])
    elif is_decelerating_smoothly:
        elapsed_time = current_time - deceleration_start_time
        if elapsed_time < DECELERATION_DURATION:
            fraction = elapsed_time / DECELERATION_DURATION
            car_speed = deceleration_initial_speed * (1 - fraction)
            car_y = deceleration_initial_y + (SCREEN_HEIGHT - CAR_HEIGHT - 20 - deceleration_initial_y) * fraction
        else:
            car_speed = 0
            car_y = SCREEN_HEIGHT - CAR_HEIGHT - 20  # Reset to fixed bottom position
            is_decelerating_smoothly = False
            current_level = 0
            car_x = SCREEN_WIDTH // 2  # Reset to fixed center position
    else:
        min_speed, max_speed, _, _ = SPEED_LEVELS[current_level]
        car_speed = max_speed
        car_y = speed_to_y_position(car_speed)

    # Update car x position
    car_x += horizontal_speed / 60  # Update x position (60 FPS)
    # Keep car within road boundaries
    car_x = max(SCREEN_WIDTH // 2 - ROAD_WIDTH // 2 + CAR_WIDTH // 2, 
                min(car_x, SCREEN_WIDTH // 2 + ROAD_WIDTH // 2 - CAR_WIDTH // 2))

    # Update scenery position
    scenery_speed = kmh_to_pixels_per_second(car_speed)
    for obj in scenery_objects:
        obj["y"] += scenery_speed / 60  # Move scenery at car's speed (60 FPS)
        if obj["y"] > SCREEN_HEIGHT + obj["height"]:
            obj["y"] -= SCREEN_HEIGHT + obj["height"] + SCREEN_HEIGHT  # Loop back to top

    # Draw everything
    screen.fill(GREEN)  # Background (grass)
    
    # Draw road
    pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH // 2 - ROAD_WIDTH // 2, 0, ROAD_WIDTH, SCREEN_HEIGHT))
    
    # Draw lane lines
    for i in range(1, 4):
        pygame.draw.line(screen, WHITE, (SCREEN_WIDTH // 2 - ROAD_WIDTH // 2 + i * LANE_WIDTH, 0),
                         (SCREEN_WIDTH // 2 - ROAD_WIDTH // 2 + i * LANE_WIDTH, SCREEN_HEIGHT), 2)
    
    # Draw road part lines (for visualization)
    for i in range(1, 10):
        pygame.draw.line(screen, YELLOW, (SCREEN_WIDTH // 2 - ROAD_WIDTH // 2, i * PART_HEIGHT),
                         (SCREEN_WIDTH // 2 + ROAD_WIDTH // 2, i * PART_HEIGHT), 1)
    
    # Draw traffic lights
    traffic_light_x = SCREEN_WIDTH // 2 - (3 * TRAFFIC_LIGHT_RADIUS * 2 + 2 * TRAFFIC_LIGHT_SPACING) // 2
    pygame.draw.circle(screen, RED if traffic_light_state == "red" else (100, 0, 0), 
                       (traffic_light_x + TRAFFIC_LIGHT_RADIUS, TRAFFIC_LIGHT_Y), TRAFFIC_LIGHT_RADIUS)
    pygame.draw.circle(screen, YELLOW if traffic_light_state == "yellow" else (100, 100, 0), 
                       (traffic_light_x + 2 * TRAFFIC_LIGHT_RADIUS + TRAFFIC_LIGHT_SPACING + TRAFFIC_LIGHT_RADIUS, TRAFFIC_LIGHT_Y), TRAFFIC_LIGHT_RADIUS)
    pygame.draw.circle(screen, TRAFFIC_GREEN if traffic_light_state == "green" else (0, 50, 0), 
                       (traffic_light_x + 4 * TRAFFIC_LIGHT_RADIUS + 2 * TRAFFIC_LIGHT_SPACING + TRAFFIC_LIGHT_RADIUS, TRAFFIC_LIGHT_Y), TRAFFIC_LIGHT_RADIUS)

    # Draw scenery
    for obj in scenery_objects:
        if obj["type"] == "palm":
            pygame.draw.rect(screen, (139, 69, 19), (obj["x"], obj["y"], 10, obj["height"]))  # Trunk
            pygame.draw.circle(screen, (0, 128, 0), (obj["x"] + 5, obj["y"]), 20)  # Leaves
        elif obj["type"] == "building":
            pygame.draw.rect(screen, (200, 200, 200), (obj["x"], obj["y"], 50, obj["height"]))
        elif obj["type"] == "mall":
            pygame.draw.rect(screen, (255, 165, 0), (obj["x"], obj["y"], 80, obj["height"]))

    # Draw car
    screen.blit(car_image, (car_x - CAR_WIDTH // 2, car_y))
    
    # Display speed
    font = pygame.font.SysFont(None, 36)
    speed_text = font.render(f"Speed: {car_speed:.1f} km/h", True, WHITE)
    screen.blit(speed_text, (10, 10))

    # Update display
    pygame.display.flip()
    
    # Control frame rate
    clock.tick(60)

pygame.quit()