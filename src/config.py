import toml
from os import environ


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = toml.load("config.toml")
        return cls._instance

    def __init__(self):
        self.config = toml.load("config.toml")

    def get_config(self):
        return self.config

    # ------------ APP CONFIG ------------

    def get_primary_context_size(self):
        return int(self.config["APP_CONFIG"]["PRIMARY_CONTENT_SIZE"])

    def get_secondary_context_size(self):
        return int(self.config["APP_CONFIG"]["SECONDARY_CONTENT_SIZE"])

    def get_content_per_llm_call(self):
        return int(self.config["APP_CONFIG"]["CONTENT_PER_LLM_CALL"])

    def get_max_llm_calls(self):
        return int(self.config["APP_CONFIG"]["MAX_LLM_CALLS"])

    def get_web_scraping_timeout(self):
        return int(self.config["APP_CONFIG"]["WEB_SCRAPING_TIMEOUT"])

    def get_max_sites_per_query(self):
        return int(self.config["APP_CONFIG"]["MAX_SITES_PER_QUERY"])

    # ------------ LOG CONFIG ------------

    def get_debug_logging(self):
        return self.config["LOGGING"]["DEBUG_LOGGING"] == "true"

    def get_logging(self):
        return self.config["LOGGING"]["LOGGING"] == "true"

    def save_config(self):
        with open("config.toml", "w") as f:
            toml.dump(self.config, f)
