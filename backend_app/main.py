# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="Мой магазин", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === JWT ===
SECRET_KEY = "change-me-in-production-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)  # ← ВОТ ЭТО ГЛАВНОЕ!

# === Модели с ПРИМЕРАМИ (чтобы не было "string") ===
class UserCreate(BaseModel):
    username: str = Field(..., example="alex")
    password: str = Field(..., example="123456")

class UserOut(BaseModel):
    username: str = Field(..., example="alex")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Category(BaseModel):
    id: int
    name: str

class Product(BaseModel):
    id: int
    name: str
    price: float
    category_id: int

class CartItem(BaseModel):
    product_id: int = Field(..., example=1)
    quantity: int = Field(1, ge=1, example=1)

class CartResponse(BaseModel):
    cart: Dict[int, int] = {}
    total_items: int = 0
    message: str = "Ok"

# === БД ===
db_users: Dict[str, str] = {}  # username → hashed_password
db_carts: Dict[str, Dict[int, int]] = {}

db_categories = [
    Category(id=1, name="Электроника"),
    Category(id=2, name="Книги")
]

db_products = [
    Product(id=1, name="Смартфон", price=50000, category_id=1),
    Product(id=2, name="Ноутбук", price=120000, category_id=1),
    Product(id=3, name="FastAPI для профи", price=2990, category_id=2),
]

# === Утилиты ===
def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, ALGORITHM)

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except:
        return None

# === Роуты ===
@app.post("/auth/register", response_model=UserOut)
async def register(user: UserCreate):
    if user.username in db_users:
        raise HTTPException(400, "Username already exists")
    db_users[user.username] = pwd_context.hash(user.password)
    return UserOut(username=user.username)

@app.post("/auth/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    hashed = db_users.get(form.username)
    if not hashed or not pwd_context.verify(form.password, hashed):
        raise HTTPException(401, "Incorrect username or password")
    token = create_token(form.username)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserOut)
async def me(username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(401, "Not authenticated")
    return UserOut(username=username)

@app.get("/categories/", response_model=List[Category])
def get_categories():
    return db_categories

@app.get("/products/", response_model=List[Product])
def get_products(category_id: Optional[int] = None):
    if category_id:
        return [p for p in db_products if p.category_id == category_id]
    return db_products

@app.get("/cart/", response_model=CartResponse)
async def get_cart(username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(401, "Login required")
    cart = db_carts.get(username, {})
    return CartResponse(cart=cart, total_items=sum(cart.values()))

@app.post("/cart/add", response_model=CartResponse)
async def add_to_cart(item: CartItem, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(401, "Login required")
    if not any(p.id == item.product_id for p in db_products):
        raise HTTPException(404, "Product not found")
    
    db_carts.setdefault(username, {})
    db_carts[username][item.product_id] = db_carts[username].get(item.product_id, 0) + item.quantity
    
    return CartResponse(
        cart=db_carts[username],
        total_items=sum(db_carts[username].values()),
        message="Added to cart"
    )

@app.post("/cart/clear")
async def clear_cart(username: str = Depends(get_current_user)):
    if username and username in db_carts:
        db_carts[username] = {}
    return {"message": "Cart cleared"}
