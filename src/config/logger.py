import logging
from logging import Logger, basicConfig, getLevelName, getLogger

import google.cloud.logging
from fastapi_cloud_logging.fastapi_cloud_logging_handler import FastAPILoggingFilter
from google.cloud.logging_v2.handlers import (
    CloudLoggingFilter,
    StructuredLogHandler,
    setup_logging,
)
from google.cloud.logging_v2.handlers._monitored_resources import detect_resource
from google.cloud.logging_v2.handlers.handlers import EXCLUDED_LOGGER_DEFAULTS

logger: Logger = None


def get_logger(level: str) -> Logger:
    global logger
    if logger:
        return logger

    level = getLevelName(level)
    if is_gcp():
        # Instantiates a client
        client = google.cloud.logging.Client()

        # This logic comes from `google.cloud.logging.Client.setup_logging()`_
        #
        # Manually set up StructuredLogHandler to force the use of it
        # This is to avoid the error in cloud batch (compute engine) environment:
        #   CloudLoggingHandler shutting down,
        #   cannot send logs entries to Cloud Logging due to inconsistent
        #   threading behavior at shutdown. To avoid this issue,
        #   flush the logging handler manually or switch to StructuredLogHandler.
        #   You can also close the CloudLoggingHandler manually
        #   via handler.close or client.close.
        handler = StructuredLogHandler()
        client._handlers.add(handler)

        # This logic comes from `fastapi_cloud_logging.fastapi_cloud_logging_handler.FastAPILoggingHandler`_  # noqa: E501
        for filter in handler.filters:
            if isinstance(filter, CloudLoggingFilter):
                handler.removeFilter(filter)
        handler.addFilter(FastAPILoggingFilter())

        setup_logging(
            handler,
            log_level=level,
            excluded_loggers=EXCLUDED_LOGGER_DEFAULTS,
        )

    basicConfig(level=level)
    for name in logging.root.manager.loggerDict:
        if any(
            (name.startswith(prefix) for prefix in ["urllib3", "httpcore", "httpx"])
        ):
            getLogger(name).setLevel(logging.INFO)

    logger = getLogger("Logger")
    return logger


def is_gcp() -> bool:
    """Check if the environment is running on Google Cloud Platform."""
    resource = detect_resource()
    return resource.type != "global"
