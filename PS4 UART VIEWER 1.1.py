import sys
import serial
import threading
import datetime
import logging
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QComboBox, QLineEdit, QMessageBox, QDialog, QTextBrowser
from serial.tools.list_ports import comports

log_filename = datetime.datetime.now().strftime("uart_log_%Y%m%d_%H%M%S.txt")

logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UartViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.uart = None
        self.connected = False
        self.connecting = False
        self.baud_rate = 115200

        self.initUI()

    def initUI(self):
        self.setWindowTitle("PS4 UART VIEWER")
        self.setGeometry(100, 100, 1024, 768)  # Establece la resolución de la ventana

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        monitor_layout = QVBoxLayout()
        command_layout = QHBoxLayout()

        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self.connect)
        self.disconnect_button = QPushButton("Desconectar")
        self.disconnect_button.clicked.connect(self.disconnect)
        self.disconnect_button.setEnabled(False)
        self.log_button = QPushButton("Log")
        self.log_button.clicked.connect(self.open_log)
        self.close_button = QPushButton("Cerrar")
        self.close_button.clicked.connect(self.close_program)

        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.disconnect_button)
        control_layout.addWidget(self.log_button)
        control_layout.addWidget(self.close_button)

        self.port_combo = QComboBox()
        self.port_combo.addItem("Detectando...")
        self.port_combo.setEnabled(False)

        self.monitor_text = QTextBrowser()
        self.monitor_text.setStyleSheet("background-color: black; color: white;")

        self.command_entry = QLineEdit()
        self.send_button = QPushButton("Enviar Comando")
        self.send_button.clicked.connect(self.send_command)

        command_layout.addWidget(self.command_entry)
        command_layout.addWidget(self.send_button)

        monitor_layout.addWidget(self.monitor_text)
        monitor_layout.addLayout(command_layout)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.port_combo)
        main_layout.addLayout(monitor_layout)

        main_widget.setLayout(main_layout)

        self.update_port_timer = QTimer(self)
        self.update_port_timer.timeout.connect(self.update_port)
        self.update_port_timer.start(1000)  # Actualiza cada segundo

        # Crear un hilo para la lectura de datos en segundo plano
        self.data_thread = DataThread()
        self.data_thread.dataReceived.connect(self.update_monitor)

    def connect(self):
        if self.connecting:
            return
        port = self.port_combo.currentText()
        if not port or port == "Detectando...":
            return
        try:
            self.uart = serial.Serial(port, self.baud_rate)
            self.connected = True
            self.connecting = False
            self.connect_button.setEnabled(False)  # Deshabilitar el botón de conectar
            self.disconnect_button.setEnabled(True)
            QMessageBox.information(self, "Conexión", f"Conectado al puerto {port} con {self.baud_rate} baudios")
            logging.info(f"Conectado al puerto {port} con {self.baud_rate} baudios")
            self.data_thread.set_uart(self.uart)  # Asignar el puerto UART al hilo de datos
            self.data_thread.start()  # Iniciar el hilo de lectura de datos
        except serial.SerialException as e:
            self.connecting = False
            QMessageBox.critical(self, "Error de conexión", str(e))
            logging.error(f"Error de conexión: {str(e)}")

    def send_command(self):
        command = self.command_entry.text()
        if self.uart and self.connected:
            self.uart.write(command.encode('utf-8') + b'\n')
            logging.info(f"Enviado: {command}")
        else:
            QMessageBox.critical(self, "Error", "No se puede enviar el comando: no hay conexión activa.")

    def disconnect(self):
        if self.uart:
            self.uart.close()
            self.connected = False
            self.disconnect_button.setEnabled(False)
            self.connect_button.setEnabled(True)  # Habilitar el botón de conectar
            QMessageBox.information(self, "Desconexión", "Conexión cerrada.")
            logging.info("Conexión cerrada.")
            self.update_monitor("Desconectado del puerto COM")

    def open_log(self):
        try:
            with open(log_filename, 'r') as log_file:
                log_contents = log_file.read()
                log_dialog = LogDialog(log_contents)
                log_dialog.exec_()
        except FileNotFoundError:
            QMessageBox.information(self, "Registro de Log", "El registro de log aún no existe.")

    def close_program(self):
        if self.connected:
            self.disconnect()
        QApplication.quit()  # Cerrar la aplicación correctamente

    def update_port(self):
        if not self.connecting:
            selected_port = self.port_combo.currentText()  # Obtener el puerto seleccionado actual
            ports = self.check_ports()
            if ports:
                self.port_combo.clear()
                self.port_combo.addItems(ports)
                self.port_combo.setEnabled(True)
                if self.connected:
                    self.disconnect_button.setEnabled(True)
                # Restaurar la selección anterior si está disponible en la nueva lista de puertos
                if selected_port in ports:
                    self.port_combo.setCurrentText(selected_port)
            else:
                self.port_combo.clear()
                self.port_combo.addItem("No se ha detectado ningún puerto COM disponible")
                self.port_combo.setEnabled(False)
                self.disconnect_button.setEnabled(False)
                self.connect_button.setEnabled(False)  # Deshabilitar el botón de conectar
            self.connecting = False

    def check_ports(self):
        available_ports = [port.device for port in comports()]
        return available_ports

    def update_monitor(self, data):
        self.monitor_text.append(data)

class DataThread(QThread):
    dataReceived = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.uart = None
        self.running = False

    def set_uart(self, uart):
        self.uart = uart

    def run(self):
        self.running = True
        while self.running:
            try:
                data = self.uart.readline()
                if data:
                    data_str = data.decode('utf-8', errors='replace')
                    print("Datos recibidos:", data_str)
                    logging.info(data_str)
                    self.dataReceived.emit(data_str)
            except serial.SerialException as e:
                print("Error de lectura:", e)
                logging.error(f"Error de lectura: {str(e)}")
                self.running = False

class LogDialog(QDialog):
    def __init__(self, log_contents):
        super().__init__()
        self.setWindowTitle("Registro de Log")
        self.setGeometry(100, 100, 640, 480)  # Ajusta la resolución de la ventana del log

        layout = QVBoxLayout()

        log_text = QTextBrowser(self)
        log_text.setPlainText(log_contents)
        log_text.setReadOnly(True)

        layout.addWidget(log_text)

        button = QPushButton("Cerrar", self)
        button.clicked.connect(self.accept)

        layout.addWidget(button)

        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UartViewer()
    window.show()
    sys.exit(app.exec_())
