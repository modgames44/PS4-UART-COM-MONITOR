import serial
import serial.tools.list_ports
import sys
import ctypes
from colorama import init, Fore, Style
from datetime import datetime
import time

# Inicializar colorama para la salida de texto en color
init(autoreset=True)

def set_cmd_window_size(width, height):
    """ Configura el tamaño de la ventana de la consola. """
    sys.stdout.write(f"\x1b[8;{height};{width}t")

def set_window_title(title):
    """ Establece el título de la ventana de la consola. """
    if sys.platform.startswith('win'):
        ctypes.windll.kernel32.SetConsoleTitleA(title.encode())
    else:
        # No cambiar el título en sistemas no Windows
        pass

def list_serial_ports():
    """ Lista todos los puertos seriales disponibles en el sistema y devuelve la lista. """
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print(Fore.RED + "No hay dispositivos seriales disponibles.")
        return None
    return ports

def find_serial_port():
    """ Intenta encontrar un puerto serial que contenga cualquiera de las descripciones en la lista TTL_descriptions. """
    TTL_descriptions = ["USB-SERIAL", "USB Serial Port"]
    ports = list_serial_ports()
    if ports:
        for port in ports:
            for description in TTL_descriptions:
                if description in port.description:
                    return port.device
        return user_select_port(ports)
    return None

def user_select_port(ports):
    """ Permite al usuario seleccionar un puerto serial de la lista de puertos disponibles. """
    print(Fore.CYAN + "No se encontró un dispositivo compatible. Por favor, elija un puerto de la lista:")
    print(Fore.YELLOW + "0: Salir del programa")
    for index, port in enumerate(ports, start=1):
        print(Fore.YELLOW + f"{index}: {port.device} - {port.description}")
    while True:
        choice = input(Fore.GREEN + "Ingrese el número del puerto que desea usar (0 para salir): ")
        if choice.isdigit():
            choice = int(choice)
            if choice == 0:
                print(Fore.CYAN + "Saliendo del programa...")
                sys.exit(0)
            elif 1 <= choice <= len(ports):
                return ports[choice - 1].device
            else:
                print(Fore.RED + "Selección inválida. Intente de nuevo.")
        else:
            print(Fore.RED + "Entrada inválida. Por favor, ingrese un número válido.")

def main():
    """ Punto de entrada principal del programa. """
    set_window_title('ModGames')
    set_cmd_window_size(100, 30)

    print(Fore.MAGENTA + Style.BRIGHT + r"""
    ___   ___          _ _____
    |  \ /  |         | |  __ \ 
    | .   . | ___   __| | |  |/ __ _ _ __ ___   ___   ___
    | |\ /| |/ _ \ / _` | | __ / _` | '_ ` _ \ / _ \ / __|
    | |   | | (_) | (_| | |_\ \ (_| | | | | | |  __/ \__ \  
    \_|   |_/\___/ \__,_|\____/\__,_|_| |_| |_|\___| |___/
                                             Logo by Ed93
    """)
    print(f"{Fore.BLUE + Style.BRIGHT}Mod Uart: {Fore.RESET}")

    port = find_serial_port()
    if port is None:
        print(Fore.RED + "No se seleccionó ningún puerto serial.")
        return

    print(Fore.GREEN + f"Conectando a {port} a 115200 baudios.")
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"serial_log_{current_datetime}.txt"

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        log_file = open(log_filename, "a")
        last_data_time = time.time()

        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                print(Fore.WHITE + data, end='')
                log_file.write(data)
                log_file.flush()
                last_data_time = time.time()
            elif time.time() - last_data_time > 30:
                print(Fore.RED + "\nNo se han recibido más datos. El puerto COM ha sido desconectado.")
                break

    except serial.SerialException as e:
        print(Fore.RED + f"Error al abrir el puerto {port}: {e}")
    except IOError as e:
        print(Fore.RED + f"Error al abrir el archivo de log {log_filename}: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
        if 'log_file' in locals() and not log_file.closed:
            log_file.close()
        print(Fore.GREEN + "Conexión cerrada.")
        input("Presione Enter para salir...")

if __name__ == "__main__":
    main()
