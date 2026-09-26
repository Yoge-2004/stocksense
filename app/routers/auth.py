from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, PasswordResetOTP, UserRole
from app.schemas import (
    UserLogin, UserCreate, UserResponse, TokenResponse,
    OTPRequest, OTPVerifyReset
)
from app.security import hash_password, verify_password, generate_otp

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken."
        )
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    user = User(
        username=user_data.username.strip(),
        email=user_data.email.strip().lower(),
        full_name=user_data.full_name.strip(),
        hashed_password=hash_password(user_data.password),
        role=user_data.role or UserRole.WAREHOUSE_STAFF,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return token."""
    user = db.query(User).filter(
        (User.username == credentials.username) | (User.email == credentials.username)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    # Simple session token
    token = f"stocksense-token-{user.id}-{int(datetime.now().timestamp())}"
    return {"token": token, "user": user}

@router.get("/me", response_model=UserResponse)
def get_current_user(token: str, db: Session = Depends(get_db)):
    """Get profile of current logged-in user."""
    try:
        parts = token.split("-")
        user_id = int(parts[2])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user

@router.post("/forgot-password")
def request_password_reset(req: OTPRequest, db: Session = Depends(get_db)):
    """Generate and return an OTP for password reset."""
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address."
        )

    otp = generate_otp(6)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    otp_record = PasswordResetOTP(
        user_id=user.id,
        otp_code=otp,
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    db.commit()

    # For hackathon/demo ease, we return the generated OTP in the response
    return {
        "message": f"OTP sent to {user.email}. (Simulated OTP: {otp})",
        "email": user.email,
        "simulated_otp": otp
    }

@router.post("/reset-password")
def reset_password(req: OTPVerifyReset, db: Session = Depends(get_db)):
    """Verify OTP and update user's password."""
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    now = datetime.now(timezone.utc)
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id,
        PasswordResetOTP.otp_code == req.otp_code,
        PasswordResetOTP.is_used == False,
        PasswordResetOTP.expires_at > now
    ).order_by(PasswordResetOTP.id.desc()).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code."
        )

    otp_record.is_used = True
    user.hashed_password = hash_password(req.new_password)
    db.commit()

    return {"message": "Password successfully reset. You may now log in with your new credentials."}
