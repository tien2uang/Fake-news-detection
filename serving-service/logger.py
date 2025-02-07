# logger.py
import datetime


class Logger:
    def __init__(self):
        self.filename = 'logs/app.log.txt'

    def writeline(self, text):
        """Ghi một dòng vào file. Mỗi lần gọi phương thức này, dữ liệu sẽ được ghi mới vào file."""
        with open(self.filename, 'w') as f:
            f.write(text + '\n')

    def append(self, text):
        """Thêm một dòng vào cuối file mà không ghi đè lên dữ liệu cũ."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} - {text}"
        with open(self.filename, 'a') as f:
            f.write(log_entry + '\n')

# Ví dụ sử dụng:
if __name__ == "__main__":
    logger = Logger()
    logger.append('This is an appended log entry.')   # Thêm vào cuối file
