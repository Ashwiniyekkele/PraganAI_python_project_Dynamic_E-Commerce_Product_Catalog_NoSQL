# Dynamic E-Commerce Product Catalog Using MongoDB
## Complete Reference: MongoDB Queries, Comparison Operators & Aggregation Pipelines

This technical reference documents every MongoDB query, operator, and aggregation pipeline implemented in the project with PyMongo syntax, pipeline stages, and expected outputs.

---

## 1. Comparison & Logical Query Operators

### 1.1 Equality & Non-Equality (`$eq`, `$ne`)
```python
# Find all products in category 'Groceries'
collection.find({"category": {"$eq": "Groceries"}})

# Find all products NOT belonging to 'Apparel'
collection.find({"category": {"$ne": "Apparel"}})
```

### 1.2 Price Range Queries (`$lt`, `$lte`, `$gt`, `$gte`)
```python
# Products priced strictly below ₹1,000 ($lt)
collection.find({"price": {"$lt": 1000}})

# Products with rating >= 4.5 ($gte) and stock <= 10 ($lte)
collection.find({
    "rating": {"$gte": 4.5},
    "stock": {"$lte": 10}
})
```

### 1.3 Set Inclusion Operators (`$in`, `$nin`)
```python
# Find products belonging to selected premium brands
collection.find({"brand": {"$in": ["Apple", "Sony", "Nike", "Organic India"]}})

# Find products whose category is not Groceries or Apparel
collection.find({"category": {"$nin": ["Groceries", "Apparel"]}})
```

### 1.4 Logical Compound Queries (`$and`, `$or`)
```python
# $and: Electronics items priced between ₹2,000 and ₹20,000 that are currently in stock
collection.find({
    "$and": [
        {"category": "Electronics"},
        {"price": {"$gte": 2000, "$lte": 20000}},
        {"stock": {"$gt": 0}}
    ]
})

# $or: Products that are top-rated (>= 4.8) OR currently out of stock (stock == 0)
collection.find({
    "$or": [
        {"rating": {"$gte": 4.8}},
        {"stock": 0}
    ]
})
```

### 1.5 Attribute Existence (`$exists`)
```python
# Check which products have a RAM attribute (strictly Electronics)
collection.find({"attributes.ram": {"$exists": True}})

# Check products without an expiry period (Apparel, Electronics)
collection.find({"attributes.expiry_months": {"$exists": False}})
```

---

## 2. Dynamic Nested Attribute Queries (Polymorphic Documents)

### 2.1 Groceries Nested Attributes
```python
# Query organic certified grocery products
collection.find({
    "category": "Groceries",
    "attributes.organic": True
})
```

### 2.2 Apparel Nested Attributes
```python
# Query Men's Cotton T-Shirts in Size 'L' or 'XL'
collection.find({
    "category": "Apparel",
    "attributes.material": "100% Combed Cotton",
    "attributes.gender": "Men",
    "attributes.size": {"$in": ["L", "XL"]}
})
```

### 2.3 Electronics Nested Attributes
```python
# Query Electronics with 16GB RAM and Bluetooth connectivity
collection.find({
    "category": "Electronics",
    "attributes.ram": "16GB",
    "attributes.connectivity": {"$regex": "Bluetooth", "$options": "i"}
})
```

---

## 3. Full-Text Search Using Compound Text Index (`$text`, `$search`)

### Index Creation
```python
collection.create_index(
    [("name", "text"), ("brand", "text"), ("description", "text")],
    name="idx_compound_text_search"
)
```

### Text Queries
```python
# Search for organic tea products
collection.find({"$text": {"$search": "organic tea"}})

# Search for wireless audio products
collection.find({"$text": {"$search": "wireless bluetooth earbuds"}})
```

---

## 4. The 10 Essential Aggregation Pipelines (Section 10)

### Report 1: Product Count by Category
```python
pipeline_r1 = [
    {"$group": {"_id": "$category", "product_count": {"$sum": 1}}},
    {"$sort": {"product_count": -1}}
]
```

### Report 2: Average Price by Category
```python
pipeline_r2 = [
    {"$group": {"_id": "$category", "avg_price": {"$avg": "$price"}}},
    {"$project": {"category": "$_id", "_id": 0, "avg_price": {"$round": ["$avg_price", 2]}}},
    {"$sort": {"avg_price": -1}}
]
```

