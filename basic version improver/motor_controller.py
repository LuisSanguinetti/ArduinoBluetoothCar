#!/usr/bin/env python3
"""
Direct Motor Control System - AI Ready
Sends direct motor commands: "L:speed,R:speed"
Modular design for keyboard, joystick, or AI control
"""

import serial
import serial.tools.list_ports
import time
import threading
import sys
import math
from abc import ABC, abstractmethod

# Try imports for optional features
try:
    import pygame
    PYGAME_AVAILABLE = True
except:
    PYGAME_AVAILABLE = False

try:
    import msvcrt
    WINDOWS = True
except:
    import tty, termios
    WINDOWS = False

class MotorController:
    """Core motor control interface - handles Arduino communication"""
    
    def __init__(self, port=None, baudrate=115200):
        self.serial_port = None
        self.connected = False
        self.port = port
        self.baudrate = baudrate
        
        # State tracking
        self.left_speed = 0
        self.right_speed = 0
        self.servo_angle = 90
        self.distance = 0
        
        # Threading
        self.running = True
        self.read_thread = None
        
    def find_arduino(self):
        """Auto-detect Arduino port"""
        ports = serial.tools.list_ports.comports()
        
        # Look for Arduino/HC-06
        for port in ports:
            if any(x in port.description for x in ["Arduino", "HC-06", "Bluetooth", "USB"]):
                return port.device
                
        # Manual selection
        print("\n📡 Available ports:")
        for i, port in enumerate(ports):
            print(f"  {i}: {port.device} - {port.description}")
            
        try:
            choice = int(input("Select port number: "))
            return ports[choice].device
        except:
            return None
            
    def connect(self):
        """Connect to Arduino"""
        if not self.port:
            self.port = self.find_arduino()
            
        if not self.port:
            print("❌ No port selected")
            return False
            
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(2)  # Arduino reset time
            self.connected = True
            
            # Start read thread
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            print(f"✅ Connected to Arduino on {self.port}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from Arduino"""
        self.running = False
        if self.connected and self.serial_port:
            self.set_motors(0, 0)  # Stop motors
            time.sleep(0.1)
            self.serial_port.close()
            self.connected = False
            
    def set_motors(self, left_speed, right_speed):
        """Send motor command to Arduino"""
        if not self.connected:
            return False
            
        # Constrain speeds
        left_speed = int(max(-255, min(255, left_speed)))
        right_speed = int(max(-255, min(255, right_speed)))
        
        # Store state
        self.left_speed = left_speed
        self.right_speed = right_speed
        
        # Send command
        command = f"L:{left_speed},R:{right_speed}\n"
        try:
            self.serial_port.write(command.encode())
            return True
        except:
            self.connected = False
            return False
            
    def set_servo(self, angle):
        """Set servo angle"""
        if not self.connected:
            return False
            
        angle = int(max(0, min(180, angle)))
        self.servo_angle = angle
        
        command = f"S:{angle}\n"
        try:
            self.serial_port.write(command.encode())
            return True
        except:
            self.connected = False
            return False
            
    def get_distance(self):
        """Request distance measurement"""
        if self.connected:
            try:
                self.serial_port.write(b"D\n")
            except:
                self.connected = False
        return self.distance
        
    def emergency_stop(self):
        """Send emergency stop command"""
        if self.connected:
            try:
                self.serial_port.write(b"STOP\n")
                self.left_speed = 0
                self.right_speed = 0
            except:
                self.connected = False
                
    def _read_loop(self):
        """Background thread to read Arduino data"""
        buffer = ""
        while self.running and self.connected:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self._process_response(line.strip())
                        
            except:
                self.connected = False
            time.sleep(0.01)
            
    def _process_response(self, line):
        """Process Arduino responses"""
        if not line:
            return
            
        if line.startswith("ST:"):  # Status update
            parts = line[3:].split(',')
            if len(parts) >= 4:
                # ST:left,right,servo,distance
                self.distance = int(parts[3])
                
        elif line.startswith("DIST:"):
            self.distance = int(line[5:])
            
        elif line == "READY":
            print("🤖 Arduino ready!")


class InputController(ABC):
    """Abstract base class for input methods"""
    
    @abstractmethod
    def get_motor_speeds(self):
        """Return (left_speed, right_speed) tuple"""
        pass
        
    @abstractmethod
    def get_servo_angle(self):
        """Return servo angle or None if no change"""
        pass
        
    @abstractmethod
    def should_stop(self):
        """Return True to stop the program"""
        pass


class KeyboardController(InputController):
    """Keyboard input controller"""
    
    def __init__(self):
        self.keys_pressed = set()
        self.servo_angle = 90
        self.speed_multiplier = 0.8  # 80% max speed
        
    def get_key(self):
        """Get single keypress (cross-platform)"""
        if WINDOWS:
            if msvcrt.kbhit():
                return msvcrt.getch().decode('utf-8', errors='ignore').lower()
        else:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1)
                return char.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None
        
    def update(self):
        """Update keyboard state"""
        key = self.get_key()
        if key:
            if key == '\x1b':  # ESC
                return True  # Signal to stop
            self.keys_pressed.add(key)
        
        # Remove keys that haven't been pressed recently
        # (Simple implementation - could be improved)
        if len(self.keys_pressed) > 5:
            self.keys_pressed.clear()
            
    def get_motor_speeds(self):
        """Calculate motor speeds from keyboard input"""
        left = 0
        right = 0
        base_speed = int(255 * self.speed_multiplier)
        
        # Update input
        self.update()
        
        # Forward/Backward
        if 'w' in self.keys_pressed:
            left = base_speed
            right = base_speed
        elif 's' in self.keys_pressed:
            left = -base_speed
            right = -base_speed
            
        # Turning
        if 'a' in self.keys_pressed:
            if left == 0:  # Pivot turn
                left = -base_speed // 2
                right = base_speed // 2
            else:  # Moving turn
                left = int(left * 0.5)
        elif 'd' in self.keys_pressed:
            if right == 0:  # Pivot turn
                left = base_speed // 2
                right = -base_speed // 2
            else:  # Moving turn
                right = int(right * 0.5)
                
        # Clear movement keys after processing
        self.keys_pressed -= {'w', 'a', 's', 'd'}
        
        return (left, right)
        
    def get_servo_angle(self):
        """Get servo angle from keyboard"""
        if 'q' in self.keys_pressed:
            self.servo_angle = max(0, self.servo_angle - 10)
            self.keys_pressed.remove('q')
            return self.servo_angle
        elif 'e' in self.keys_pressed:
            self.servo_angle = min(180, self.servo_angle + 10)
            self.keys_pressed.remove('e')
            return self.servo_angle
        elif 'r' in self.keys_pressed:
            self.servo_angle = 90
            self.keys_pressed.remove('r')
            return self.servo_angle
        return None
        
    def should_stop(self):
        """Check if should stop"""
        return '\x1b' in self.keys_pressed or '\x03' in self.keys_pressed


