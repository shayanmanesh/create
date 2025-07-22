from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO_PACK = "pro_pack"
    BUSINESS = "business"


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String)
    
    # Auth provider
    provider = Column(String, default="email")  # email, google, tiktok, instagram
    provider_id = Column(String)
    
    # Profile
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Subscription
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    has_unlimited = Column(Boolean, default=False)
    creations_remaining = Column(Integer, default=3)
    stripe_customer_id = Column(String)
    
    # Stats
    total_creations = Column(Integer, default=0)
    last_creation_at = Column(DateTime)
    
    # Referral
    referral_code = Column(String, unique=True, index=True)
    referred_by = Column(String, ForeignKey("users.id"))
    referral_count = Column(Integer, default=0)
    
    # Relationships
    creations = relationship("Creation", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    challenges_created = relationship("Challenge", back_populates="creator")
    challenge_participations = relationship("ChallengeParticipation", back_populates="user")


class Creation(Base):
    __tablename__ = "creations"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Content
    content_type = Column(String)  # general, movie_poster, pet_adventure, etc.
    content_urls = Column(JSON)  # {text: url, images: [urls], voiceover: url}
    metadata = Column(JSON)  # AI-generated metadata
    
    # Status
    status = Column(String, default="processing")  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float)
    
    # Engagement
    views = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    shares_by_platform = Column(JSON, default={})
    
    # Challenge
    challenge_id = Column(String, ForeignKey("challenges.id"))
    
    # Relationships
    user = relationship("User", back_populates="creations")
    challenge = relationship("Challenge", back_populates="creations")


class Challenge(Base):
    __tablename__ = "challenges"
    
    id = Column(String, primary_key=True)
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Details
    title = Column(String, nullable=False)
    description = Column(Text)
    hashtag = Column(String, unique=True, nullable=False, index=True)
    theme_prompts = Column(JSON)
    
    # Status
    is_official = Column(Boolean, default=False)
    is_boosted = Column(Boolean, default=False)
    boost_ends_at = Column(DateTime)
    
    # Timeline
    starts_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Stats
    participant_count = Column(Integer, default=0)
    creation_count = Column(Integer, default=0)
    
    # Prize
    prize_description = Column(Text)
    
    # Relationships
    creator = relationship("User", back_populates="challenges_created")
    creations = relationship("Creation", back_populates="challenge")
    participations = relationship("ChallengeParticipation", back_populates="challenge")


class ChallengeParticipation(Base):
    __tablename__ = "challenge_participations"
    
    id = Column(String, primary_key=True)
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    creation_id = Column(String, ForeignKey("creations.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    challenge = relationship("Challenge", back_populates="participations")
    user = relationship("User", back_populates="challenge_participations")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Stripe
    stripe_payment_intent_id = Column(String, unique=True)
    
    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String, default="usd")
    surge_multiplier = Column(Float, default=1.0)
    
    # Details
    plan_type = Column(String)  # single, basic, pro_pack, business, viral_boost
    status = Column(String, default="pending")  # pending, succeeded, failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="payments")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True)  # Stripe subscription ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    plan_type = Column(String, nullable=False)
    status = Column(String, default="active")  # active, canceled, past_due
    
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    
    auto_renew = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    canceled_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")