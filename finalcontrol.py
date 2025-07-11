import socket
import time
import threading
import sys
import select
from queue import Queue, Empty
import platform

class DroneController:
    def __init__(self, drone_ip='192.168.4.153', command_port=8090, debug=False):
        """
        Initialize the drone controller
        :param drone_ip: IP address of the drone (default: 192.168.4.153)
        :param command_port: UDP port for commands (default: 8090)
        :param debug: Enable debug output (default: False)
        """
        self.drone_ip = drone_ip
        self.command_port = command_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        
        # Command queue for thread-safe command sending
        self.command_queue = Queue()
        self.running = False
        self.keep_alive_active = False
        self.debug = debug
        
        # Current command state
        self.current_cmd = {
            'throttle': 0x80,
            'yaw': 0x80,
            'pitch': 0x80,
            'roll': 0x80,
            'aux': 0x00
        }
        
        # Start the command processing thread
        self.running = True
        self.command_thread = threading.Thread(target=self._command_worker, daemon=True)
        self.command_thread.start()
    
    def _command_worker(self):
        """Worker thread that processes commands from the queue"""
        while self.running:
            try:
                # Get a command from the queue (with timeout to allow checking self.running)
                try:
                    command = self.command_queue.get(timeout=0.1)
                    if command == 'KEEP_ALIVE' and not self.keep_alive_active:
                        continue  # Skip keep-alive if not active
                    self._send_command_direct(command)
                except Empty:
                    # If queue is empty, send current command state
                    self._send_current_command()
                time.sleep(0.05)  # ~20 commands per second
            except Exception as e:
                print(f"Error in command worker: {e}")
                time.sleep(1)
    
    def _send_command_direct(self, command_data):
        """Send a command directly (internal use only)"""
        try:
            # Only print command bytes in debug mode
            if self.debug:
                print(f"Sending command: {[f'0x{b:02X}' for b in command_data]}")
            self.sock.sendto(command_data, (self.drone_ip, self.command_port))
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def _send_current_command(self):
        """Send the current command state"""
        cmd = bytes([
            0x66,  # Header
            self.current_cmd['throttle'],
            self.current_cmd['yaw'],
            self.current_cmd['pitch'],
            self.current_cmd['roll'],
            self.current_cmd['aux'],
            0x99   # Footer
        ])
        self._send_command_direct(cmd)
    
    def start_keep_alive(self):
        """Start sending keep-alive packets"""
        self.keep_alive_active = True
        print("Keep-alive started")
    
    def stop_keep_alive(self):
        """Stop sending keep-alive packets"""
        self.keep_alive_active = False
        print("Keep-alive stopped")
    
    def set_controls(self, throttle=None, yaw=None, pitch=None, roll=None, aux=None):
        """
        Set control axes
        :param throttle: Throttle (0-255, 0x80 is neutral)
        :param yaw: Yaw (0-255, 0x80 is center)
        :param pitch: Pitch (0-255, 0x80 is center)
        :param roll: Roll (0-255, 0x80 is center)
        :param aux: Auxiliary control byte
        """
        if throttle is not None:
            self.current_cmd['throttle'] = max(0, min(255, throttle))
        if yaw is not None:
            self.current_cmd['yaw'] = max(0, min(255, yaw))
        if pitch is not None:
            self.current_cmd['pitch'] = max(0, min(255, pitch))
        if roll is not None:
            self.current_cmd['roll'] = max(0, min(255, roll))
        if aux is not None:
            self.current_cmd['aux'] = max(0, min(255, aux))
    
    def takeoff(self):
        """Send takeoff command"""
        print("Sending takeoff command...")
        self.set_controls(throttle=0x80, yaw=0x80, pitch=0x80, roll=0x80, aux=0x01)
        self.start_keep_alive()
        time.sleep(1)  # Give it time to take off
        self.set_controls(aux=0x00)  # Reset aux after takeoff
        return True
    
    def land(self):
        """Send land command"""
        print("Sending land command...")
        self.set_controls(throttle=0x40, yaw=0x80, pitch=0x80, roll=0x80, aux=0x02)
        time.sleep(2)  # Give it time to land
        self.stop_keep_alive()
        self.set_controls(throttle=0x80, aux=0x00)  # Reset to neutral
        return True
    
    def emergency_stop(self):
        """Send emergency stop command"""
        print("EMERGENCY STOP!")
        # Try different emergency stop patterns
        patterns = [
            (0x40, 0x80, 0x80, 0x80, 0x04),  # Common emergency stop pattern
            (0x40, 0x80, 0x80, 0x80, 0x00),  # All neutral with low throttle
            (0x40, 0x80, 0x80, 0x80, 0x08),  # Another common emergency pattern
            (0x40, 0x80, 0x80, 0x80, 0x10),  # Yet another pattern
        ]
        
        # Send each pattern multiple times
        for _ in range(3):  # Repeat the sequence 3 times
            for throttle, yaw, pitch, roll, aux in patterns:
                print(f"Sending emergency command: throttle={throttle}, aux={aux:02X}")
                self.set_controls(throttle=throttle, yaw=yaw, pitch=pitch, roll=roll, aux=aux)
                self._send_current_command()
                time.sleep(0.1)  # Short delay between commands
        
        # Ensure motors are stopped
        self.set_controls(throttle=0x40, yaw=0x80, pitch=0x80, roll=0x80, aux=0x00)
        for _ in range(5):  # Send stop command multiple times
            self._send_current_command()
            time.sleep(0.1)
        
        self.stop_keep_alive()
        return True
    
    def manual_control(self):
        """Enter manual control mode"""
        print("\nManual Control Mode")
        print("W/S: Throttle | A/D: Yaw | I/K: Pitch | J/L: Roll | Q: Quit")
        print("Press Q to exit manual control")

        is_windows = platform.system() == "Windows"
        if is_windows:
            import msvcrt
        else:
            import tty
            import termios
            import select

        if not is_windows:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

        try:
            # Arm the drone first
            print("Arming drone...")
            self.set_controls(throttle=0x40, yaw=0x80, pitch=0x80, roll=0x80, aux=0x01)
            for _ in range(10):  # Send arm command multiple times
                self._send_current_command()
                time.sleep(0.1)

            # Reset aux but keep sending commands
            self.set_controls(aux=0x00)
            self.start_keep_alive()

            last_print = time.time()
            step = 3  # Smaller step for finer control

            while True:
                current_time = time.time()

                # Send current command state continuously
                self._send_current_command()

                key = None
                if is_windows:
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                else:
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        key = sys.stdin.read(1).lower()

                if key == 'q':
                    break

                # Throttle control (0x40-0xC0 range for safety)
                if key == 'w':
                    self.current_cmd['throttle'] = min(0xC0, self.current_cmd['throttle'] + step)
                elif key == 's':
                    self.current_cmd['throttle'] = max(0x40, self.current_cmd['throttle'] - step)

                # Yaw control
                elif key == 'a':
                    self.current_cmd['yaw'] = max(0x40, self.current_cmd['yaw'] - step)
                elif key == 'd':
                    self.current_cmd['yaw'] = min(0xC0, self.current_cmd['yaw'] + step)

                # Pitch control
                elif key == 'i':
                    self.current_cmd['pitch'] = min(0xC0, self.current_cmd['pitch'] + step)
                elif key == 'k':
                    self.current_cmd['pitch'] = max(0x40, self.current_cmd['pitch'] - step)

                # Roll control
                elif key == 'j':
                    self.current_cmd['roll'] = max(0x40, self.current_cmd['roll'] - step)
                elif key == 'l':
                    self.current_cmd['roll'] = min(0xC0, self.current_cmd['roll'] + step)

                # Print status less frequently to reduce flicker
                if current_time - last_print > 0.1:  # 10 times per second
                    print(f"\rThr: {self.current_cmd['throttle']:3d} | Yaw: {self.current_cmd['yaw']:3d} | "
                          f"Pit: {self.current_cmd['pitch']:3d} | Rol: {self.current_cmd['roll']:3d} | "
                          f"Aux: {self.current_cmd['aux']:02X}  ", end='', flush=True)
                    last_print = current_time

                time.sleep(0.02)  # ~50 updates per second
        finally:
            # Clean up
            print("\nDisarming...")
            self.set_controls(throttle=0x40, yaw=0x80, pitch=0x80, roll=0x80, aux=0x00)
            for _ in range(5):
                self._send_current_command()
                time.sleep(0.1)
            self.stop_keep_alive()
            if not is_windows:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            print("Exited manual control")
    
    def close(self):
        """Clean up resources"""
        print("Closing drone controller...")
        self.running = False
        if hasattr(self, 'command_thread') and self.command_thread.is_alive():
            self.command_thread.join(timeout=2.0)
        self.sock.close()
        print("Drone controller closed")


