# Dynamic E-Commerce Product Catalog Using MongoDB

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB%20Atlas-green.svg)](https://www.mongodb.com/cloud/atlas)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red.svg)](https://streamlit.io/)
[![Google Colab](https://img.shields.io/badge/Notebook-Google%20Colab-orange.svg)](https://colab.research.google.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

An academic, production-ready NoSQL database project demonstrating how **MongoDB's flexible document model** solves the classic relational database bottleneck for heterogeneous e-commerce product catalogs.

---

## Table of Contents
1. [Project Title](#1-project-title)
2. [Overview](#2-overview)
3. [Problem Statement](#3-problem-statement)
4. [Objectives](#4-objectives)
5. [Features](#5-features)
6. [Technology Stack](#6-technology-stack)
7. [Why MongoDB?](#7-why-mongodb)
8. [MongoDB Architecture](#8-mongodb-architecture)
9. [Document Structure](#9-document-structure)
10. [Dynamic Attributes](#10-dynamic-attributes)
11. [CRUD Operations](#11-crud-operations)
12. [Aggregation Pipelines](#12-aggregation-pipelines)
13. [$match and $facet Implementation](#13-match-and-facet-implementation)
14. [Google Colab Setup](#14-google-colab-setup)
15. [MongoDB Atlas Setup Guide](#15-mongodb-atlas-setup-guide)
16. [How to Run (Notebook & Local)](#16-how-to-run)
17. [Streamlit Instructions](#17-streamlit-instructions)
18. [CSV Exports & Reports](#18-csv-exports)
19. [Screenshots & UI Walkthrough](#19-screenshots-section)
20. [Future Enhancements](#20-future-enhancements)
21. [Conclusion](#21-conclusion)

---

## 1. Project Title
**Dynamic E-Commerce Product Catalog Using MongoDB**  
*A Schema-Agnostic, Multi-Category NoSQL Catalog with Faceted Aggregations and Interactive Streamlit Dashboard.*

---

## 2. Overview
Modern retail platforms must catalog thousands of products across diverse domains—including **Groceries, Apparel, Electronics, and Home & Kitchen**. Each category has radically different attributes:
* Groceries require weight, organic certification, and expiry dates.
* Apparel requires sizing, colors, fabric composition, and gender categorization.
* Electronics require processor specs, RAM, battery capacity, and warranty periods.
* Home & Kitchen require dimensions, material composition, and usage guidelines.

This project implements a unified **MongoDB database (`ecommerce_catalog`)** and collection (`products`) that houses all categories within polymorphic documents. By combining root-level common fields with nested dynamic subdocuments (`attributes`), the system supports real-time multi-criteria filtering, compound full-text search, complex inventory valuation, and multi-faceted aggregations without schema migrations or NULL-column storage penalties.

---

## 3. Problem Statement
Traditional Relational Database Management Systems (RDBMS) enforce rigid tables with fixed schemas. In an e-commerce catalog, this leads to two well-documented anti-patterns:
1. **The Sparse-Columns Anti-Pattern:** Creating a single table with columns for every category attribute results in 70%+ of cells being `NULL` (e.g., grocery items have `NULL` for `ram`, `screen_size`, and `fabric`). This causes database bloat, inefficient page usage, and degrades B-tree index performance.
2. **The Entity-Attribute-Value (EAV) Anti-Pattern:** Splitting attributes into three-column tables (`entity_id`, `attribute_name`, `attribute_value`) eliminates NULLs but requires 8 to 12 expensive SQL `JOIN` operations to render a single product card, crippling read performance under concurrent user loads.

### The NoSQL Solution
MongoDB documents map directly to application objects. Common fields reside at the document root, while domain-specific attributes live inside an unconstrained, indexed subdocument (`attributes`), achieving $O(1)$ single-read document retrieval with zero column sparsity.

---

## 4. Objectives
1. **Develop a Dynamic Catalog:** Store heterogeneous products in a single collection (`products`).
2. **Support Dynamic Attributes:** House category-specific keys inside nested subdocuments.
3. **Implement Full CRUD Operations:** Complete Create, Read, Update, and Delete with database-level constraints.
4. **Demonstrate MongoDB Operators:** Execute `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`, `$and`, `$or`, and `$exists`.
5. **Full-Text Search:** Query product names, brands, and descriptions via compound `$text` indexing.
6. **Execute Aggregation Pipelines:** Demonstrate multi-stage data processing with `$match`, `$group`, `$sort`, `$project`, `$bucket`, and `$limit`.
7. **Multi-Faceted Search:** Implement a dedicated `$facet` aggregation pipeline executing 5 analytical summaries concurrently.
8. **Real-Time Inventory Analysis:** Compute inventory valuations ($\text{Price} \times \text{Stock}$) and classify stock status.
9. **Interactive Web Dashboard:** Build an 11-page responsive Streamlit dashboard.
10. **Google Colab Cloud Execution:** Enable seamless execution from notebook cells directly to MongoDB Atlas.
11. **Export Capabilities:** Generate downloadable CSV reports for business intelligence.

---

## 5. Features
* **Zero-Setup Demo Fallback:** Built-in `MockCollection` engine allows local or offline evaluation if cloud cluster credentials are not immediately configured.
* **Safe Authentication:** Seamless integration with Python `getpass` and Google Colab Secrets masking URIs from execution logs.
* **Unique Key Enforcement:** Database-level unique index on `product_id` preventing duplicate catalog writes.
* **Idempotent Data Seeding:** Database initialization checks existing records before writing, preventing duplicate records on notebook reruns.
* **Responsive Multi-Page UI:** Streamlit interface with 11 pages including KPI cards, interactive Plotly visualizations, dynamic CRUD forms, and CSV exports.

---

## 6. Technology Stack
* **Programming Language:** Python 3.10+
* **Primary Database:** MongoDB 7.0+ (Community / Enterprise)
* **Cloud Database as a Service:** MongoDB Atlas (M0 Free Tier)
* **Python Database Driver:** PyMongo 4.6+
* **Data Manipulation & Analysis:** Pandas 2.0+
* **Interactive Visualization:** Plotly Express & Plotly Graph Objects 5.18+
* **Web Application Framework:** Streamlit 1.30+
* **Execution Environment:** Google Colab / Local Terminal / Render Cloud

---

## 7. Why MongoDB?
* **Polymorphic Documents:** Documents in a single collection can have distinct structures and dynamic subfields.
* **Native JSON/BSON Alignment:** Documents correspond 1:1 with JSON, removing the Object-Relational Impedance Mismatch.
* **Subdocument Indexing:** MongoDB allows creating indexes on nested fields (e.g., `attributes.ram`, `attributes.organic`), providing high-speed nested queries.
* **High-Performance Aggregations:** Aggregations execute directly on database nodes, eliminating client-side memory bottlenecks.
* **High Availability & Horizontal Scale:** Built-in replica sets provide 99.99% uptime with automated failover, while sharding supports petabyte-scale horizontal partitioning.

---

## 8. MongoDB Architecture
The system architecture follows a clean 3-tier model:
```
+-------------------------------------------------------------+
|                      PRESENTATION TIER                      |
|      Google Colab Notebook  |  Streamlit Web Dashboard       |
+-------------------------------------------------------------+
                              | (PyMongo Driver / TLS)
                              v
+-------------------------------------------------------------+
|                     APPLICATION & LOGIC                     |
|  CRUD Wrappers | Faceted Pipeline ($facet) | Data Validator |
+-------------------------------------------------------------+
                              | (BSON Protocol)
                              v
+-------------------------------------------------------------+
|                      CLOUD DATABASE                         |
|     MongoDB Atlas Cluster (Primary Replica + Secondaries)   |
|        Database: ecommerce_catalog | Collection: products   |
|     Indexes: unique(product_id), text(name,brand,desc), ... |
+-------------------------------------------------------------+
```

---

## 9. Document Structure
All documents share common metadata fields at the root level, while category-specific attributes are encapsulated in the `attributes` subdocument:

```json
{
  "_id": {"$oid": "6640c1e8..."},
  "product_id": "P001",
  "name": "Daawat Rozana Basmati Rice",
  "brand": "Daawat",
  "category": "Groceries",
  "subcategory": "Rice & Grains",
  "price": 420.0,
  "stock": 85,
  "rating": 4.5,
  "reviews": 310,
  "description": "Daily aromatic long-grain basmati rice aged to perfection.",
  "attributes": {
    "weight": "5 kg",
    "organic": false,
    "expiry_months": 24,
    "grain_type": "Long Grain"
  },
  "created_at": "2026-01-10T10:00:00"
}
```

---

## 10. Dynamic Attributes
Below are representative examples illustrating how the `attributes` subdocument adapts across categories:

### Grocery Product
```json
{
  "product_id": "P002",
  "name": "Organic India Tulsi Green Tea",
  "category": "Groceries",
  "price": 280.0,
  "attributes": {
    "weight": "100 g",
    "organic": true,
    "expiry_months": 18,
    "caffeine_free": false
  }
}
```

### Apparel Product
```json
{
  "product_id": "P014",
  "name": "Levi's Men 511 Slim Fit Jeans",
  "category": "Apparel",
  "price": 2499.0,
  "attributes": {
    "size": "32",
    "color": "Dark Indigo",
    "material": "98% Cotton 2% Elastane",
    "gender": "Men",
    "fit": "Slim Fit"
  }
}
```

### Electronics Product
```json
{
  "product_id": "P027",
  "name": "Apple MacBook Air M2",
  "category": "Electronics",
  "price": 89900.0,
  "attributes": {
    "ram": "16GB",
    "storage": "512GB SSD",
    "processor": "Apple M2 8-core",
    "battery": "18 Hours",
    "warranty": "1 Year"
  }
}
```

### Home & Kitchen Product
```json
{
  "product_id": "P039",
  "name": "Prestige Deluxe Alpha Stainless Steel Pressure Cooker",
  "category": "Home & Kitchen",
  "price": 2150.0,
  "attributes": {
    "capacity": "5 Litres",
    "material": "Food Grade Stainless Steel",
    "induction_compatible": true,
    "warranty": "5 Years"
  }
}
```

---

## 11. CRUD Operations
The application implements complete CRUD operations using PyMongo:

* **Create (`insert_one`, `insert_many`):** Inserts single or bulk product documents. Rejects duplicate `product_id` via unique index.
* **Read (`find`, `find_one`):** Supports equality, range filtering, projection, and pagination.
* **Update (`update_one`, `update_many`):** Modifies specific fields and nested subfields in-place using `$set` and `$inc`.
* **Delete (`delete_one`):** Removes target documents with safety confirmation and existence validation.

---

## 12. Aggregation Pipelines
The project implements all 10 core analytical aggregation reports:
1. **Product Count by Category:** `$group` on `$category` with `$sum`.
2. **Average Price by Category:** `$group` on `$category` with `$avg` and `$round`.
3. **Average Rating by Category:** Aggregates customer feedback scores by category.
4. **Brand-Wise Product Count:** Identifies brand concentration using `$sortByCount`.
5. **Top-Rated Products:** Filters `$rating >= 4.7` and sorts by popularity.
6. **Most Expensive Products:** Identifies premium luxury items across the catalog.
7. **Total Inventory Value:** Calculates total capital tied up in stock ($\sum \text{Price} \times \text{Stock}$).
8. **Low-Stock Products:** Filters inventory units where `stock <= 10` for replenishment.
9. **Price Distribution Buckets:** Groups items into ₹0–500, ₹500–1,500, ₹1,500–5,000, and ₹20,000+ buckets via `$bucket`.
10. **Category-Wise Inventory Valuation:** Groups valuation and unit counts by domain category.

---

## 13. `$match` and `$facet` Implementation
The project features a dedicated **multi-faceted search pipeline** demonstrating MongoDB's high-performance parallel processing:

```python
pipeline = [
    # Optional early filtering stage
    {"$match": {"category": "Electronics", "price": {"$lte": 50000}}},
    # Parallel multi-dimensional aggregation
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
            "matching_product_count": [{"$count": "count"}],
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
```
**Why this matters:** Instead of executing 5 round-trip network queries from the web server to the database, MongoDB executes all 5 sub-pipelines in parallel on the database server in a single atomic transaction.

---

## 14. Google Colab Setup
The primary execution deliverable is the Jupyter Notebook:
`dynamic_ecommerce_catalog.ipynb`

### Execution Workflow:
1. Open Google Colab: [colab.research.google.com](https://colab.research.google.com)
2. Upload `dynamic_ecommerce_catalog.ipynb`.
3. Run **Cell 5** to install dependencies:
   ```bash
   !pip install -q pymongo pandas plotly streamlit
   ```
4. Run **Cell 7** and enter your MongoDB Atlas URI when prompted (or configure via Colab Secrets).
5. Execute cells in order (Cells 1 through 31). Every cell is fully executable and self-contained!

---

## 15. MongoDB Atlas Setup Guide
1. **Create Free Account:** Visit [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) and register.
2. **Deploy Free Cluster:** Create an **M0 Free Cluster** (hosted on AWS / GCP in your nearest region).
3. **Configure Database User:** Under **Database Access**, create a user (e.g., `catalog_admin`) with password authentication and `readWriteAnyDatabase` privileges.
4. **Configure Network Access:** Under **Network Access**, click **Add IP Address** $\rightarrow$ **Allow Access from Anywhere** (`0.0.0.0/0`) $\rightarrow$ Confirm. (Required for dynamic Google Colab runtime IPs).
5. **Get Connection String:** Click **Connect** $\rightarrow$ **Drivers** $\rightarrow$ Select Python 3.12+ $\rightarrow$ Copy the connection string:
   `mongodb+srv://<username>:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority`

---

## 16. How to Run

### Option A: In Google Colab
Follow Section 14 above. Execute the notebook sequentially. Cell 30 will launch Streamlit and provide a localtunnel link to open the interactive dashboard.

### Option B: Local Machine Execution
1. Clone the repository and navigate to the directory:
   ```bash
   cd dynamic_ecommerce_catalog
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your MongoDB Atlas URI:
   ```bash
   # Windows PowerShell:
   $env:MONGODB_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
   # Linux/macOS:
   export MONGODB_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
   ```
5. Launch the Streamlit application:
   ```bash
   streamlit run app.py
   ```
6. Open your browser at `http://localhost:8501`.

---

## 17. Streamlit Instructions
The dashboard contains 11 dedicated functional pages accessible from the left sidebar:
* **Page 1: Dashboard:** Live KPI cards (Total Products, Categories, Brands, Average Price, Average Rating, Total Inventory Valuation, Low-Stock items).
* **Page 2: Product Catalog:** Tabular catalog with column sorting, keyword search, and item inspection.
* **Page 3: Add Product:** Dynamic form that changes attribute inputs based on selected category.
* **Page 4: Update Product:** Select existing product ID to modify price, stock, or nested attributes.
* **Page 5: Delete Product:** Delete products by ID with safety confirmation dialog.
* **Page 6: Search & Filters:** Multi-criteria filtering by category, price bounds, rating, and stock status.
* **Page 7: Faceted Search ($facet):** Parallel faceted navigation demonstrating live pipeline execution and matching counts.
* **Page 8: Analytics:** 6 Plotly charts displaying distributions, price histograms, and category valuations.
* **Page 9: MongoDB Query Demonstration:** Live interactive query console testing comparison, logical, and nested attribute queries.
* **Page 10: Export Reports:** Instant CSV download buttons for catalog data, category summaries, brand rankings, and inventory reports.
* **Page 11: About:** System architecture, academic metadata, and technology stack explanations.

---

## 18. CSV Exports
The system automatically generates and allows downloading of 4 standardized CSV reports:
1. `reports/products.csv`: Full catalog with flattened attributes JSON.
2. `reports/category_summary.csv`: Rollup of product counts, average prices, and stock per category.
3. `reports/brand_summary.csv`: Brand concentration and average pricing metrics.
4. `reports/inventory_report.csv`: Complete stock status, valuation, and unit levels.

---

## 19. Screenshots Section
*(Recommended screenshots to capture during evaluation)*
* **Screenshot 1:** Streamlit Dashboard with KPI metric cards and category overview.
* **Screenshot 2:** Faceted Search ($facet) showing parallel bucket distributions.
* **Screenshot 3:** Dynamic Add Product form displaying category-specific nested fields.
* **Screenshot 4:** Plotly Analytics charts (Price distribution histogram & Category inventory pie chart).
* **Screenshot 5:** MongoDB Atlas Web Console displaying the `ecommerce_catalog.products` collection and indexes.

---

## 20. Future Enhancements
* **Atlas Vector Search:** Implement semantic search embeddings to support natural-language queries ("affordable cotton summer shirts").
* **MongoDB Change Streams:** Real-time stock change notifications pushed to client web sockets.
* **Role-Based Access Control (RBAC):** Separate interfaces for Vendor Catalog Managers and Customers.
* **Multi-Currency Support:** Automated currency conversion pipeline for international catalogs.

---

## 21. Conclusion
This project successfully proves the architectural superiority of MongoDB for dynamic e-commerce product catalogs. By combining common metadata at the root level with unconstrained nested subdocuments, MongoDB completely eliminates the SQL sparse-columns and EAV bottlenecks. Coupled with high-performance compound indexing and the parallel processing power of the `$facet` aggregation framework, MongoDB delivers a responsive, scalable, and production-ready catalog management platform.
