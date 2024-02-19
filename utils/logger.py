from logging import DEBUG, getLogger, handlers, Formatter, Logger, StreamHandler, INFO


class AppLogger:
    logger: Logger

    def __init__(self) -> None:
        self.logger = getLogger("discord")

    def setup(self):
        handler = handlers.RotatingFileHandler(
            filename="discord.log",
            encoding="utf-8",
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        console_formatter = StreamHandler()
        console_formatter.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.addHandler(console_formatter)
        self.logger.setLevel(DEBUG)
