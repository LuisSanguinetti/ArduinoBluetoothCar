import serial
import serial.tools.list_ports
import time
import threading
import numpy as np
import torch
from agent import DQNAgent
import re

class ArduinoAIController:
    """AI Controller for Arduino Car"""
    
    def __init__(self, model_path='trained_models/car_agent_final.pth'):
        # Serial connection
        self.serial_port = None
        self.connected = False
        
        # AI Agent
        self.agent = DQNAgent(state_size=4, action_size=9)
        self.agent.load(model_path)
        self.agent.epsilon = 0  # No exploration during deployment
        
        # Sensor data
        self.distances = {'L': 100, 'C': 100, 'R': 100}
        self.current_speed = 3
        self.running = True
        
        # Action mapping
        self.action_map = {
            0: 'W',  # Forward
            1: 'A',  # Rotate Left
            2: 'D',  # Rotate Right
            3: 'S',  # Backward
            4: '1',  # Speed 1
            5: '2',  # Speed 2
            6: '3',  # Speed 3
            7: '4',  # Speed 4
            8: '5',  # Speed 5
        }
        
    def find_and_connect(self):
        """Find and connect to Arduino via Bluetooth"""
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            if "HC-06" in port.description or "Bluetooth" in port.description:
                try:
                    self.serial_port = serial.Serial(port.device, 9600, timeout=0.1)
                    time.sleep(2)
                    self.connected = True
                    print(f"✅ Connected to Arduino on {port.device}")
                    return True
                except Exception as e:
                    print(f"Failed to connect to {port.device}: {e}")
                    
        print("❌ No Arduino found. Available ports:")
        for i, port in enumerate(ports):
            print(f"{i}: {port.device} - {port.description}")
            
        choice = input("Select port number: ")
        try:
            port = ports[int(choice)]
            self.serial_port = serial.Serial(port.device, 9600, timeout=0.1)
            time.sleep(2)
            self.connected = True
            print(f"✅ Connected to Arduino on {port.device}")
            return True
        except:
            print("❌ Connection failed")
            return False
    
    def read_serial_data(self):
        """Read sensor data from Arduino"""
        while self.running and self.connected:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    
                    # Parse distance data: DIST:L30:25 or DIST:C90:50
                    if line.startswith("DIST:"):
                        match = re.match(r"DIST:([LCR])(\d+):(\d+)", line)
                        if match:
                            position = match.group(1)
                            angle = int(match.group(2))
                            distance = int(match.group(3))
                            self.distances[position] = distance
                            
            except Exception as e:
                print(f"Serial read error: {e}")
                
            time.sleep(0.01)
    
    def get_state(self):
        """Get current state for AI agent"""
        # Normalize distances (0-200cm to 0-1)
        left_dist = min(self.distances['L'], 200) / 200.0
        center_dist = min(self.distances['C'], 200) / 200.0
        right_dist = min(self.distances['R'], 200) / 200.0
        speed_norm = self.current_speed / 5.0
        
        return np.array([left_dist, center_dist, right_dist, speed_norm])
    
    def send_command(self, command):
        """Send command to Arduino"""
        if self.connected and self.serial_port:
            try:
                self.serial_port.write(command.encode())
                # Update speed if speed command
                if command in '12345':
                    self.current_speed = int(command)
                return True
            except:
                self.connected = False
                return False
        return False
    
    def run_ai_control(self):
        """Main AI control loop"""
        print("\n🤖 AI Control Active!")
        print("The AI is now controlling your Arduino car.")
        print("Press Ctrl+C to stop.\n")
        
        last_action_time = time.time()
        action_interval = 0.2  # Take action every 200ms
        
        try:
            while self.running:
                current_time = time.time()
                
                # Take action at intervals
                if current_time - last_action_time >= action_interval:
                    # Get current state
                    state = self.get_state()
                    
                    # Get AI decision
                    action = self.agent.act(state, training=False)
                    command = self.action_map[action]
                    
                    # Send command
                    self.send_command(command)
                    
                    # Display status
                    action_name = ['Forward', 'Left', 'Right', 'Backward', 
                                 'Speed1', 'Speed2', 'Speed3', 'Speed4', 'Speed5'][action]
                    print(f"\rDistances - L:{self.distances['L']:3d} "
                          f"C:{self.distances['C']:3d} R:{self.distances['R']:3d} | "
                          f"Action: {action_name:8s} | Speed: {self.current_speed}", 
                          end='', flush=True)
                    
                    last_action_time = current_time
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping AI control...")
            
    def start(self):
        """Start the AI controller"""
        # Connect to Arduino
        if not self.find_and_connect():
            print("Failed to connect to Arduino. Exiting.")
            return
            
        # Start serial reading thread
        serial_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        serial_thread.start()
        
        # Wait for initial sensor data
        print("Waiting for sensor data...")
        time.sleep(3)
        
        # Run AI control
        self.run_ai_control()
        
        # Cleanup
        self.running = False
        if self.connected:
            self.send_command('X')  # Stop motors
            self.serial_port.close()
        print("AI Controller shutdown complete.")

def test_model_in_simulator():
    """Test the trained model in simulator before real deployment"""
    from environment import CarSimulatorEnv
    
    print("Testing trained model in simulator...")
    
    env = CarSimulatorEnv(render=True)
    agent = DQNAgent(state_size=4, action_size=9)
    
    try:
        agent.load('trained_models/car_agent_final.pth')
        agent.epsilon = 0  # No exploration
    except:
        print("No trained model found! Train first using train.py")
        return
    
    for episode in range(5):
        state = env.reset()
        done = False
        total_reward = 0
        
        print(f"\nTest Episode {episode + 1}")
        
        while not done:
            action = agent.act(state, training=False)
            state, reward, done, _ = env.step(action)
            total_reward += reward
            
        print(f"Episode Score: {total_reward:.2f}, Distance: {env.total_distance:.1f}")
    
    print("\nSimulator test complete!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Test in simulator first
        test_model_in_simulator()
    else:
        # Run on real Arduino
        controller = ArduinoAIController()
        controller.start()