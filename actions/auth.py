from datetime import datetime, timedelta
from typing import Union

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette import status

from actions.user import get_user_by_email
from config import apisecrets, get_logger
from models.user import User
from schemas.auth import TokenData

logger = get_logger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = apisecrets.SECRET_KEY
ACCESS_TOKEN_ALGORITHM = 'HS256'
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def valid_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, user_email: str,
                      password: str) -> Union[bool, User]:
    user = get_user_by_email(db, user_email)
    if not user:
        return False
    if not valid_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode,
                             SECRET_KEY,
                             algorithm=ACCESS_TOKEN_ALGORITHM)
    return encoded_jwt


def get_current_user(db: Session, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token,
                             SECRET_KEY,
                             algorithms=[ACCESS_TOKEN_ALGORITHM])
        email = payload.get("sub")
        if email is None or email == '':
            raise credentials_exception
        token_data = TokenData(email=email)
    except PyJWTError:
        raise credentials_exception
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise credentials_exception
    return user