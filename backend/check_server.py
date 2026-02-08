
import socket
import sys

def check_server(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    except Exception as e:
        return False

if __name__ == "__main__":
    is_running = check_server("127.0.0.1", 8000)
    msg = "RUNNING" if is_running else "STOPPED"
    with open("server_check_result.txt", "w") as f:
        f.write(msg)
    print(msg)
