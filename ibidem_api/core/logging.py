LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "[%(asctime)s|%(levelprefix)s] %(message)s [%(name)s|%(threadName)s]",
            "use_colors": None,
        },
        "json": {
            "()": "fiaas_logging.FiaasFormatter",
        },
    },
    "handlers": {
        "default": {
            "formatter": "plain",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"handlers": ["default"], "level": "INFO"},
}


def get_log_config(format, log_level):
    config = LOGGING_CONFIG.copy()
    config["handlers"]["default"]["formatter"] = format
    config["root"]["level"] = log_level
    return config
