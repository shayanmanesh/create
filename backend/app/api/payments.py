from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel
from typing import Optional, Dict
import stripe
from app.config import settings
from app.services.database import get_db
from app.models import User, Payment, Subscription
from app.api.auth import get_current_user
from datetime import datetime, timedelta
import uuid

router = APIRouter()

stripe.api_key = settings.stripe_api_key


class PurchaseRequest(BaseModel):
    plan_type: str  # "basic", "pro_pack", "business", "viral_boost", "single"
    payment_method_id: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    action: str  # "cancel", "resume"


class PaymentWebhook(BaseModel):
    type: str
    data: Dict


PRICING = {
    "single": {
        "price": 0.99,
        "creations": 1,
        "name": "Single Creation"
    },
    "basic": {
        "price": 9.99,
        "creations": "unlimited",
        "name": "Basic Monthly",
        "interval": "month"
    },
    "pro_pack": {
        "price": 49.99,
        "creations": 100,
        "name": "Pro Pack"
    },
    "business": {
        "price": 499.00,
        "creations": "unlimited",
        "name": "Business",
        "interval": "month",
        "features": ["api_access", "priority_support", "custom_branding"]
    },
    "viral_boost": {
        "price": 19.99,
        "name": "Viral Boost",
        "description": "Promote challenge to 100K users"
    }
}


@router.post("/purchase")
async def create_purchase(
    request: Request,
    purchase: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a purchase or subscription"""
    
    plan = PRICING.get(purchase.plan_type)
    if not plan:
        raise HTTPException(400, "Invalid plan type")
    
    # Apply surge pricing if applicable
    base_price = plan["price"]
    surge_multiplier = getattr(request.state, 'surge_multiplier', 1.0)
    final_price = base_price * surge_multiplier
    
    try:
        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(final_price * 100),  # Convert to cents
            currency="usd",
            customer=current_user.stripe_customer_id,
            payment_method=purchase.payment_method_id,
            confirm=True,
            metadata={
                "user_id": current_user.id,
                "plan_type": purchase.plan_type,
                "surge_applied": str(surge_multiplier > 1.0)
            }
        )
        
        # Handle subscription plans
        if plan.get("interval"):
            subscription = stripe.Subscription.create(
                customer=current_user.stripe_customer_id,
                items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": plan["name"]
                        },
                        "unit_amount": int(final_price * 100),
                        "recurring": {
                            "interval": plan["interval"]
                        }
                    }
                }],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"]
            )
            
            # Save subscription to database
            db_subscription = Subscription(
                id=subscription.id,
                user_id=current_user.id,
                plan_type=purchase.plan_type,
                status="active",
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end),
                created_at=datetime.utcnow()
            )
            db.add(db_subscription)
        
        # Record payment
        payment = Payment(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            stripe_payment_intent_id=intent.id,
            amount=final_price,
            currency="usd",
            status=intent.status,
            plan_type=purchase.plan_type,
            surge_multiplier=surge_multiplier,
            created_at=datetime.utcnow()
        )
        db.add(payment)
        
        # Update user based on purchase
        if purchase.plan_type == "single":
            current_user.creations_remaining += 1
        elif purchase.plan_type == "pro_pack":
            current_user.creations_remaining += 100
        elif plan.get("creations") == "unlimited":
            current_user.has_unlimited = True
            current_user.subscription_tier = purchase.plan_type
        
        await db.commit()
        
        return {
            "success": True,
            "payment_intent_id": intent.id,
            "amount": final_price,
            "surge_applied": surge_multiplier > 1.0,
            "subscription_id": db_subscription.id if plan.get("interval") else None
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get user's current subscription"""
    
    subscription = await db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        return {
            "has_subscription": False,
            "subscription_tier": "free",
            "creations_remaining": current_user.creations_remaining
        }
    
    return {
        "has_subscription": True,
        "subscription_id": subscription.id,
        "plan_type": subscription.plan_type,
        "status": subscription.status,
        "current_period_end": subscription.current_period_end,
        "auto_renew": subscription.auto_renew
    }


@router.post("/subscription/update")
async def update_subscription(
    update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update subscription (cancel, resume, etc.)"""
    
    subscription = await db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(404, "No active subscription found")
    
    try:
        if update.action == "cancel":
            # Cancel at period end
            stripe_sub = stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=True
            )
            subscription.auto_renew = False
            
        elif update.action == "resume":
            # Resume subscription
            stripe_sub = stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=False
            )
            subscription.auto_renew = True
        
        await db.commit()
        
        return {
            "success": True,
            "subscription_status": subscription.status,
            "auto_renew": subscription.auto_renew
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db = Depends(get_db)
):
    """Handle Stripe webhooks"""
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    # Handle different event types
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        
        # Update payment status
        payment = await db.query(Payment).filter(
            Payment.stripe_payment_intent_id == payment_intent.id
        ).first()
        
        if payment:
            payment.status = "succeeded"
            await db.commit()
    
    elif event.type == "subscription.updated":
        subscription = event.data.object
        
        # Update subscription in database
        db_sub = await db.query(Subscription).filter(
            Subscription.id == subscription.id
        ).first()
        
        if db_sub:
            db_sub.status = subscription.status
            db_sub.current_period_end = datetime.fromtimestamp(
                subscription.current_period_end
            )
            await db.commit()
    
    elif event.type == "subscription.deleted":
        subscription = event.data.object
        
        # Cancel subscription in database
        db_sub = await db.query(Subscription).filter(
            Subscription.id == subscription.id
        ).first()
        
        if db_sub:
            db_sub.status = "canceled"
            
            # Remove unlimited access
            user = await db.get(User, db_sub.user_id)
            if user:
                user.has_unlimited = False
                user.subscription_tier = "free"
            
            await db.commit()
    
    return {"received": True}


@router.get("/pricing")
async def get_pricing(request: Request):
    """Get current pricing with surge status"""
    
    surge_multiplier = getattr(request.state, 'surge_multiplier', 1.0)
    surge_active = surge_multiplier > 1.0
    
    pricing_with_surge = {}
    for plan_id, plan in PRICING.items():
        plan_copy = plan.copy()
        plan_copy["current_price"] = plan["price"] * surge_multiplier
        plan_copy["surge_active"] = surge_active
        pricing_with_surge[plan_id] = plan_copy
    
    return {
        "pricing": pricing_with_surge,
        "surge_active": surge_active,
        "surge_multiplier": surge_multiplier
    }


@router.get("/revenue/stats")
async def get_revenue_stats(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get revenue statistics (admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")
    
    # Get today's revenue
    today = datetime.utcnow().date()
    today_revenue = await db.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.status == "succeeded",
        func.date(Payment.created_at) == today
    ).scalar() or 0
    
    # Get total revenue
    total_revenue = await db.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.status == "succeeded"
    ).scalar() or 0
    
    # Get hourly revenue for chart
    hourly_revenue = await db.query(
        func.date_trunc('hour', Payment.created_at).label('hour'),
        func.sum(Payment.amount).label('revenue')
    ).filter(
        Payment.status == "succeeded",
        Payment.created_at >= datetime.utcnow() - timedelta(hours=24)
    ).group_by('hour').all()
    
    return {
        "today_revenue": today_revenue,
        "total_revenue": total_revenue,
        "target_revenue": 20000000,  # $20M target
        "progress_percentage": (total_revenue / 20000000) * 100,
        "hourly_revenue": [
            {"hour": h.hour.isoformat(), "revenue": h.revenue}
            for h in hourly_revenue
        ]
    }