### Report 3: Average Customer Rating by Category
```python
pipeline_r3 = [
    {"$group": {"_id": "$category", "avg_rating": {"$avg": "$rating"}}},
    {"$project": {"category": "$_id", "_id": 0, "avg_rating": {"$round": ["$avg_rating", 2]}}},
    {"$sort": {"avg_rating": -1}}
]
```

### Report 4: Brand-Wise Product Count
```python
pipeline_r4 = [
    {"$group": {"_id": "$brand", "count": {"$sum": 1}}},
    {"$sort": {"count": -1, "_id": 1}},
    {"$limit": 15}
]
```

### Report 5: Top-Rated Products
```python
pipeline_r5 = [
    {"$match": {"rating": {"$gte": 4.6}}},
    {"$sort": {"rating": -1, "reviews": -1}},
    {"$limit": 10},
    {"$project": {"_id": 0, "product_id": 1, "name": 1, "brand": 1, "rating": 1, "price": 1}}
]
```

### Report 6: Most Expensive Products
```python
pipeline_r6 = [
    {"$sort": {"price": -1}},
    {"$limit": 10},
    {"$project": {"_id": 0, "product_id": 1, "name": 1, "brand": 1, "category": 1, "price": 1}}
]
```

### Report 7: Total Inventory Valuation ($\text{Price} \times \text{Stock}$)
```python
pipeline_r7 = [
    {"$project": {"val": {"$multiply": ["$price", "$stock"]}}},
    {"$group": {"_id": None, "total_inventory_value": {"$sum": "$val"}}}
]
```

### Report 8: Low-Stock Products ($\text{Stock} \le 10$)
```python
pipeline_r8 = [
    {"$match": {"stock": {"$lte": 10}}},
    {"$sort": {"stock": 1}},
    {"$project": {"_id": 0, "product_id": 1, "name": 1, "category": 1, "stock": 1, "price": 1}}
]
```

### Report 9: Price Distribution Buckets (`$bucket`)
```python
pipeline_r9 = [
    {
        "$bucket": {
            "groupBy": "$price",
            "boundaries": [0, 500, 1500, 5000, 20000, 60000],
            "default": "60000+",
            "output": {
                "product_count": {"$sum": 1},
                "avg_price": {"$avg": "$price"}
            }
        }
    }
]
```

### Report 10: Category-Wise Inventory Value
```python
pipeline_r10 = [
    {
        "$group": {
            "_id": "$category",
            "total_units": {"$sum": "$stock"},
            "total_valuation": {"$sum": {"$multiply": ["$price", "$stock"]}},
            "avg_unit_price": {"$avg": "$price"}
        }
    },
    {
        "$project": {
            "category": "$_id",
            "_id": 0,
            "total_units": 1,
            "total_valuation": 1,
            "avg_unit_price": {"$round": ["$avg_unit_price", 2]}
        }
    },
    {"$sort": {"total_valuation": -1}}
]
```

---

## 5. Parallel Multi-Dimensional Faceted Search (`$facet`)

```python
pipeline_faceted_search = [
    # 1. Early filtering stage using $match
    {
        "$match": {
            "price": {"$lte": 25000},
            "rating": {"$gte": 4.0}
        }
    },
    # 2. Multi-faceted execution in one atomic database trip
    {
        "$facet": {
            "category_counts": [
                {"$sortByCount": "$category"}
            ],
            "brand_counts": [
                {"$sortByCount": "$brand"},
                {"$limit": 8}
            ],
            "price_buckets": [
                {
                    "$bucket": {
                        "groupBy": "$price",
                        "boundaries": [0, 500, 1500, 5000, 25000],
                        "default": "Other",
                        "output": {"count": {"$sum": 1}, "avg_price": {"$avg": "$price"}}
                    }
                }
            ],
            "rating_distribution": [
                {
                    "$bucket": {
                        "groupBy": "$rating",
                        "boundaries": [4.0, 4.3, 4.6, 5.1],
                        "default": "Other",
                        "output": {"count": {"$sum": 1}}
                    }
                }
            ],
            "matching_product_count": [
                {"$count": "total_matches"}
            ]
        }
    }
]

# Execute against collection
result = list(collection.aggregate(pipeline_faceted_search))[0]
```
