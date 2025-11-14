from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# --- Важно для фронтенда! ---
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- Настройка CORS ---
# Это позволит твоему другу (фронтенду) делать запросы к твоему API
# со своего компьютера (localhost)
origins = [
    "http://localhost",
    "http://localhost:8080", # Стандартный порт для Vue/React
    "http://localhost:3000", # Другой стандартный порт
    "http://127.0.0.1:5500", # Для Live Server в VS Code (если он просто html)
    # Добавь сюда адрес, с которого будет работать твой друг, если он другой
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Разрешаем эти источники
    allow_credentials=True,
    allow_methods=["*"], # Разрешаем все методы (GET, POST и т.д.)
    allow_headers=["*"], # Разрешаем все заголовки
)


# --- Модели данных (Pydantic) ---
# Так FastAPI будет проверять, что данные в запросе правильные

class Category(BaseModel):
    id: int
    name: str

class Product(BaseModel):
    id: int
    name: str
    price: float
    category_id: int # Связь с категорией

class CartItem(BaseModel): # Модель для добавления в корзину
    product_id: int
    quantity: int


# --- Наша "База данных" (просто списки) ---
# Позже ты заменишь это на PostgreSQL, SQLite и т.д.

db_categories = [
    Category(id=1, name="Электроника"),
    Category(id=2, name="Книги")
]

db_products = [
    Product(id=1, name="Смартфон", price=500.0, category_id=1),
    Product(id=2, name="Ноутбук", price=1200.0, category_id=1),
    Product(id=3, name="FastAPI для профи", price=45.0, category_id=2)
]

# Корзина будет словарем: {product_id: quantity}
db_cart = {}


# --- API Эндпоинты (Роуты) ---

@app.get("/")
def read_root():
    return {"message": "Привет! Это бэкенд для FastAPI проекта."}

# --- Категории ---
@app.get("/categories/", response_model=List[Category])
def get_categories():
    """Получить список всех категорий."""
    return db_categories

# --- Продукты ---
@app.get("/products/", response_model=List[Product])
def get_products(category_id: Optional[int] = None):
    """
    Получить список всех продуктов.
    Можно фильтровать по category_id, передав его как параметр.
    Пример: /products/?category_id=1
    """
    if category_id:
        # Возвращаем продукты только из этой категории
        return [p for p in db_products if p.category_id == category_id]
    # Иначе возвращаем все продукты
    return db_products

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    """
    Получить один продукт по его ID.
    """
    for p in db_products:
        if p.id == product_id:
            return p
    # Если не нашли, кидаем ошибку 404
    raise HTTPException(status_code=404, detail="Product not found")

# --- Корзина ---
@app.get("/cart/")
def get_cart():
    """
    Посмотреть содержимое корзины.
    Возвращает словарь {product_id: quantity}
    """
    return db_cart

@app.post("/cart/add")
def add_to_cart(item: CartItem):
    """
    Добавить товар в корзину.
    Тело запроса (JSON) должно быть: {"product_id": 1, "quantity": 1}
    """
    # 1. Проверяем, есть ли такой продукт
    product_exists = any(p.id == item.product_id for p in db_products)
    if not product_exists:
        raise HTTPException(status_code=404, detail="Product not found, cannot add to cart")

    # 2. Добавляем в корзину
    if item.product_id in db_cart:
        # Если товар уже есть, увеличиваем кол-во
        db_cart[item.product_id] += item.quantity
    else:
        # Если нет, добавляем
        db_cart[item.product_id] = item.quantity
    
    return {"message": "Product added to cart", "cart_state": db_cart}