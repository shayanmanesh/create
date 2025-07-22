from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.services.database import get_db
from app.models import User
import uuid
import httpx

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    referral_code: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SocialLogin(BaseModel):
    provider: str  # google, tiktok, instagram
    access_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db = Depends(get_db)):
    """Register new user"""
    
    # Check if user exists
    existing_user = await db.query(User).filter(
        User.email == user_data.email
    ).first()
    
    if existing_user:
        raise HTTPException(400, "Email already registered")
    
    # Check username
    existing_username = await db.query(User).filter(
        User.username == user_data.username
    ).first()
    
    if existing_username:
        raise HTTPException(400, "Username already taken")
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        created_at=datetime.utcnow(),
        subscription_tier="free",
        creations_remaining=3,  # Free tier
        referral_code=str(uuid.uuid4())[:8]
    )
    
    # Handle referral
    if user_data.referral_code:
        referrer = await db.query(User).filter(
            User.referral_code == user_data.referral_code
        ).first()
        
        if referrer:
            user.referred_by = referrer.id
            # Give referrer bonus creation
            referrer.creations_remaining += 1
            referrer.referral_count += 1
    
    db.add(user)
    await db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_tier": user.subscription_tier,
            "creations_remaining": user.creations_remaining
        }
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db = Depends(get_db)):
    """Login with email and password"""
    
    user = await db.query(User).filter(
        User.email == credentials.email
    ).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_tier": user.subscription_tier,
            "creations_remaining": user.creations_remaining
        }
    }


@router.post("/social-login", response_model=Token)
async def social_login(social_data: SocialLogin, db = Depends(get_db)):
    """Login with social providers"""
    
    # Verify social token with provider
    user_info = await verify_social_token(social_data.provider, social_data.access_token)
    
    if not user_info:
        raise HTTPException(401, "Invalid social token")
    
    # Find or create user
    user = await db.query(User).filter(
        User.email == user_info["email"]
    ).first()
    
    if not user:
        # Create new user from social login
        user = User(
            id=str(uuid.uuid4()),
            email=user_info["email"],
            username=user_info.get("username", user_info["email"].split("@")[0]),
            provider=social_data.provider,
            provider_id=user_info["id"],
            created_at=datetime.utcnow(),
            subscription_tier="free",
            creations_remaining=3,
            referral_code=str(uuid.uuid4())[:8]
        )
        db.add(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_tier": user.subscription_tier,
            "creations_remaining": user.creations_remaining
        }
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "subscription_tier": current_user.subscription_tier,
        "creations_remaining": current_user.creations_remaining,
        "total_creations": current_user.total_creations,
        "referral_code": current_user.referral_code,
        "referral_count": current_user.referral_count
    }


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Logout user"""
    # In a production app, you might want to blacklist the token
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


async def verify_social_token(provider: str, token: str) -> Optional[Dict]:
    """Verify social provider tokens"""
    
    async with httpx.AsyncClient() as client:
        try:
            if provider == "google":
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data["id"],
                        "email": data["email"],
                        "username": data.get("name", "").replace(" ", "_").lower()
                    }
            
            elif provider == "tiktok":
                # TikTok OAuth verification
                response = await client.get(
                    "https://open-api.tiktok.com/oauth/userinfo/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    data = response.json()["data"]
                    return {
                        "id": data["open_id"],
                        "email": data.get("email", f"{data['display_name']}@tiktok.local"),
                        "username": data["display_name"]
                    }
            
            elif provider == "instagram":
                # Instagram Basic Display API
                response = await client.get(
                    f"https://graph.instagram.com/me?fields=id,username&access_token={token}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data["id"],
                        "email": f"{data['username']}@instagram.local",
                        "username": data["username"]
                    }
            
        except Exception as e:
            print(f"Social auth error: {e}")
    
    return None