#!/usr/bin/env python3
"""
Simple Console-Based Robot Controller
Minimal dependencies - only requires pyserial
version2 with better UI incoming
"""

import serial
import serial.tools.list_ports
import time
import threading
import sys
import os

# For cross-platform keyboard input
try:
    import msvcrt  # Windows
    WINDOWS = True
except ImportError:
    import tty, termios  # Linux/Mac
    WINDOWS = False

class SimpleRobotController:
    """Simple console-based robot controller"""
    
    def __init__(self):
        self.serial_port = None
        self.connected = False
        self.running = True
        self.current_speed = 3
        self.last_distance = 0
        
    def clear_screen(self):
        """Clear console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def get_key(self):
        """Get single keypress (cross-platform)"""
        if WINDOWS:
            if msvcrt.kbhit():
                return msvcrt.getch().decode('utf-8', errors='ignore').lower()
        else:
            # Linux/Mac
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdin.flush()
                char = sys.stdin.read(1)
                return char.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None
    
    def find_port(self):
        """Find Bluetooth port"""
        ports = serial.tools.list_ports.comports()
        bluetooth_ports = []
        
        for port in ports:
            if "HC-06" in port.description or "Bluetooth" in port.description:
                bluetooth_ports.append(port)
        
        if bluetooth_ports:
            if len(bluetooth_ports) == 1:
                return bluetooth_ports[0].device
            else:
                print("\nMultiple Bluetooth ports found:")
                for i, port in enumerate(bluetooth_ports):
                    print(f"{i}: {port.device} - {port.description}")
                choice = input("Select port number: ")
                try:
                    return bluetooth_ports[int(choice)].device
                except:
                    return None
        
        # Manual selection
        print("\nNo Bluetooth ports auto-detected. All available ports:")
        for i, port in enumerate(ports):
            print(f"{i}: {port.device} - {port.description}")
        
        choice = input("Select port number (or press Enter to skip): ")
        if choice:
            try:
                return ports[int(choice)].device
            except:
                pass
        return None
    
    def connect(self):
        """Connect to robot"""
        port = self.find_port()
        if port:
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=0.1)
                time.sleep(2)  # Wait for connection
                self.connected = True
                print(f"\n✅ Connected to robot on {port}")
                return True
            except Exception as e:
                print(f"\n❌ Connection failed: {e}")
                return False
        return False
    
    def send_command(self, cmd):
        """Send command to robot"""
        if self.connected and self.serial_port:
            try:
                self.serial_port.write(cmd.encode())
                return True
            except:
                self.connected = False
                return False
        return False
    
    def read_serial(self):
        """Read serial data in background"""
        while self.running and self.connected:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line.startswith("DIST:"):
                        # Parse new format: DIST:L90:25
                        parts = line.split(":")
                        if len(parts) >= 3:
                            position = parts[1]  # L90, C90, R120 etc
                            distance = int(parts[2])
                            self.last_distance = f"{position} {distance}cm"
            except:
                pass
            time.sleep(0.01)
    
    def display_interface(self):
        """Display control interface"""
        self.clear_screen()
        print("=" * 50)
        print("🤖 ROBOT CAR CONTROLLER - Simple Mode")
        print("=" * 50)
        
        status = "🟢 Connected" if self.connected else "🔴 Disconnected"
        print(f"Status: {status}")
        print(f"Speed Level: {self.current_speed}/5")
        print(f"Distance: {self.last_distance} cm")
        print("=" * 50)
        
        print("\nCONTROLS:")
        print("├─ Movement:")
        print("│  W - Forward      S - Backward")
        print("│  A - Rotate Left    D - Rotate Right")
        print("│  Space - Stop")
        print("│")
        print("├─ Speed: 1-5 (Current: {})".format(self.current_speed))
        print("│")
        print("├─ Servo:")
        print("│  L - Look Left    R - Look Right")
        print("│  C - Center")
        print("│")
        print("├─ Other:")
        print("│  H - Honk    M - Measure Distance")
        print("│  ESC - Exit")
        print("└─" + "─" * 48)
        
        if not self.connected:
            print("\n⚠️  Press 'F' to retry connection")
    
    def run(self):
        """Main control loop"""
        # Try to connect
        if not self.connect():
            print("\n⚠️  Running in demo mode (no robot connected)")
            print("Press any key to continue...")
            input()
        
        # Start serial reading thread
        if self.connected:
            serial_thread = threading.Thread(target=self.read_serial, daemon=True)
            serial_thread.start()
        
        # Display initial interface
        self.display_interface()
        
        # Main control loop
        last_update = time.time()
        last_key = None
        
        print("\n👉 Ready for commands...")
        
        while self.running:
            # Get keyboard input
            key = self.get_key()
            
            if key:
                # Movement commands
                if key == 'w':
                    self.send_command('W')
                    last_key = "Forward"
                elif key == 's':
                    self.send_command('S')
                    last_key = "Backward"
                elif key == 'a':
                    self.send_command('A')
                    last_key = "Rotate Left"
                elif key == 'd':
                    self.send_command('D')
                    last_key = "Rotate Right"
                elif key == ' ':
                    self.send_command('X')
                    last_key = "STOP"
                
                # Speed control
                elif key in '12345':
                    self.current_speed = int(key)
                    self.send_command(key)
                    last_key = f"Speed {key}"
                
                # Servo control
                elif key == 'l':
                    self.send_command('L')
                    last_key = "Servo Left"
                elif key == 'r':
                    self.send_command('R')
                    last_key = "Servo Right"
                elif key == 'c':
                    self.send_command('C')
                    last_key = "Servo Center"
                
                # Special commands
                elif key == 'h':
                    self.send_command('H')
                    last_key = "HONK!"
                elif key == 'm':
                    self.send_command('M')
                    last_key = "Measuring..."
                
                # System commands
                elif key == '\x1b' or key == '\x03':  # ESC or Ctrl+C
                    self.running = False
                elif key == 'f' and not self.connected:
                    self.connect()
                    
                # Update display after command
                self.display_interface()
                if last_key:
                    print(f"\n📍 Last command: {last_key}")
                    print("\n👉 Ready for commands...")
            
            # Periodic display update (every 0.5 seconds)
            if time.time() - last_update > 0.5:
                self.display_interface()
                if last_key:
                    print(f"\n📍 Last command: {last_key}")
                    print("\n👉 Ready for commands...")
                last_update = time.time()
            
            time.sleep(0.01)  # Small delay to prevent CPU overuse
        
        # Cleanup
        print("\n\nShutting down...")
        if self.connected and self.serial_port:
            self.send_command('X')  # Stop motors
            self.serial_port.close()
        print("Goodbye! 👋")

# Main execution
if __name__ == "__main__":
    print("🚀 Starting Simple Robot Controller...")
    print("This version requires only pyserial: pip install pyserial")
    print("-" * 50)
    
    controller = SimpleRobotController()
    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        if controller.connected and controller.serial_port:
            controller.send_command('X')
            controller.serial_port.close()