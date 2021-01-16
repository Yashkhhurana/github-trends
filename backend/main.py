from fastapi import FastAPI

from external.github_api.user import get_user as _get_user
from external.github_api.repo import get_repo_stargazers as _get_repo

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/user/{user_id}")
def get_user(user_id: str) -> dict:
    return _get_user(user_id)


@app.get("/repo/{user_id}/{repo_name}")
def get_repo(user_id: str, repo_name: str) -> dict:
    return _get_repo(user_id, repo_name)