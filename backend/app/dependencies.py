from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_error
    except JWTError:
        raise credentials_error
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise credentials_error
    return user

def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)):
        if user.role.name not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user
    return checker
