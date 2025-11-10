import logging
import traceback
from datetime import datetime, timezone

from libs.logging.slack import Slack


class SlackLogHandler(logging.StreamHandler):
    def __init__(self, slack: Slack, critical_log_level=logging.ERROR):
        """
        Initializes a SlackLogHandler instance.
        Args:
            slack (Slack): An instance of Slack used to send messages to a Slack channel.
            critical_log_level (int): The logging level above which messages are sent to the specified Slack channel as critical messages. Defaults to logging.WARNING.
        """
        super().__init__()
        self.slack = slack
        self.critical_log_level = critical_log_level


    def emit(self, record) -> None:
        """
        Handles the logging of messages and exceptions to the console and/or a specified Slack channel.
        Args:
            record (logging.LogRecord): The log record to be processed.
        Notes:
            If the log level of the record is above the critical_log_level, the message is sent to the specified Slack channel as a critical message.
            If the record contains an exception, the exception details are extracted and logged as part of the message.
        """
        if record:
            # Extracting exception details if available
            if record.exc_info:
                exc_type, exc_value, exc_traceback = record.exc_info
                log_message = f'{exc_type.__name__ if exc_type is not None else ""}: {exc_value}\n' + ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            else:
                log_message = record.msg

            # Deciding where to print the log
            if record.levelno >= self.critical_log_level:
                print(f'[{record.levelname}] [{record.module}.{record.funcName} Line {record.lineno}] - {log_message}')
                self.slack.send_notification(f'*[DP-EVENT] [{record.levelname}] [{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%fZ")}]*\n'
                                             f'*Module:* {record.module}.{record.funcName} (Line: {record.lineno})\n'
                                             f'*Message:* {log_message}')
            else:
                print(f'[{record.levelname}] [{record.module}.{record.funcName} Line {record.lineno}] - {log_message}')