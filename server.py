import os
import http.server
import socket
import subprocess
import urllib.parse
import sys

PORT = 8000  # Порт, на котором будет работать сервер
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "transfer_data")  # Путь к папке рядом с исполняемым файлом

# Функция для открытия порта в брандмауэре Windows
def open_port_windows(port):
    rule_name = f"Open Port {port}"
    try:
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                        f'name={rule_name}', 'dir=in', 'action=allow',
                        'protocol=TCP', f'localport={port}'],
                       check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при открытии порта: {e}")

# Функция для закрытия порта в брандмауэре Windows
def close_port_windows(port):
    rule_name = f"Open Port {port}"
    try:
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                        f'name={rule_name}'],
                       check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при закрытии порта: {e}")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = super().translate_path(path)
        return os.path.join(DIRECTORY, os.path.relpath(path, os.path.dirname(path)))

    def do_GET(self):
        print(f"Получен запрос: {self.path} от {self.client_address}")  # Логирование запроса
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_html().encode('utf-8'))
        else:
            # Декодируем URL
            file_path = os.path.join(DIRECTORY, urllib.parse.unquote(self.path.lstrip('/')))
            if os.path.isfile(file_path):
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/pdf')  # Укажите правильный тип содержимого

                    # Кодируем имя файла в utf-8 и добавляем к заголовку
                    safe_filename = urllib.parse.quote(os.path.basename(file_path))
                    self.send_header('Content-Disposition', f'attachment; filename="{safe_filename}"')
                    self.send_header('Content-Length', str(os.path.getsize(file_path)))
                    self.end_headers()

                    # Чтение и отправка файла
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                except Exception as e:
                    print(f"Ошибка при отправке файла: {e}")
                    self.send_error(500, "Ошибка при отправке файла")
            else:
                self.send_error(404, "File not found")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        boundary = self.headers['Content-Type'].split("=")[1].encode('utf-8')
        body = self.rfile.read(content_length)

        # Разделяем тело запроса на части по границе
        parts = body.split(boundary)

        # Проверка на наличие файла
        file_found = False
        for part in parts:
            if b'filename="' in part:
                file_found = True
                # Извлекаем имя файла
                filename = part.split(b'filename="')[1].split(b'"')[0].decode('utf-8')
                filename = os.path.basename(filename)

                # Извлекаем данные файла
                # Находим начало данных файла
                header_end = part.find(b'\r\n\r\n') + 4
                file_data = part[header_end:-len(b'\r\n--')]

                # Сохраняем файл
                with open(os.path.join(DIRECTORY, filename), 'wb') as f:
                    f.write(file_data)

                self.send_response(201)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(self.get_success_message().encode('utf-8'))
                return

        # Если файл не найден, отправляем сообщение об ошибке
        if not file_found:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_error_message().encode('utf-8'))

    def get_success_message(self):
        return """
        <html>
        <body style="background-color: #121212;">
            <p style="color: #ffff00; font-size: 20px">Файл успешно загружен.</p>
            <a href="/" style="font-size: 30px; color: #ffff00;">На главную</a>
        </body>
        </html>
        """

    def get_error_message(self):
        return """
        <html>
        <body style="background-color: #121212;">
            <p style="color: #ffff00; font-size: 20px">Файл не выбран.</p>
            <a href="/" style="font-size: 30px; color: #ffff00;">На главную</a>
        </body>
        </html>
        """

    def get_html(self):
        files = os.listdir(DIRECTORY)
        file_links = ''.join(f'<li><a href="{file}" download>{file}</a></li>' for file in files)
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Файловый сервер</title>
            <style>
                body {{
                    background-color: #121212;
                    color: #ffff00;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    box-sizing: border-box;
                }}
                h1, h2 {{
                    color: #ffff00;
                }}
                a {{
                    color: #bb86fc;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                form {{
                    margin-bottom: 20px;
                }}
                input[type="file"], input[type="submit"] {{
                    padding: 10px;
                    margin-top: 10px;
                    border: none;
                    border-radius: 5px;
                    width: 100%;
                    box-sizing: border-box;
                }}
                input[type="submit"] {{
                    background-color: #bb86fc;
                    color: #ffffff;
                    cursor: pointer;
                }}
                input[type="submit"]:hover {{
                    background-color: #3700b3;
                }}
                ul {{
                    list-style-type: none;
                    color: #ffff00;
                    padding: 0;
                }}
                li {{
                    color: #ffff00;
                    margin: 5px 0;
                }}
                @media (max-width: 600px) {{
                    body {{
                        padding: 10px;
                    }}
                    h1 {{
                        font-size: 1.5em;
                    }}
                    h2 {{
                        font-size: 1.2em;
                    }}
                }}
            </style>
        </head>
        <body>
            <h1>Файловый сервер</h1>
            <h2>Загрузить файл</h2>
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <input type="submit" value="Загрузить">
            </form>
            <h2>Доступные файлы:</h2>
            <ul>
                {file_links}
            </ul>
        </body>
        </html>
        """

def run(server_class=http.server.HTTPServer, handler_class=CustomHandler):
    server_address = ('0.0.0.0', PORT)
    httpd = server_class(server_address, handler_class)
    print(f'Сервер запущен по адресу: http://{get_ip_address()}:{PORT}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        close_port_windows(PORT)  # Закрываем порт при завершении работы сервера

def get_ip_address():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

if __name__ == "__main__":
    # Проверяем наличие директории и создаем её, если она не существует
    if not os.path.exists(DIRECTORY):
        os.makedirs(DIRECTORY)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # Переходим в директорию скрипта
    open_port_windows(PORT)  # Открываем порт перед запуском сервера
    run()