class JoystickController(InputController):
    """Joystick/Gamepad input controller"""
    
    def __init__(self):
        if not PYGAME_AVAILABLE:
            raise Exception("pygame not installed")
            
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            raise Exception("No joystick found")
            
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        print(f"🎮 Joystick detected: {self.joystick.get_name()}")
        
        self.deadzone = 0.15
        self.servo_angle = 90
        
    def get_motor_speeds(self):
        """Calculate motor speeds from joystick"""
        pygame.event.pump()
        
        # Get axes
        x = self.joystick.get_axis(0)  # Left stick X
        y = -self.joystick.get_axis(1)  # Left stick Y (inverted)
        
        # Apply deadzone
        if abs(x) < self.deadzone: x = 0
        if abs(y) < self.deadzone: y = 0
        
        # Calculate motor speeds (arcade drive)
        forward = y * 255
        turn = x * 200
        
        left = int(forward + turn)
        right = int(forward - turn)
        
        # Constrain
        left = max(-255, min(255, left))
        right = max(-255, min(255, right))
        
        return (left, right)
        
    def get_servo_angle(self):
        """Get servo angle from right stick"""
        pygame.event.pump()
        
        # Right stick X (if available)
        if self.joystick.get_numaxes() >= 3:
            rx = self.joystick.get_axis(2)
            if abs(rx) > self.deadzone:
                self.servo_angle = int(90 + (rx * 90))
                return self.servo_angle
                
        return None
        
    def should_stop(self):
        """Check for exit button"""
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 6:  # Usually Select/Back button
                    return True
        return False


