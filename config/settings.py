from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    base_url: str = "http://localhost:8080/api/v1"

    user1_username: str = "test1"
    user1_password: str = "test123"

    user2_username: str = "test2"
    user2_password: str = "test456"

    # load the test configuration
    load_request_count: int = 1000
    load_max_workers: int = 50
    load_success_rate_threshold: float = 0.95

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()