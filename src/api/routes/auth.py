from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.database import get_db
from api.models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from api.services import auth as auth_service
from utils import jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    user = auth_service.signup_user(
        db, email=body.email, password=body.password, name=body.name
    )

    return TokenResponse(
        access_token=jwt.create_access_token(user.id),
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.login_user(db, email=body.email, password=body.password)

    return TokenResponse(
        access_token=jwt.create_access_token(user.id),
        user=UserResponse.model_validate(user),
    )
