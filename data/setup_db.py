import os
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Date, Numeric, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker
from faker import Faker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

Base = declarative_base()
fake = Faker()

# --- Models ---

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    region = Column(String)
    signup_date = Column(Date)
    tier = Column(String)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String)
    price = Column(Numeric(10, 2))
    cost = Column(Numeric(10, 2))

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    order_date = Column(Date)
    status = Column(String)
    total_amount = Column(Numeric(10, 2))

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    unit_price = Column(Numeric(10, 2))

class Return(Base):
    __tablename__ = 'returns'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    return_date = Column(Date)
    reason = Column(String)
    refund_amount = Column(Numeric(10, 2))

class MarketingSpend(Base):
    __tablename__ = 'marketing_spend'
    id = Column(Integer, primary_key=True)
    region = Column(String)
    month = Column(Date)
    channel = Column(String)
    amount_spent = Column(Numeric(10, 2))

# --- Seeding Logic ---

def seed_data(session):
    print("Seeding customers...")
    regions = ["East", "West", "North", "South"]
    tiers = ["Standard", "VIP"]
    customers = [Customer(
        name=fake.name(),
        email=fake.unique.email(),
        region=fake.random_element(regions),
        signup_date=fake.date_between(start_date='-3y', end_date='-1y'),
        tier=fake.random_element(tiers)
    ) for _ in range(200)]
    session.bulk_save_objects(customers)
    session.commit()

    print("Seeding products...")
    categories = ["Electronics", "Home", "Clothing", "Books", "Beauty"]
    products = []
    for _ in range(50):
        price = float(fake.random_int(min=10, max=500))
        products.append(Product(
            name=fake.catch_phrase(),
            category=fake.random_element(categories),
            price=Decimal(str(price)),
            cost=Decimal(str(price * 0.6))
        ))
    session.bulk_save_objects(products)
    session.commit()

    print("Seeding orders...")
    statuses = ["completed", "pending", "cancelled"]
    
    # Refresh customers to get IDs
    all_customers = session.query(Customer).all()
    top_customers = all_customers[:3]
    
    orders = []
    for i in range(1500):
        cust = fake.random_element(top_customers) if i < 300 else fake.random_element(all_customers)
        total_amount = float(fake.random_int(min=20, max=1000))
        if i == 42: total_amount = -100.0
        
        orders.append(Order(
            customer_id=cust.id,
            order_date=fake.date_between(start_date='-1y', end_date='today'),
            status=fake.random_element(statuses),
            total_amount=Decimal(str(total_amount))
        ))
    
    session.bulk_save_objects(orders)
    session.commit()

    print("Seeding order items...")
    all_orders = session.query(Order).all()
    all_products = session.query(Product).all()
    
    order_items = []
    for order in all_orders:
        for _ in range(fake.random_int(min=1, max=5)):
            prod = fake.random_element(all_products)
            order_items.append(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=fake.random_int(min=1, max=3),
                unit_price=prod.price
            ))
    session.bulk_save_objects(order_items)
    session.commit()

    print("Seeding returns...")
    completed_orders = session.query(Order).filter(Order.status == "completed").all()
    returns = [Return(
        order_id=o.id,
        return_date=o.order_date + timedelta(days=fake.random_int(1, 14)),
        reason=fake.sentence(),
        refund_amount=o.total_amount * Decimal('0.8')
    ) for o in completed_orders[:int(len(completed_orders)*0.1)]]
    session.bulk_save_objects(returns)
    session.commit()

    print("Seeding marketing spend...")
    channels = ["social", "search", "email", "affiliate"]
    marketing = []
    for region in regions:
        for month_offset in range(12):
            month_date = date(2025, 1, 1) + timedelta(days=month_offset*30)
            for channel in channels:
                amount = float(fake.random_int(min=100, max=1000))
                if region == "North": amount += (month_offset * 100)
                marketing.append(MarketingSpend(
                    region=region,
                    month=month_date,
                    channel=channel,
                    amount_spent=Decimal(str(amount))
                ))
    session.bulk_save_objects(marketing)
    session.commit()

def generate_manifest(engine):
    print("Generating schema_manifest.json...")
    manifest = {}
    with engine.connect() as conn:
        # Get tables
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()
        for table_row in tables:
            table_name = table_row[0]
            # Get columns
            columns = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")).fetchall()
            manifest[table_name] = {
                "columns": {col[0]: col[1] for col in columns},
                "relationships": []
            }
            
        # Hardcode relationships based on spec since extracting FKs from Postgres can be verbose
        manifest['orders']['relationships'].append({"column": "customer_id", "references": "customers.id"})
        manifest['order_items']['relationships'].append({"column": "order_id", "references": "orders.id"})
        manifest['order_items']['relationships'].append({"column": "product_id", "references": "products.id"})
        manifest['returns']['relationships'].append({"column": "order_id", "references": "orders.id"})
        # marketing_spend joined on region (implicit)
        manifest['marketing_spend']['relationships'].append({"column": "region", "references": "customers.region", "type": "implicit"})

    with open("data/schema_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("Manifest generated.")

if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    with Session() as session:
        seed_data(session)
    
    generate_manifest(engine)
    print("Phase 0 setup complete!")
