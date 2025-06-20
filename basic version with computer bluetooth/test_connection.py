import serial
import time

# Test different COM ports
com_ports = ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8']

print("Testing Bluetooth connection...")
print("Make sure your robot is ON and HC-06 LED is blinking\n")

for port in com_ports:
    try:
        print(f"Trying {port}... ", end='')
        ser = serial.Serial(port, 9600, timeout=1)
        time.sleep(2)  # Give it time to connect
        
        # Send a test command
        ser.write(b'M')  # Request distance measurement
        time.sleep(0.5)
        
        # Check for response
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"✅ SUCCESS! Got response: {response}")
            print(f"\nYour robot is on {port}")
            print("The HC-06 LED should now be SOLID RED (not blinking)")
            
            # Keep connection alive
            print("\nPress Ctrl+C to disconnect")
            try:
                while True:
                    ser.write(b'M')
                    time.sleep(1)
                    if ser.in_waiting:
                        print(f"Distance: {ser.readline().decode('utf-8').strip()}")
            except KeyboardInterrupt:
                pass
                
            ser.close()
            break
        else:
            print("No response")
            ser.close()
            
    except Exception as e:
        print(f"Failed: {e}")

print("\nIf no ports worked, check:")
print("1. Is the robot powered on?")
print("2. Is HC-06 properly wired?")
print("3. Did you upload the Arduino code?")
print("4. Try removing and re-pairing the HC-06")