class AIController(InputController):
    """AI control interface - implement your AI logic here"""
    
    def __init__(self):
        self.target_left = 0
        self.target_right = 0
        self.servo_angle = 90
        
    def set_motors(self, left, right):
        """AI sets motor speeds"""
        self.target_left = left
        self.target_right = right
        
    def set_servo(self, angle):
        """AI sets servo angle"""
        self.servo_angle = angle
        
    def get_motor_speeds(self):
        return (self.target_left, self.target_right)
        
    def get_servo_angle(self):
        return self.servo_angle
        
    def should_stop(self):
        return False


class RobotApp:
    """Main application"""
    
    def __init__(self):
        self.motor_controller = MotorController()
        self.input_controller = None
        self.running = True
        
    def setup_input(self):
        """Setup input method"""
        print("\n🎮 Select input method:")
        print("1. Keyboard (WASD + QE for servo)")
        print("2. Joystick/Gamepad")
        print("3. AI Control (demo)")
        
        choice = input("Choice (1-3): ").strip()
        
        if choice == '2' and PYGAME_AVAILABLE:
            try:
                self.input_controller = JoystickController()
                return True
            except Exception as e:
                print(f"❌ Joystick error: {e}")
                
        if choice == '3':
            self.input_controller = AIController()
            print("✅ AI Controller ready - implement your AI logic in AIController class")
            return True
            
        # Default to keyboard
        self.input_controller = KeyboardController()
        print("✅ Keyboard control: WASD=move, QE=servo, R=center servo, ESC=exit")
        return True
        
    def display_status(self):
        """Display current status"""
        print(f"\r🤖 L:{self.motor_controller.left_speed:4d} "
              f"R:{self.motor_controller.right_speed:4d} "
              f"Servo:{self.motor_controller.servo_angle:3d}° "
              f"Dist:{self.motor_controller.distance:3d}cm", end='')
              
    def run(self):
        """Main application loop"""
        print("=" * 60)
        print("🤖 DIRECT MOTOR CONTROL SYSTEM")
        print("=" * 60)
        
        # Connect to Arduino
        if not self.motor_controller.connect():
            print("Failed to connect to Arduino")
            return
            
        # Setup input method
        if not self.setup_input():
            return
            
        print("\n🚀 Starting control loop...\n")
        
        # Control loop
        last_update = time.time()
        
        try:
            while self.running:
                # Get input
                left, right = self.input_controller.get_motor_speeds()
                servo = self.input_controller.get_servo_angle()
                
                # Send motor commands
                self.motor_controller.set_motors(left, right)
                
                # Update servo if changed
                if servo is not None:
                    self.motor_controller.set_servo(servo)
                    
                # Check for exit
                if self.input_controller.should_stop():
                    self.running = False
                    
                # Display status
                if time.time() - last_update > 0.1:
                    self.display_status()
                    last_update = time.time()
                    
                time.sleep(0.02)  # 50Hz update rate
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            
        finally:
            # Cleanup
            print("\n🛑 Shutting down...")
            self.motor_controller.disconnect()
            print("✅ Goodbye!")


# Example AI implementation
def example_ai_control():
    """Example of how to use AI controller"""
    app = RobotApp()
    app.motor_controller.connect()
    
    # Create AI controller
    ai = AIController()
    app.input_controller = ai
    
    # Example: simple obstacle avoidance
    while True:
        distance = app.motor_controller.get_distance()
        
        if distance < 30:  # Obstacle detected
            ai.set_motors(-150, 150)  # Turn right
        else:
            ai.set_motors(200, 200)  # Go forward
            
        # Let the app handle the actual motor control
        left, right = ai.get_motor_speeds()
        app.motor_controller.set_motors(left, right)
        
        time.sleep(0.1)


if __name__ == "__main__":
    app = RobotApp()
    app.run()