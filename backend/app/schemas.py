from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class UserBase(BaseModel):
    github_id: int
    username: str
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    encrypted_access_token: str


class UserRead(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    repo_id: str
    repo_name: str
    repo_full_name: str
    repo_pushed_at: str


class JobRead(BaseModel):
    id: str
    user_id: str
    repo_id: str
    repo_name: str
    repo_full_name: str
    repo_pushed_at: str
    status: str
    checkpoint: str
    agent1_output: Optional[Dict[str, Any]] = None
    agent2_output: Optional[Dict[str, Any]] = None
    agent3_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    input_tokens: int
    output_tokens: int
    model_used: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepoRead(BaseModel):
    id: str
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    pushed_at: str
    language: Optional[str] = None
    stargazers_count: int
    has_readme: bool = True


class DraftUpdate(BaseModel):
    post_index: int
    content: str
