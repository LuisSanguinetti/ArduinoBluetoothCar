#!/usr/bin/env python3
"""
PS5 DualSense Controller for Arduino Robot Car
Requires: pip install pygame pyserial
"""

import pygame
import serial
import serial.tools.list_ports
import time
import math
import sys

class PS5RobotController:
    def __init__(self):
        self.serial_port = None
        self.connected = False
        self.running = True
        self.controller = None
        
        # PS5 DualSense button mapping
        self.BUTTON_X = 0
        self.BUTTON_CIRCLE = 1
        self.BUTTON_TRIANGLE = 2
        self.BUTTON_SQUARE = 3
        self.BUTTON_L1 = 4
        self.BUTTON_R1 = 5
        self.BUTTON_L2 = 6
        self.BUTTON_R2 = 7
        self.BUTTON_SHARE = 8
        self.BUTTON_OPTIONS = 9
        self.BUTTON_PS = 10
        self.BUTTON_L3 = 11
        self.BUTTON_R3 = 12
        
        # Axes
        self.AXIS_LEFT_X = 0
        self.AXIS_LEFT_Y = 1
        self.AXIS_RIGHT_X = 2
        self.AXIS_RIGHT_Y = 3
        self.AXIS_L2 = 4
        self.AXIS_R2 = 5
        
        # Control settings
        self.deadzone = 0.15
        self.max_speed = 255
        self.servo_angle = 90
        self.turbo_mode = False
        
    def init_controller(self):
        """Initialize PS5 controller"""
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            print("❌ No controller detected! Please connect your PS5 controller.")
            print("   - For USB: Just plug it in")
            print("   - For Bluetooth: Pair it in your system settings first")
            return False
            
        self.controller = pygame.joystick.Joystick(0)
        self.controller.init()
        
        print(f"✅ Controller detected: {self.controller.get_name()}")
        print(f"   Axes: {self.controller.get_numaxes()}")
        print(f"   Buttons: {self.controller.get_numbuttons()}")
        
        return True
        
    def find_arduino_port(self):
        """Auto-detect Arduino with HC-06 Bluetooth"""
        ports = serial.tools.list_ports.comports()
        
        # Look for HC-06 or Arduino
        for port in ports:
            if any(x in port.description for x in ["HC-06", "Bluetooth", "Arduino"]):
                return port.device
                
        # Manual selection
        print("\n📡 Available serial ports:")
        for i, port in enumerate(ports):
            print(f"   {i}: {port.device} - {port.description}")
            
        choice = input("\nSelect port number: ")
        try:
            return ports[int(choice)].device
        except:
            return None
            
    def connect_arduino(self):
        """Connect to Arduino via Bluetooth"""
        port = self.find_arduino_port()
        if not port:
            return False
            
        try:
            self.serial_port = serial.Serial(port, 9600, timeout=0.1)
            time.sleep(2)  # Wait for connection
            self.connected = True
            print(f"✅ Connected to Arduino on {port}")
            
            # Enable joystick mode on Arduino
            self.serial_port.write(b'J')
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    def send_motor_command(self, left_speed, right_speed):
        """Send motor speeds to Arduino"""
        if self.connected:
            try:
                # Format: "M,left_speed,right_speed\n"
                command = f"M,{left_speed},{right_speed}\n"
                self.serial_port.write(command.encode())
            except:
                self.connected = False
                
    def send_command(self, cmd):
        """Send single character command"""
        if self.connected:
            try:
                self.serial_port.write(cmd.encode())
            except:
                self.connected = False
                
    def process_controller_input(self):
        """Process PS5 controller input"""
        pygame.event.pump()
        
        # Get joystick values
        left_x = self.controller.get_axis(self.AXIS_LEFT_X)
        left_y = -self.controller.get_axis(self.AXIS_LEFT_Y)  # Invert Y
        right_x = self.controller.get_axis(self.AXIS_RIGHT_X)
        
        # Apply deadzone
        if abs(left_x) < self.deadzone: left_x = 0
        if abs(left_y) < self.deadzone: left_y = 0
        if abs(right_x) < self.deadzone: right_x = 0
        
        # Calculate motor speeds using arcade drive
        forward = left_y * self.max_speed
        turn = left_x * self.max_speed * 0.7  # Reduce turn rate
        
        left_speed = int(forward + turn)
        right_speed = int(forward - turn)
        
        # Apply turbo mode (R2 trigger)
        r2_value = (self.controller.get_axis(self.AXIS_R2) + 1) / 2  # Convert to 0-1
        if r2_value > 0.1:
            boost = 1 + (r2_value * 0.5)  # Up to 50% boost
            left_speed = int(left_speed * boost)
            right_speed = int(right_speed * boost)
        
        # Constrain speeds
        left_speed = max(-255, min(255, left_speed))
        right_speed = max(-255, min(255, right_speed))
        
        # Send motor command
        self.send_motor_command(left_speed, right_speed)
        
        # Process servo control (right stick X)
        if abs(right_x) > self.deadzone:
            self.servo_angle = int(90 + (right_x * 90))
            self.servo_angle = max(0, min(180, self.servo_angle))
            self.send_command(f'V{self.servo_angle}\n'.encode())
        
        # Process buttons
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                self.handle_button_press(event.button)
            elif event.type == pygame.JOYBUTTONUP:
                self.handle_button_release(event.button)
                
    def handle_button_press(self, button):
        """Handle button press events"""
        if button == self.BUTTON_X:  # X - Honk
            self.send_command(b'H')
            print("🔊 HONK!")
            
        elif button == self.BUTTON_CIRCLE:  # Circle - Measure distance
            self.send_command(b'M')
            print("📏 Measuring distance...")
            
        elif button == self.BUTTON_TRIANGLE:  # Triangle - Center servo
            self.servo_angle = 90
            self.send_command(b'C')
            print("🎯 Servo centered")
            
        elif button == self.BUTTON_SQUARE:  # Square - Stop
            self.send_motor_command(0, 0)
            print("🛑 STOP")
            
        elif button == self.BUTTON_L1:  # L1 - Spin left
            self.send_motor_command(-200, 200)
            print("↺ Spinning left")
            
        elif button == self.BUTTON_R1:  # R1 - Spin right
            self.send_motor_command(200, -200)
            print("↻ Spinning right")
            
        elif button == self.BUTTON_OPTIONS:  # Options - Exit
            print("👋 Exiting...")
            self.running = False
            
        elif button == self.BUTTON_PS:  # PS button - Emergency stop
            self.send_motor_command(0, 0)
            self.send_command(b'X')
            print("🚨 EMERGENCY STOP")
            
    def handle_button_release(self, button):
        """Handle button release events"""
        if button in [self.BUTTON_L1, self.BUTTON_R1]:
            # Stop spinning when L1/R1 released
            self.send_motor_command(0, 0)
            
    def display_status(self):
        """Display controller status"""
        print("\n" + "="*50)
        print("🎮 PS5 ROBOT CONTROLLER")
        print("="*50)
        print(f"Connection: {'🟢 Connected' if self.connected else '🔴 Disconnected'}")
        print(f"Servo Angle: {self.servo_angle}°")
        print("\nCONTROLS:")
        print("├─ Left Stick: Drive")
        print("├─ Right Stick X: Servo control")
        print("├─ R2: Turbo boost")
        print("├─ X: Honk")
        print("├─ Circle: Measure distance")
        print("├─ Triangle: Center servo")
        print("├─ Square: Stop")
        print("├─ L1/R1: Spin left/right")
        print("├─ PS: Emergency stop")
        print("└─ Options: Exit")
        print("="*50)
        
    def run(self):
        """Main control loop"""
        print("🚀 PS5 Robot Controller Starting...")
        
        # Initialize controller
        if not self.init_controller():
            return
            
        # Connect to Arduino
        if not self.connect_arduino():
            print("⚠️  Running in demo mode")
            
        self.display_status()
        
        # Main loop
        clock = pygame.time.Clock()
        last_display = time.time()
        
        while self.running:
            try:
                # Process controller input
                self.process_controller_input()
                
                # Update display every 2 seconds
                if time.time() - last_display > 2:
                    self.display_status()
                    last_display = time.time()
                
                # Run at 60 FPS
                clock.tick(60)
                
            except KeyboardInterrupt:
                break
                
        # Cleanup
        print("\n🛑 Shutting down...")
        if self.connected:
            self.send_motor_command(0, 0)  # Stop motors
            self.send_command(b'X')  # Emergency stop
            self.serial_port.close()
        pygame.quit()
        print("✅ Goodbye!")

if __name__ == "__main__":
    controller = PS5RobotController()
    controller.run()