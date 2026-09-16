import asyncio
from datetime import date
from decimal import Decimal
from pydantic import BaseModel

from app.main import AffordabilityRequest, check_affordability
from core.models import UserProfile, BaseEvent, PurchaseRequest

async def main():
    req = AffordabilityRequest(
        mode="deterministic",
        profile=UserProfile(
            user_id="u1",
            home_currency="USD",
            minimum_balance_to_keep=Decimal("500.0")
        ),
        transactions=[
            BaseEvent(
                event_id="e1",
                user_id="u1",
                description="Salary",
                category="salary",
                amount=Decimal("5000.0"),
                currency="USD",
                event_date=date(2023, 10, 1),
                status="settled",
                event_type="income"
            ),
            BaseEvent(
                event_id="e2",
                user_id="u1",
                description="Rent",
                category="rent",
                amount=Decimal("2000.0"),
                currency="USD",
                event_date=date(2023, 10, 5),
                status="settled",
                event_type="expense"
            )
        ],
        purchase=PurchaseRequest(
            request_id="r1",
            user_id="u1",
            description="New Laptop",
            request_amount=Decimal("1500.0"),
            request_date=date(2023, 10, 10)
        )
    )
    
    res = await check_affordability(req)
    print(res.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