def main():
    # Create drone controller with debug mode off by default
    drone = DroneController(debug=False)
    is_windows = platform.system() == "Windows"

    try:
        while True:
            print("\n" * 2)  # Add some space before the menu
            print("=" * 30)
            print("Drone Controller")
            print("=" * 30)
            print("1. Takeoff")
            print("2. Land")
            print("3. Manual Control")
            print("4. Emergency Stop")
            print("5. Exit")
            print("=" * 30)

            try:
                if not is_windows:
                    import select
                    # Clear any buffered input before reading (Unix only)
                    while select.select([sys.stdin], [], [], 0.1)[0]:
                        sys.stdin.read(1)

                choice = input("\nEnter your choice (1-5): ")

                if choice == '1':
                    print("\nTaking off...")
                    if drone.takeoff():
                        print("Takeoff command sent!")
                    
                elif choice == '2':
                    print("\nLanding...")
                    if drone.land():
                        print("Land command sent!")
                    
                elif choice == '3':
                    print("\nEntering manual control mode...")
                    drone.manual_control()
                    
                elif choice == '4':
                    print("\nEMERGENCY STOP!")
                    if drone.emergency_stop():
                        print("Emergency stop command sent!")
                    
                elif choice == '5':
                    print("\nExiting...")
                    break
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                break
            except Exception as e:
                print(f"\nError: {e}")
                import traceback
                traceback.print_exc()
    
    finally:
        drone.close()
        print("Drone controller shutdown complete")


if __name__ == "__main__":
    main()