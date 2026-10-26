"""
Dynamic E-Commerce Product Catalog Using MongoDB
Dashboard Application built with Streamlit & PyMongo
Designed for Google Colab, Local Execution, and Render Deployment.
"""

import os
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import ConnectionFailure, DuplicateKeyError, PyMongoError

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==============================================================================
st.set_page_config(
    page_title="Dynamic E-Commerce Catalog | MongoDB",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for academic, professional theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 1.2rem;
        border-left: 4px solid #2563EB;
        margin-bottom: 1rem;
    }
    .metric-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stMetric {
        background-color: #F1F5F9;
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. DATABASE HELPER FUNCTIONS (MODULAR PYMONGO WRAPPERS)
# ==============================================================================
# ==============================================================================
# LOCAL DEMO IN-MEMORY MOCK ENGINE (FALLBACK WHEN ATLAS IS NOT YET CONNECTED)
# ==============================================================================
class MockCursor:
    def __init__(self, docs):
        self.docs = [d.copy() for d in docs]
    def sort(self, key, direction=1):
        reverse = (direction == -1)
        self.docs.sort(key=lambda x: (x.get(key) is None, x.get(key)), reverse=reverse)
        return self
    def limit(self, n):
        self.docs = self.docs[:n]
        return self
    def __iter__(self):
        return iter(self.docs)
    def __list__(self):
        return list(self.docs)

class MockResult:
    def __init__(self, inserted_id=None, inserted_ids=None, matched_count=0, modified_count=0, deleted_count=0):
        self.inserted_id = inserted_id or "mock_id"
        self.inserted_ids = inserted_ids or []
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.deleted_count = deleted_count

class MockCollection:
    """In-memory collection that adheres to PyMongo collection interface."""
    def __init__(self, initial_docs=None):
        self.docs = [dict(d) for d in (initial_docs or [])]
    def count_documents(self, query=None):
        return len(list(self.find(query)))
    def distinct(self, key):
        vals = set()
        for d in self.docs:
            if key in d:
                vals.add(d[key])
        return sorted(list(vals))
    def create_index(self, *args, **kwargs):
        return "mock_index_created"
    def _matches(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            if k == "$or":
                if not any(self._matches(doc, cond) for cond in v):
                    return False
            elif k == "$and":
                if not all(self._matches(doc, cond) for cond in v):
                    return False
            elif k == "$text":
                search = v.get("$search", "").lower()
                text_blob = f"{doc.get('name', '')} {doc.get('brand', '')} {doc.get('description', '')}".lower()
                if search not in text_blob:
                    return False
            elif "." in k:
                parts = k.split(".")
                curr = doc
                for p in parts:
                    if isinstance(curr, dict):
                        curr = curr.get(p)
                    else:
                        curr = None
                        break
                if isinstance(v, dict):
                    if "$exists" in v:
                        if v["$exists"] and curr is None:
                            return False
                        if not v["$exists"] and curr is not None:
                            return False
                elif curr != v:
                    return False
            elif isinstance(v, dict):
                curr = doc.get(k)
                for op, op_val in v.items():
                    if op == "$gt" and not (curr is not None and curr > op_val):
                        return False
                    elif op == "$gte" and not (curr is not None and curr >= op_val):
                        return False
                    elif op == "$lt" and not (curr is not None and curr < op_val):
                        return False
                    elif op == "$lte" and not (curr is not None and curr <= op_val):
                        return False
                    elif op == "$in" and curr not in op_val:
                        return False
                    elif op == "$nin" and curr in op_val:
                        return False
                    elif op == "$exists":
                        if op_val and curr is None:
                            return False
                        if not op_val and curr is not None:
                            return False
                    elif op == "$regex":
                        pattern = re.compile(op_val, re.IGNORECASE if v.get("$options") == "i" else 0)
                        if not (curr and pattern.search(str(curr))):
                            return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def find(self, query=None, projection=None):
        matched = [d for d in self.docs if self._matches(d, query)]
        return MockCursor(matched)

    def find_one(self, query=None, projection=None):
        for d in self.docs:
            if self._matches(d, query):
                return d.copy()
        return None

    def insert_one(self, doc):
        # Check uniqueness of product_id
        if any(d.get("product_id") == doc.get("product_id") for d in self.docs):
            raise DuplicateKeyError(f"Duplicate product_id: {doc.get('product_id')}")
        self.docs.append(doc.copy())
        return MockResult(inserted_id="mock_id_" + doc.get("product_id", "0"))

    def insert_many(self, docs, ordered=False):
        for d in docs:
            self.docs.append(d.copy())
        return MockResult(inserted_ids=["mock_id"] * len(docs))

    def update_one(self, query, update):
        target = None
        for d in self.docs:
            if self._matches(d, query):
                target = d
                break
        if not target:
            return MockResult(matched_count=0, modified_count=0)
        if "$set" in update:
            for k, v in update["$set"].items():
                if "." in k:
                    parts = k.split(".")
                    curr = target
                    for p in parts[:-1]:
                        curr = curr.setdefault(p, {})
                    curr[parts[-1]] = v
                else:
                    target[k] = v
        return MockResult(matched_count=1, modified_count=1)

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                del self.docs[i]
                return MockResult(deleted_count=1)
        return MockResult(deleted_count=0)

    def aggregate(self, pipeline):
        filtered_docs = self.docs
        for stage in pipeline:
            if "$match" in stage:
                filtered_docs = [d for d in filtered_docs if self._matches(d, stage["$match"])]

            if "$facet" in stage:
                facet_def = stage["$facet"]
                facet_res = {}
                for facet_name in facet_def:
                    if facet_name == "category_counts":
                        counts = {}
                        for d in filtered_docs:
                            c = d.get("category", "Unknown")
                            counts[c] = counts.get(c, 0) + 1
                        facet_res["category_counts"] = [{"_id": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
                    elif facet_name == "brand_counts":
                        counts = {}
                        for d in filtered_docs:
                            b = d.get("brand", "Unknown")
                            counts[b] = counts.get(b, 0) + 1
                        facet_res["brand_counts"] = [{"_id": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])[:10]]
                    elif facet_name == "price_buckets":
                        buckets = {"₹0 - ₹500": 0, "₹500 - ₹1,500": 0, "₹1,500 - ₹5,000": 0, "₹5,000 - ₹20,000": 0, "₹20,000 - ₹60,000": 0}
                        for d in filtered_docs:
                            p = d.get("price", 0)
                            if p < 500: buckets["₹0 - ₹500"] += 1
                            elif p < 1500: buckets["₹500 - ₹1,500"] += 1
                            elif p < 5000: buckets["₹1,500 - ₹5,000"] += 1
                            elif p < 20000: buckets["₹5,000 - ₹20,000"] += 1
                            else: buckets["₹20,000 - ₹60,000"] += 1
                        facet_res["price_buckets"] = [{"_id": k, "count": v} for k, v in buckets.items()]
                    elif facet_name == "rating_distribution":
                        r_buckets = {"< 4.0 ⭐": 0, "4.0 - 4.3 ⭐": 0, "4.3 - 4.6 ⭐": 0, "4.6 - 5.0 ⭐": 0}
                        for d in filtered_docs:
                            r = d.get("rating", 0)
                            if r < 4.0: r_buckets["< 4.0 ⭐"] += 1
                            elif r < 4.3: r_buckets["4.0 - 4.3 ⭐"] += 1
                            elif r < 4.6: r_buckets["4.3 - 4.6 ⭐"] += 1
                            else: r_buckets["4.6 - 5.0 ⭐"] += 1
                        facet_res["rating_distribution"] = [{"_id": k, "count": v} for k, v in r_buckets.items()]
                    elif facet_name == "matching_product_count":
                        facet_res["matching_product_count"] = [{"count": len(filtered_docs)}]
                    elif facet_name == "stock_status":
                        s_counts = {"Available (>10)": 0, "Low Stock (<=10)": 0, "Out of Stock": 0}
                        for d in filtered_docs:
                            st = d.get("stock", 0)
                            if st == 0: s_counts["Out of Stock"] += 1
                            elif st <= 10: s_counts["Low Stock (<=10)"] += 1
                            else: s_counts["Available (>10)"] += 1
                        facet_res["stock_status"] = [{"_id": k, "count": v} for k, v in s_counts.items()]
                return [facet_res]

            if "$group" in stage:
                grp = stage["$group"]
                if grp.get("_id") == "$category":
                    cats = {}
                    for d in filtered_docs:
                        c = d.get("category")
                        if c not in cats:
                            cats[c] = {"prods": [], "stock": 0, "val": 0}
                        cats[c]["prods"].append(d)
                        stk = d.get("stock", 0)
                        prc = d.get("price", 0)
                        cats[c]["stock"] += stk
                        cats[c]["val"] += stk * prc
                    res = []
                    for c, info in cats.items():
                        plist = info["prods"]
                        prices = [p.get("price", 0) for p in plist]
                        ratings = [p.get("rating", 0) for p in plist]
                        res.append({
                            "category": c,
                            "total_products": len(plist),
                            "avg_price": round(sum(prices)/len(prices), 2) if prices else 0,
                            "min_price": min(prices) if prices else 0,
                            "max_price": max(prices) if prices else 0,
                            "avg_rating": round(sum(ratings)/len(ratings), 2) if ratings else 0,
                            "total_stock": info["stock"],
                            "total_inventory_value": round(info["val"], 2)
                        })
                    return sorted(res, key=lambda x: -x["total_products"])

                elif grp.get("_id") == "$brand":
                    brands = {}
                    for d in filtered_docs:
                        b = d.get("brand")
                        if b not in brands:
                            brands[b] = []
                        brands[b].append(d)
                    res = []
                    for b, plist in brands.items():
                        prices = [p.get("price", 0) for p in plist]
                        ratings = [p.get("rating", 0) for p in plist]
                        res.append({
                            "brand": b,
                            "count": len(plist),
                            "avg_price": round(sum(prices)/len(prices), 2) if prices else 0,
                            "avg_rating": round(sum(ratings)/len(ratings), 2) if ratings else 0
                        })
                    return sorted(res, key=lambda x: -x["count"])[:15]

                elif grp.get("_id") is None:
                    tot_stk = sum(d.get("stock", 0) for d in filtered_docs)
                    tot_val = sum(d.get("price", 0) * d.get("stock", 0) for d in filtered_docs)
                    low_cnt = sum(1 for d in filtered_docs if 0 < d.get("stock", 0) <= 10)
                    out_cnt = sum(1 for d in filtered_docs if d.get("stock", 0) == 0)
                    return [{
                        "total_stock": tot_stk,
                        "total_inventory_val": tot_val,
                        "low_stock_count": low_cnt,
                        "out_of_stock_count": out_cnt,
                        "total_items": len(filtered_docs),
                        "avg_price": round(sum(d.get("price", 0) for d in filtered_docs)/len(filtered_docs), 2) if filtered_docs else 0,
                        "avg_rating": round(sum(d.get("rating", 0) for d in filtered_docs)/len(filtered_docs), 2) if filtered_docs else 0
                    }]
        return []

DB_NAME = "ecommerce_catalog"
COLLECTION_NAME = "products"

@st.cache_resource(show_spinner=False)
def connect_to_mongodb(uri: str):
    """
    Connects to MongoDB Atlas cluster and returns client, db, and collection.
    Cached resource prevents reconnections on each Streamlit rerun.
    """
    if not uri or not uri.startswith("mongodb"):
        return None, None, None, "Invalid or missing MongoDB URI."
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Verify connection
        client.admin.command("ping")
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        return client, db, collection, "Connection successful."
    except ConnectionFailure as ce:
        return None, None, None, f"Connection Failure: {str(ce)}"
    except PyMongoError as pe:
        return None, None, None, f"MongoDB Error: {str(pe)}"
    except Exception as e:
        return None, None, None, f"Unexpected Error: {str(e)}"

def create_indexes(collection) -> List[str]:
    """Creates required indexes on the products collection."""
    results = []
    try:
        # Unique index on product_id
        collection.create_index([("product_id", ASCENDING)], unique=True, name="idx_product_id_unique")
        results.append("Unique index on 'product_id' ensured.")
        # Single field indexes
        collection.create_index([("category", ASCENDING)], name="idx_category")
        collection.create_index([("brand", ASCENDING)], name="idx_brand")
        collection.create_index([("price", ASCENDING)], name="idx_price")
        collection.create_index([("rating", ASCENDING)], name="idx_rating")
        results.append("Single-field indexes on 'category', 'brand', 'price', 'rating' ensured.")
        # Text index for search
        collection.create_index(
            [("name", TEXT), ("brand", TEXT), ("description", TEXT)],
            name="idx_text_search"
        )
        results.append("Compound Text index on ('name', 'brand', 'description') ensured.")
    except Exception as e:
        results.append(f"Index creation notice: {str(e)}")
    return results

def insert_product(collection, product_doc: Dict[str, Any]) -> Tuple[bool, str]:
    """Inserts a single product document with validation."""
    try:
        if not product_doc.get("product_id"):
            return False, "Validation Error: Product ID is required."
        if not product_doc.get("name"):
            return False, "Validation Error: Product Name cannot be empty."
        if product_doc.get("price", 0) < 0:
            return False, "Validation Error: Price cannot be negative."
        if product_doc.get("stock", 0) < 0:
            return False, "Validation Error: Stock cannot be negative."
        if not (0 <= product_doc.get("rating", 0) <= 5.0):
            return False, "Validation Error: Rating must be between 0.0 and 5.0."

        res = collection.insert_one(product_doc)
        return True, f"Product '{product_doc['product_id']}' added with _id: {res.inserted_id}"
    except DuplicateKeyError:
        return False, f"Duplicate Error: Product ID '{product_doc.get('product_id')}' already exists in database."
    except Exception as e:
        return False, f"Insertion Failed: {str(e)}"

def insert_many_products(collection, products: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Bulk inserts sample products."""
    try:
        res = collection.insert_many(products, ordered=False)
        return True, f"Successfully inserted {len(res.inserted_ids)} products."
    except PyMongoError as pe:
        return False, f"Bulk insert encountered an issue: {str(pe)}"

def get_products(collection, query: Optional[Dict[str, Any]] = None, sort_field: str = "product_id", sort_asc: bool = True, limit: int = 500) -> List[Dict[str, Any]]:
    """Retrieves products matching query and returns clean list without ObjectId serialization issues."""
    if query is None:
        query = {}
    direction = ASCENDING if sort_asc else -1
    cursor = collection.find(query).sort(sort_field, direction).limit(limit)
    docs = list(cursor)
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"])
    return docs

def get_product_by_id(collection, product_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by product_id."""
    doc = collection.find_one({"product_id": product_id})
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def search_products(collection, search_term: str) -> List[Dict[str, Any]]:
    """Searches products using text index or regex fallback."""
    if not search_term or not search_term.strip():
        return get_products(collection)
    search_term = search_term.strip()
    try:
        # First attempt text index
        cursor = collection.find({"$text": {"$search": search_term}}).limit(100)
        docs = list(cursor)
        if docs:
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
    except Exception:
        pass
    # Regex fallback across name, brand, category, description
    regex = {"$regex": search_term, "$options": "i"}
    query = {
        "$or": [
            {"name": regex},
            {"brand": regex},
            {"category": regex},
            {"description": regex}
        ]
    }
    return get_products(collection, query=query)

def filter_products(collection, category: Optional[str] = None, brand: Optional[str] = None,
                    min_price: float = 0, max_price: float = 1000000,
                    min_rating: float = 0, in_stock_only: bool = False) -> List[Dict[str, Any]]:
    """Constructs dynamic query filter directly on MongoDB."""
    q: Dict[str, Any] = {
        "price": {"$gte": min_price, "$lte": max_price},
        "rating": {"$gte": min_rating}
    }
    if category and category != "All":
        q["category"] = category
    if brand and brand != "All":
        q["brand"] = brand
    if in_stock_only:
        q["stock"] = {"$gt": 0}
    return get_products(collection, query=q)

def update_product(collection, product_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, str]:
    """Updates product fields using $set."""
    try:
        res = collection.update_one({"product_id": product_id}, {"$set": update_fields})
        if res.matched_count == 0:
            return False, f"Product ID '{product_id}' not found."
        return True, f"Product '{product_id}' updated successfully. (Modified: {res.modified_count})"
    except Exception as e:
        return False, f"Update failed: {str(e)}"

def delete_product(collection, product_id: str) -> Tuple[bool, str]:
    """Deletes a product by product_id."""
    try:
        res = collection.delete_one({"product_id": product_id})
        if res.deleted_count == 0:
            return False, f"Product ID '{product_id}' not found."
        return True, f"Product '{product_id}' deleted successfully."
    except Exception as e:
        return False, f"Deletion failed: {str(e)}"

def get_category_statistics(collection) -> List[Dict[str, Any]]:
    """Aggregation pipeline: Category-wise stats ($group, $sort, $project)."""
    pipeline = [
        {
            "$group": {
                "_id": "$category",
                "total_products": {"$sum": 1},
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"},
                "avg_rating": {"$avg": "$rating"},
                "total_stock": {"$sum": "$stock"},
                "total_inventory_value": {"$sum": {"$multiply": ["$price", "$stock"]}}
            }
        },
        {"$sort": {"total_products": -1}},
        {
            "$project": {
                "category": "$_id",
                "_id": 0,
                "total_products": 1,
                "avg_price": {"$round": ["$avg_price", 2]},
                "min_price": 1,
                "max_price": 1,
                "avg_rating": {"$round": ["$avg_rating", 2]},
                "total_stock": 1,
                "total_inventory_value": {"$round": ["$total_inventory_value", 2]}
            }
        }
    ]
    return list(collection.aggregate(pipeline))

def get_brand_statistics(collection) -> List[Dict[str, Any]]:
    """Aggregation pipeline: Brand-wise distribution."""
    pipeline = [
        {
            "$group": {
                "_id": "$brand",
                "count": {"$sum": 1},
                "avg_price": {"$avg": "$price"},
                "avg_rating": {"$avg": "$rating"}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 15},
        {
            "$project": {
                "brand": "$_id",
                "_id": 0,
                "count": 1,
                "avg_price": {"$round": ["$avg_price", 2]},
                "avg_rating": {"$round": ["$avg_rating", 2]}
            }
        }
    ]
    return list(collection.aggregate(pipeline))

def get_faceted_results(collection, match_query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Aggregation pipeline utilizing $match and $facet stages.
    Executes multiple multi-faceted search filters in a single atomic database trip.
    """
    pipeline: List[Dict[str, Any]] = []
    if match_query:
        pipeline.append({"$match": match_query})

    pipeline.append({
        "$facet": {
            "category_counts": [
                {"$sortByCount": "$category"}
            ],
            "brand_counts": [
                {"$sortByCount": "$brand"},
                {"$limit": 10}
            ],
            "price_buckets": [
                {
                    "$bucket": {
                        "groupBy": "$price",
                        "boundaries": [0, 500, 1500, 5000, 20000, 60000],
                        "default": "60000+",
                        "output": {
                            "count": {"$sum": 1},
                            "avg_price": {"$avg": "$price"}
                        }
                    }
                }
            ],
            "rating_distribution": [
                {
                    "$bucket": {
                        "groupBy": "$rating",
                        "boundaries": [0.0, 4.0, 4.3, 4.6, 5.1],
                        "default": "Other",
                        "output": {"count": {"$sum": 1}}
                    }
                }
            ],
            "matching_product_count": [
                {"$count": "count"}
            ],
            "stock_status": [
                {
                    "$project": {
                        "status": {
                            "$cond": [
                                {"$eq": ["$stock", 0]},
                                "Out of Stock",
                                {"$cond": [{"$lte": ["$stock", 10]}, "Low Stock (<=10)", "Available (>10)"]}
                            ]
                        }
                    }
                },
                {"$sortByCount": "$status"}
            ]
        }
    })

    result = list(collection.aggregate(pipeline))
    return result[0] if result else {}

def get_inventory_statistics(collection) -> Dict[str, Any]:
    """Aggregates inventory KPIs: Total stock, low stock, out of stock, valuation."""
    pipeline = [
        {
            "$project": {
                "price": 1,
                "stock": 1,
                "val": {"$multiply": ["$price", "$stock"]},
                "is_low": {"$cond": [{"$and": [{"$gt": ["$stock", 0]}, {"$lte": ["$stock", 10]}]}, 1, 0]},
                "is_out": {"$cond": [{"$eq": ["$stock", 0]}, 1, 0]}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_stock": {"$sum": "$stock"},
                "total_inventory_val": {"$sum": "$val"},
                "low_stock_count": {"$sum": "$is_low"},
                "out_of_stock_count": {"$sum": "$is_out"},
                "total_items": {"$sum": 1}
            }
        }
    ]
    res = list(collection.aggregate(pipeline))
    if res:
        return res[0]
    return {
        "total_stock": 0,
        "total_inventory_val": 0,
        "low_stock_count": 0,
        "out_of_stock_count": 0,
        "total_items": 0
    }

def load_local_sample_data() -> List[Dict[str, Any]]:
    """Loads sample products from local fallback file if available."""
    json_path = os.path.join(os.path.dirname(__file__), "data", "sample_products.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ==============================================================================
# 3. SIDEBAR NAVIGATION & CONNECTION MANAGEMENT
# ==============================================================================
st.sidebar.title("🛒 E-Commerce Catalog")
st.sidebar.caption("NoSQL Dynamic Product Catalog • MongoDB Atlas")

# URI input (Supports Environment Variable or Manual Colab Input)
default_uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI", "")
mongo_uri = st.sidebar.text_input(
    "MongoDB Atlas Connection URI",
    value=default_uri,
    type="password",
    help="Enter your mongodb+srv://<user>:<password>@cluster.mongodb.net URI. Password is kept safe."
)

client, db, collection, conn_msg = None, None, None, ""

if mongo_uri:
    client, db, collection, conn_msg = connect_to_mongodb(mongo_uri)
    if client:
        st.sidebar.success("✅ Connected to MongoDB Atlas Cloud")
    else:
        st.sidebar.error(f"❌ {conn_msg}")

if collection is None:
    if "mock_collection" not in st.session_state:
        st.session_state["mock_collection"] = MockCollection(load_local_sample_data())
    collection = st.session_state["mock_collection"]
    st.sidebar.info("🚀 **Demo Mode Active** (50 sample products loaded). To connect to cloud database, paste your MongoDB Atlas URI above.")

# Quick Seeding helper in sidebar
if collection is not None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Database Utilities")
    col_a, col_b = st.sidebar.columns(2)
    if col_a.button("Seed 50 Items", help="Populate sample dataset"):
        sample_items = load_local_sample_data()
        if sample_items:
            # Check existing count
            existing_count = collection.count_documents({})
            if existing_count == 0:
                success, msg = insert_many_products(collection, sample_items)
                create_indexes(collection)
                st.sidebar.success(msg)
                st.rerun()
            else:
                st.sidebar.warning(f"Database already contains {existing_count} items.")
        else:
            st.sidebar.error("Local sample data file not found.")

    if col_b.button("Ensure Indexes", help="Create unique, category, and text indexes"):
        res = create_indexes(collection)
        for r in res:
            st.sidebar.caption(r)
        st.sidebar.success("Indexes checked!")

# Navigation Menu
st.sidebar.markdown("---")
menu_selection = st.sidebar.radio(
    "Navigation Menu",
    [
        "1. Dashboard",
        "2. Product Catalog",
        "3. Add Product",
        "4. Update Product",
        "5. Delete Product",
        "6. Search & Filters",
        "7. Faceted Search ($facet)",
        "8. Analytics",
        "9. MongoDB Queries Live",
        "10. Export Data (CSV)",
        "11. About Project"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Academic Project • Python, PyMongo & Streamlit")


# ==============================================================================
# 4. VIEW LOGIC FOR EACH MENU OPTION
# ==============================================================================

# Helper for connection check
def ensure_db():
    return True


# ------------------------------------------------------------------------------
# 1. DASHBOARD PAGE
# ------------------------------------------------------------------------------
if menu_selection == "1. Dashboard":
    st.markdown('<div class="main-header">Dynamic E-Commerce Product Catalog</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Schema-Agnostic NoSQL Product Catalog with MongoDB Atlas & Streamlit</div>', unsafe_allow_html=True)

    if ensure_db():
        # Top KPI Cards
        total_products = collection.count_documents({})
        categories_count = len(collection.distinct("category"))
        brands_count = len(collection.distinct("brand"))

        inv_stats = get_inventory_statistics(collection)
        total_stock = inv_stats.get("total_stock", 0)
        total_val = inv_stats.get("total_inventory_val", 0)
        low_stock_count = inv_stats.get("low_stock_count", 0)

        # Average price and rating
        avg_res = list(collection.aggregate([
            {"$group": {"_id": None, "avg_price": {"$avg": "$price"}, "avg_rating": {"$avg": "$rating"}}}
        ]))
        avg_price = avg_res[0]["avg_price"] if avg_res else 0
        avg_rating = avg_res[0]["avg_rating"] if avg_res else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Total Products", f"{total_products}")
        c2.metric("🏷️ Categories", f"{categories_count}")
        c3.metric("🏢 Distinct Brands", f"{brands_count}")
        c4.metric("💰 Avg Price", f"₹{avg_price:,.2f}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("⭐ Avg Rating", f"{avg_rating:.2f} / 5.0")
        c6.metric("📊 Total Units in Stock", f"{total_stock:,}")
        c7.metric("💵 Total Inventory Value", f"₹{total_val:,.2f}")
        c8.metric("⚠️ Low Stock (<10)", f"{low_stock_count}", delta="-Critical" if low_stock_count > 0 else "Optimal", delta_color="inverse")

        st.markdown("---")

        # Quick Highlights Grid
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Category Breakdown")
            cat_stats = get_category_statistics(collection)
            if cat_stats:
                df_cat = pd.DataFrame(cat_stats)
                fig_cat = px.pie(
                    df_cat,
                    names="category",
                    values="total_products",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_cat.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No category data available yet.")

        with col_right:
            st.subheader("Inventory Valuation by Category")
            if cat_stats:
                df_cat = pd.DataFrame(cat_stats)
                fig_val = px.bar(
                    df_cat,
                    x="category",
                    y="total_inventory_value",
                    text_auto=True,
                    color="category",
                    labels={"total_inventory_value": "Inventory Value (₹)", "category": "Category"}
                )
                fig_val.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_val, use_container_width=True)

        # Highlight recent/featured products
        st.subheader("Recent Catalog Additions")
        recent_items = get_products(collection, sort_field="created_at", sort_asc=False, limit=6)
        if recent_items:
            df_recent = pd.DataFrame(recent_items)[["product_id", "name", "brand", "category", "price", "stock", "rating"]]
            st.dataframe(df_recent, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------------------
# 2. PRODUCT CATALOG
# ------------------------------------------------------------------------------
elif menu_selection == "2. Product Catalog":
    st.markdown('<div class="main-header">Product Catalog</div>', unsafe_allow_html=True)
    st.caption("Browse, sort, and inspect documents stored in MongoDB Atlas.")

    if ensure_db():
        # Top filters for browsing
        f1, f2, f3, f4 = st.columns(4)
        cat_list = ["All"] + sorted(collection.distinct("category"))
        sel_cat = f1.selectbox("Filter Category", cat_list)

        brand_list = ["All"] + sorted(collection.distinct("brand"))
        sel_brand = f2.selectbox("Filter Brand", brand_list)

        sort_col = f3.selectbox("Sort By", ["product_id", "price", "rating", "stock", "name"])
        sort_order = f4.selectbox("Order", ["Ascending", "Descending"])

        # Fetch products
        query = {}
        if sel_cat != "All":
            query["category"] = sel_cat
        if sel_brand != "All":
            query["brand"] = sel_brand

        docs = get_products(collection, query=query, sort_field=sort_col, sort_asc=(sort_order == "Ascending"))

        st.write(f"Showing **{len(docs)}** products")

        if docs:
            # Flatten table for visual presentation
            table_rows = []
            for d in docs:
                table_rows.append({
                    "Product ID": d.get("product_id"),
                    "Name": d.get("name"),
                    "Brand": d.get("brand"),
                    "Category": d.get("category"),
                    "Subcategory": d.get("subcategory"),
                    "Price (₹)": f"₹{d.get('price', 0):,.2f}",
                    "Stock": d.get("stock"),
                    "Rating": f"⭐ {d.get('rating')}",
                    "Reviews": d.get("reviews", 0),
                    "Attributes Count": len(d.get("attributes", {}))
                })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            # Detail expander
            st.markdown("### Document Inspector (Inspect Dynamic Nested Attributes)")
            selected_pid = st.selectbox("Select Product to Inspect Document Schema", [d["product_id"] for d in docs])
            if selected_pid:
                selected_doc = get_product_by_id(collection, selected_pid)
                st.json(selected_doc)


# ------------------------------------------------------------------------------
# 3. ADD PRODUCT
# ------------------------------------------------------------------------------
elif menu_selection == "3. Add Product":
    st.markdown('<div class="main-header">Add New Product</div>', unsafe_allow_html=True)
    st.caption("Demonstrates schema flexibility: different categories receive completely distinct nested attributes.")

    if ensure_db():
        with st.form("add_product_form", clear_on_submit=False):
            st.subheader("1. General Core Information")
            c1, c2, c3 = st.columns(3)
            pid = c1.text_input("Product ID *", placeholder="e.g. P051").strip()
            name = c2.text_input("Product Name *", placeholder="e.g. Wireless Mouse").strip()
            brand = c3.text_input("Brand *", placeholder="e.g. Logitech").strip()

            c4, c5 = st.columns(2)
            category = c4.selectbox("Category *", ["Groceries", "Apparel", "Electronics", "Home & Kitchen", "Other"])
            subcategory = c5.text_input("Subcategory", placeholder="e.g. Accessories / Cookware").strip()

            c6, c7, c8 = st.columns(3)
            price = c6.number_input("Price (₹) *", min_value=0.0, value=999.0, step=10.0)
            stock = c7.number_input("Stock Units *", min_value=0, value=25, step=1)
            rating = c8.slider("Initial Rating", min_value=0.0, max_value=5.0, value=4.5, step=0.1)

            reviews = st.number_input("Initial Reviews Count", min_value=0, value=10, step=1)
            desc = st.text_area("Description", placeholder="Enter comprehensive product description...")

            st.markdown("---")
            st.subheader("2. Category-Specific Dynamic Attributes (Nested Document)")
            st.info(f"Fields below dynamically adapt to the selected category: **{category}**")

            dyn_attrs = {}

            if category == "Groceries":
                g1, g2, g3 = st.columns(3)
                dyn_attrs["weight"] = g1.text_input("Weight / Volume", value="1 kg")
                dyn_attrs["organic"] = g2.checkbox("Certified Organic", value=False)
                dyn_attrs["expiry_months"] = g3.number_input("Shelf Life (Months)", min_value=1, value=12)

            elif category == "Apparel":
                a1, a2, a3, a4 = st.columns(4)
                dyn_attrs["size"] = a1.selectbox("Size", ["XS", "S", "M", "L", "XL", "XXL", "Free Size"])
                dyn_attrs["color"] = a2.text_input("Color", value="Navy Blue")
                dyn_attrs["material"] = a3.text_input("Material", value="100% Cotton")
                dyn_attrs["gender"] = a4.selectbox("Gender", ["Men", "Women", "Unisex", "Kids"])

            elif category == "Electronics":
                e1, e2, e3 = st.columns(3)
                dyn_attrs["ram"] = e1.text_input("RAM", value="8GB")
                dyn_attrs["storage"] = e2.text_input("Storage", value="128GB")
                dyn_attrs["battery"] = e3.text_input("Battery Life", value="5000 mAh")

                e4, e5 = st.columns(2)
                dyn_attrs["connectivity"] = e4.text_input("Connectivity", value="Bluetooth 5.3 / Wi-Fi")
                dyn_attrs["warranty"] = e5.text_input("Warranty", value="1 Year")

            elif category == "Home & Kitchen":
                h1, h2, h3 = st.columns(3)
                dyn_attrs["capacity"] = h1.text_input("Capacity", value="3 Litres")
                dyn_attrs["material"] = h2.text_input("Material", value="Stainless Steel")
                dyn_attrs["wattage"] = h3.text_input("Wattage / Power", value="750 Watts")

                h4, h5 = st.columns(2)
                dyn_attrs["dishwasher_safe"] = h4.checkbox("Dishwasher Safe", value=True)
                dyn_attrs["warranty"] = h5.text_input("Warranty", value="2 Years")

            else:
                st.caption("Enter arbitrary key-value attributes as valid JSON:")
                custom_json = st.text_area("Custom Attributes (JSON format)", value='{"model": "2026", "color": "Grey"}')
                try:
                    dyn_attrs = json.loads(custom_json)
                except Exception:
                    dyn_attrs = {}

            submitted = st.form_submit_button("Add Product to MongoDB Atlas", use_container_width=True)

            if submitted:
                new_doc = {
                    "product_id": pid,
                    "name": name,
                    "brand": brand,
                    "category": category,
                    "subcategory": subcategory,
                    "price": float(price),
                    "stock": int(stock),
                    "rating": float(rating),
                    "reviews": int(reviews),
                    "description": desc,
                    "attributes": dyn_attrs,
                    "created_at": datetime.datetime.now().isoformat()
                }
                success, msg = insert_product(collection, new_doc)
                if success:
                    st.success(f"🎉 {msg}")
                    st.json(new_doc)
                else:
                    st.error(f"⚠️ {msg}")


# ------------------------------------------------------------------------------
# 4. UPDATE PRODUCT
# ------------------------------------------------------------------------------
elif menu_selection == "4. Update Product":
    st.markdown('<div class="main-header">Update Product</div>', unsafe_allow_html=True)
    st.caption("Update product pricing, stock availability, rating, or nested attributes.")

    if ensure_db():
        all_ids = [d["product_id"] for d in get_products(collection, sort_field="product_id")]
        if not all_ids:
            st.info("No products found in the catalog to update.")
        else:
            sel_pid = st.selectbox("Select Product ID to Edit", all_ids)
            target = get_product_by_id(collection, sel_pid)

            if target:
                st.markdown(f"**Editing:** {target.get('name')} (*{target.get('brand')}* - {target.get('category')})")

                with st.form("update_form"):
                    u1, u2 = st.columns(2)
                    new_name = u1.text_input("Product Name", value=target.get("name", ""))
                    new_brand = u2.text_input("Brand", value=target.get("brand", ""))

                    u3, u4, u5 = st.columns(3)
                    new_price = u3.number_input("Price (₹)", min_value=0.0, value=float(target.get("price", 0.0)))
                    new_stock = u4.number_input("Stock", min_value=0, value=int(target.get("stock", 0)))
                    new_rating = u5.slider("Rating", min_value=0.0, max_value=5.0, value=float(target.get("rating", 0.0)))

                    new_desc = st.text_area("Description", value=target.get("description", ""))

                    st.markdown("**Nested Attributes (JSON Editor)**")
                    current_attrs_json = json.dumps(target.get("attributes", {}), indent=2)
                    new_attrs_raw = st.text_area("Edit Attributes JSON directly:", value=current_attrs_json, height=120)

                    upd_submitted = st.form_submit_button("Update Product (update_one)", use_container_width=True)

                    if upd_submitted:
                        try:
                            parsed_attrs = json.loads(new_attrs_raw)
                        except Exception as e:
                            st.error(f"Invalid JSON format for attributes: {e}")
                            parsed_attrs = target.get("attributes", {})

                        update_fields = {
                            "name": new_name,
                            "brand": new_brand,
                            "price": float(new_price),
                            "stock": int(new_stock),
                            "rating": float(new_rating),
                            "description": new_desc,
                            "attributes": parsed_attrs,
                            "updated_at": datetime.datetime.now().isoformat()
                        }
                        success, msg = update_product(collection, sel_pid, update_fields)
                        if success:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")


# ------------------------------------------------------------------------------
# 5. DELETE PRODUCT
# ------------------------------------------------------------------------------
elif menu_selection == "5. Delete Product":
    st.markdown('<div class="main-header">Delete Product</div>', unsafe_allow_html=True)
    st.caption("Remove a product document permanently from MongoDB Atlas collection.")

    if ensure_db():
        all_ids = [d["product_id"] for d in get_products(collection, sort_field="product_id")]
        if not all_ids:
            st.info("No products found in the catalog.")
        else:
            del_pid = st.selectbox("Select Product ID to Delete", all_ids)
            doc_to_delete = get_product_by_id(collection, del_pid)

            if doc_to_delete:
                st.warning(f"Are you sure you want to delete **{doc_to_delete.get('name')}** (`{del_pid}`)?")
                st.json({
                    "product_id": doc_to_delete.get("product_id"),
                    "name": doc_to_delete.get("name"),
                    "category": doc_to_delete.get("category"),
                    "price": doc_to_delete.get("price"),
                    "stock": doc_to_delete.get("stock")
                })

                confirm = st.checkbox("I confirm that I want to delete this document permanently.")
                if st.button("Delete Product (delete_one)", type="primary"):
                    if confirm:
                        success, msg = delete_product(collection, del_pid)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Please tick the confirmation checkbox first.")


# ------------------------------------------------------------------------------
# 6. SEARCH & FILTERS
# ------------------------------------------------------------------------------
elif menu_selection == "6. Search & Filters":
    st.markdown('<div class="main-header">Search & Multi-Condition Filters</div>', unsafe_allow_html=True)
    st.caption("Directly executes MongoDB queries using comparison, range, and text operators.")

    if ensure_db():
        search_kw = st.text_input("🔍 Search by Name, Brand, Category, or Description (MongoDB $text / $regex)", placeholder="e.g. Wireless, Cotton, Rice, Sony...")

        st.markdown("#### Filter Criteria")
        col_f1, col_f2, col_f3 = st.columns(3)
        cat_choices = ["All"] + sorted(collection.distinct("category"))
        sel_c = col_f1.selectbox("Category", cat_choices)

        brand_choices = ["All"] + sorted(collection.distinct("brand"))
        sel_b = col_f2.selectbox("Brand", brand_choices)

        stock_filter = col_f3.selectbox("Stock Filter", ["All Items", "In Stock Only (>0)", "Low Stock (<=10)"])

        col_f4, col_f5 = st.columns(2)
        price_range = col_f4.slider("Price Range (₹)", min_value=0, max_value=60000, value=(0, 60000), step=500)
        min_rat = col_f5.slider("Minimum Rating (⭐)", min_value=0.0, max_value=5.0, value=0.0, step=0.1)

        # Dynamic query generation
        if search_kw:
            filtered_results = search_products(collection, search_kw)
            # Post filter on search results for UI convenience
            final_docs = []
            for d in filtered_results:
                if sel_c != "All" and d.get("category") != sel_c:
                    continue
                if sel_b != "All" and d.get("brand") != sel_b:
                    continue
                if not (price_range[0] <= d.get("price", 0) <= price_range[1]):
                    continue
                if d.get("rating", 0) < min_rat:
                    continue
                if stock_filter == "In Stock Only (>0)" and d.get("stock", 0) <= 0:
                    continue
                if stock_filter == "Low Stock (<=10)" and (d.get("stock", 0) <= 0 or d.get("stock", 0) > 10):
                    continue
                final_docs.append(d)
        else:
            in_stock_bool = (stock_filter == "In Stock Only (>0)")
            final_docs = filter_products(
                collection,
                category=sel_c,
                brand=sel_b,
                min_price=float(price_range[0]),
                max_price=float(price_range[1]),
                min_rating=float(min_rat),
                in_stock_only=in_stock_bool
            )
            if stock_filter == "Low Stock (<=10)":
                final_docs = [d for d in final_docs if 0 < d.get("stock", 0) <= 10]

        st.success(f"Matched **{len(final_docs)}** products.")

        if final_docs:
            for item in final_docs:
                with st.expander(f"{item.get('name')} — ₹{item.get('price'):,.2f} ({item.get('brand')} | ⭐ {item.get('rating')})"):
                    c_left, c_right = st.columns([2, 1])
                    c_left.write(f"**Description:** {item.get('description')}")
                    c_left.write(f"**Category:** {item.get('category')} > {item.get('subcategory')}")
                    c_left.write(f"**Stock Available:** {item.get('stock')} units")
                    c_right.markdown("**Dynamic Attributes:**")
                    c_right.json(item.get("attributes", {}))


# ------------------------------------------------------------------------------
# 7. FACETED SEARCH ($facet)
# ------------------------------------------------------------------------------
elif menu_selection == "7. Faceted Search ($facet)":
    st.markdown('<div class="main-header">High-Performance Faceted Search ($facet)</div>', unsafe_allow_html=True)
    st.info("""
    **Core Requirement Highlight:** This page demonstrates MongoDB's `$facet` aggregation stage.
    Instead of making 4 separate queries to count categories, brands, price buckets, and rating distributions,
    MongoDB processes all sub-pipelines **in parallel in a single atomic database round-trip**!
    """)

    if ensure_db():
        st.subheader("1. Active Search / Match Filter")
        c1, c2 = st.columns(2)
        target_cat = c1.selectbox("Filter by Category (Optional $match stage)", ["All"] + sorted(collection.distinct("category")))
        min_rat = c2.slider("Filter by Rating ($gte)", min_value=0.0, max_value=5.0, value=0.0, step=0.1)

        match_stage = {}
        if target_cat != "All":
            match_stage["category"] = target_cat
        if min_rat > 0.0:
            match_stage["rating"] = {"$gte": min_rat}

        st.markdown("**Executed MongoDB Pipeline:**")
        pipeline_code = [
            {"$match": match_stage} if match_stage else "/* No initial $match (All products) */",
            {
                "$facet": {
                    "category_counts": [{"$sortByCount": "$category"}],
                    "brand_counts": [{"$sortByCount": "$brand"}, {"$limit": 10}],
                    "price_buckets": [
                        {
                            "$bucket": {
                                "groupBy": "$price",
                                "boundaries": [0, 500, 1500, 5000, 20000, 60000],
                                "default": "60000+",
                                "output": {"count": {"$sum": 1}, "avg_price": {"$avg": "$price"}}
                            }
                        }
                    ],
                    "rating_distribution": [
                        {
                            "$bucket": {
                                "groupBy": "$rating",
                                "boundaries": [0.0, 4.0, 4.3, 4.6, 5.1],
                                "default": "Other",
                                "output": {"count": {"$sum": 1}}
                            }
                        }
                    ],
                    "stock_status": [
                        {
                            "$project": {
                                "status": {
                                    "$cond": [
                                        {"$eq": ["$stock", 0]}, "Out of Stock",
                                        {"$cond": [{"$lte": ["$stock", 10]}, "Low Stock (<=10)", "Available (>10)"]}
                                    ]
                                }
                            }
                        },
                        {"$sortByCount": "$status"}
                    ]
                }
            }
        ]
        st.code(json.dumps(pipeline_code, indent=2), language="json")

        # Execute faceted aggregation
        facets = get_faceted_results(collection, match_query=match_stage if match_stage else None)

        # Extract matching count
        match_cnt_list = facets.get("matching_product_count", [])
        total_matches = match_cnt_list[0].get("count", 0) if match_cnt_list else 0
        
        st.metric("Total Matching Products (from $facet)", f"{total_matches} Items")
        
        # Display matching products table
        matching_docs = list(collection.find(match_stage if match_stage else {}))
        if matching_docs:
            st.markdown(f"**Matching Products Preview ({len(matching_docs)} items):**")
            df_matches = pd.DataFrame(matching_docs)[["product_id", "name", "brand", "category", "price", "stock", "rating"]]
            st.dataframe(df_matches, use_container_width=True, hide_index=True)

        st.markdown("### Faceted Aggregation Output (Multi-Dimensional Summaries)")
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**Category Facets:**")
            cat_facet = facets.get("category_counts", [])
            st.dataframe(pd.DataFrame(cat_facet), use_container_width=True, hide_index=True)

            st.markdown("**Price Bucket Facets:**")
            price_facet = facets.get("price_buckets", [])
            st.dataframe(pd.DataFrame(price_facet), use_container_width=True, hide_index=True)

        with fc2:
            st.markdown("**Top Brand Facets:**")
            brand_facet = facets.get("brand_counts", [])
            st.dataframe(pd.DataFrame(brand_facet), use_container_width=True, hide_index=True)

            st.markdown("**Stock Availability Facets:**")
            stock_facet = facets.get("stock_status", [])
            st.dataframe(pd.DataFrame(stock_facet), use_container_width=True, hide_index=True)



# ------------------------------------------------------------------------------
# 8. ANALYTICS
# ------------------------------------------------------------------------------
elif menu_selection == "8. Analytics":
    st.markdown('<div class="main-header">Catalog Analytics & Visualizations</div>', unsafe_allow_html=True)
    st.caption("Aggregation pipelines driving interactive analytical charts.")

    if ensure_db():
        cat_stats = get_category_statistics(collection)
        brand_stats = get_brand_statistics(collection)

        if not cat_stats:
            st.info("No data available for analytics.")
        else:
            df_cat = pd.DataFrame(cat_stats)
            df_brand = pd.DataFrame(brand_stats)

            # Chart Row 1: Category Count & Avg Price
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("1. Product Distribution by Category")
                fig1 = px.bar(df_cat, x="category", y="total_products", text_auto=True, color="category",
                              labels={"total_products": "Product Count", "category": "Category"})
                fig1.update_layout(showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)

            with c2:
                st.subheader("2. Average Price by Category (₹)")
                fig2 = px.bar(df_cat, x="category", y="avg_price", text_auto=True, color="category",
                              labels={"avg_price": "Avg Price (₹)", "category": "Category"})
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            # Chart Row 2: Average Rating & Top Brands
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("3. Average Customer Rating by Category")
                fig3 = px.bar(df_cat, x="category", y="avg_rating", text_auto=True, color="avg_rating",
                              color_continuous_scale="Blues", range_y=[3.5, 5.0],
                              labels={"avg_rating": "Rating (out of 5)", "category": "Category"})
                st.plotly_chart(fig3, use_container_width=True)

            with c4:
                st.subheader("4. Brand-wise Product Counts (Top 15)")
                fig4 = px.bar(df_brand, x="count", y="brand", orientation="h", text_auto=True,
                              color="count", color_continuous_scale="Viridis",
                              labels={"count": "Number of Products", "brand": "Brand"})
                fig4.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig4, use_container_width=True)

            # Chart Row 3: Price distribution & Inventory value
            all_prods = get_products(collection)
            df_all = pd.DataFrame(all_prods)

            c5, c6 = st.columns(2)
            with c5:
                st.subheader("5. Overall Price Distribution (Histogram)")
                fig5 = px.histogram(df_all, x="price", nbins=20, color="category",
                                    labels={"price": "Price (₹)"})
                st.plotly_chart(fig5, use_container_width=True)

            with c6:
                st.subheader("6. Total Inventory Valuation by Category (₹)")
                fig6 = px.pie(df_cat, names="category", values="total_inventory_value", hole=0.4,
                              labels={"total_inventory_value": "Inventory Valuation"})
                st.plotly_chart(fig6, use_container_width=True)


# ------------------------------------------------------------------------------
# 9. MONGODB QUERIES LIVE
# ------------------------------------------------------------------------------
elif menu_selection == "9. MongoDB Queries Live":
    st.markdown('<div class="main-header">Live MongoDB Query Demonstrator</div>', unsafe_allow_html=True)
    st.caption("Interactive demonstration of operators: $gt, $lte, $in, $exists, nested attributes, and regex.")

    if ensure_db():
        query_options = {
            "1. Comparison: Products with Price < ₹1,000": {"price": {"$lt": 1000}},
            "2. Comparison: High Rated Products (Rating >= 4.6)": {"rating": {"$gte": 4.6}},
            "3. Set Membership: Selected Brands ($in)": {"brand": {"$in": ["Sony", "Apple", "OnePlus", "boAt"]}},
            "4. Logical AND: Electronics with Stock <= 15": {"$and": [{"category": "Electronics"}, {"stock": {"$lte": 15}}]},
            "5. Logical OR: Category Groceries OR Apparel": {"$or": [{"category": "Groceries"}, {"category": "Apparel"}]},
            "6. Dynamic Nested Attribute: Organic Groceries": {"attributes.organic": True},
            "7. Dynamic Nested Attribute: Apparel Color = Black": {"attributes.color": "Black"},
            "8. Dynamic Nested Attribute: Electronics with RAM": {"attributes.ram": {"$exists": True}},
            "9. Inventory: Low Stock Products (Stock <= 10)": {"stock": {"$lte": 10}},
            "10. Custom Query JSON (Type your own)": {}
        }

        selected_label = st.selectbox("Select Query Scenario to Execute", list(query_options.keys()))

        if "Custom" in selected_label:
            raw_q = st.text_area("Enter MongoDB Query Filter (JSON)", value='{"category": "Electronics", "price": {"$lt": 10000}}')
            try:
                active_query = json.loads(raw_q)
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
                active_query = {}
        else:
            active_query = query_options[selected_label]

        st.markdown("**Executed PyMongo Command:**")
        st.code(f"db.products.find({json.dumps(active_query, indent=2)})", language="python")

        results = get_products(collection, query=active_query)
        st.success(f"Matched **{len(results)}** documents.")

        if results:
            clean_res = []
            for r in results:
                clean_res.append({
                    "Product ID": r.get("product_id"),
                    "Name": r.get("name"),
                    "Category": r.get("category"),
                    "Price (₹)": r.get("price"),
                    "Stock": r.get("stock"),
                    "Rating": r.get("rating"),
                    "Attributes": json.dumps(r.get("attributes", {}))
                })
            st.dataframe(pd.DataFrame(clean_res), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------------------
# 10. EXPORT DATA (CSV)
# ------------------------------------------------------------------------------
elif menu_selection == "10. Export Data (CSV)":
    st.markdown('<div class="main-header">Export Data & Generate Reports</div>', unsafe_allow_html=True)
    st.caption("Generate downloadable CSV reports from MongoDB Atlas.")

    if ensure_db():
        all_docs = get_products(collection)

        if not all_docs:
            st.info("No data available to export.")
        else:
            # Flatten products
            flat_rows = []
            for d in all_docs:
                row = {
                    "product_id": d.get("product_id"),
                    "name": d.get("name"),
                    "brand": d.get("brand"),
                    "category": d.get("category"),
                    "subcategory": d.get("subcategory"),
                    "price": d.get("price"),
                    "stock": d.get("stock"),
                    "rating": d.get("rating"),
                    "reviews": d.get("reviews"),
                    "description": d.get("description"),
                    "attributes": json.dumps(d.get("attributes", {})),
                    "created_at": d.get("created_at")
                }
                flat_rows.append(row)
            df_products = pd.DataFrame(flat_rows)

            # Generate Category summary
            cat_stats = get_category_statistics(collection)
            df_cat = pd.DataFrame(cat_stats)

            # Generate Brand summary
            brand_stats = get_brand_statistics(collection)
            df_brand = pd.DataFrame(brand_stats)

            # Generate Inventory report
            df_inv = df_products.copy()
            df_inv["inventory_value"] = df_inv["price"] * df_inv["stock"]
            df_inv["stock_status"] = df_inv["stock"].apply(
                lambda s: "Out of Stock" if s == 0 else ("Low Stock (<=10)" if s <= 10 else "Available")
            )
            df_inv_report = df_inv[["product_id", "name", "category", "price", "stock", "inventory_value", "stock_status"]]

            st.subheader("Download Formats")
            r1, r2 = st.columns(2)

            with r1:
                st.markdown("**1. Complete Product Catalog (`products.csv`)**")
                csv_p = df_products.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download products.csv", csv_p, "products.csv", "text/csv")

                st.markdown("**2. Category Summary (`category_summary.csv`)**")
                csv_c = df_cat.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download category_summary.csv", csv_c, "category_summary.csv", "text/csv")

            with r2:
                st.markdown("**3. Brand Summary (`brand_summary.csv`)**")
                csv_b = df_brand.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download brand_summary.csv", csv_b, "brand_summary.csv", "text/csv")

                st.markdown("**4. Inventory Valuation Report (`inventory_report.csv`)**")
                csv_i = df_inv_report.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download inventory_report.csv", csv_i, "inventory_report.csv", "text/csv")


# ------------------------------------------------------------------------------
# 11. ABOUT PROJECT
# ------------------------------------------------------------------------------
elif menu_selection == "11. About Project":
    st.markdown('<div class="main-header">About This Project</div>', unsafe_allow_html=True)

    st.markdown("""
    ### Dynamic E-Commerce Product Catalog Using MongoDB
    **Academic NoSQL Database Project**

    ---

    #### 1. Problem Statement
    In traditional relational (SQL) databases, products from divergent categories (such as Groceries, Apparel, Electronics, and Kitchenware)
    require vastly different attributes (e.g. *RAM/Storage* vs *Size/Color* vs *Expiry Date/Organic*).
    Forcing these into a relational table results in **severe column sparsity (thousands of `NULL` values)**, rigid migration cycles,
    and slow `JOIN` queries.

    #### 2. Proposed Solution
    Using MongoDB's document-oriented NoSQL architecture:
    - Products are stored as **flexible BSON documents** in a single `products` collection.
    - Common core fields (`product_id`, `name`, `price`, `stock`, `rating`) exist at the root level.
    - Category-specific attributes are nested dynamically inside an `attributes` sub-document without schema enforcement errors.
    - High-performance faceted filtering is delivered using MongoDB's `$facet` and `$match` aggregation pipeline stages.

    #### 3. Technology Stack
    - **Database:** MongoDB Atlas (Cloud NoSQL)
    - **Language:** Python 3.10+
    - **Driver:** PyMongo 4.x
    - **User Interface:** Streamlit
    - **Visualizations:** Plotly & Matplotlib
    - **Data Processing:** Pandas

    #### 4. Key Aggregation Techniques Demonstrated
    - `$match`: Filtering before computation to minimize memory overhead.
    - `$group`: Category and brand summarization.
    - `$facet`: Multi-faceted search execution in a single atomic database trip.
    - `$project`: Inventory valuation (`$multiply: ["$price", "$stock"]`).
    - Compound Indexes: Fast text search across multiple fields.
    """)

    st.info("Developed for Academic Evaluation, Google Colab Execution, and Viva Voce Demonstration.")
