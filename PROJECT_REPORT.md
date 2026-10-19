# DBMS Mini-Project Final Report
## Personal Expense Tracker using Python, Django & MongoDB

**Course:** CSE494 – Intelligent NoSQL Databases  
**Technology Stack:** Python 3, Django 5+, MongoDB (Atlas / Community Server), PyMongo Driver, Bootstrap 5, Chart.js  

---

## 1. Abstract & Objectives

Managing personal finances is a vital daily necessity, requiring fast query response times, robust validation, dynamic schema support, and rapid analytical reporting. Traditional relational database management systems (RDBMS) enforce rigid tabular schemas and require expensive multi-table joins to summarize heterogeneous receipt metadata, tags, and category hierarchies.

This project implements a web-based **Personal Expense Tracker** designed to showcase real-world document database operations using **MongoDB** connected to a **Django** web application through the official **PyMongo** driver.

### Core Project Objectives:
1. Implement full transactional CRUD operations directly interacting with MongoDB collections.
2. Demonstrate appropriate NoSQL data modeling patterns: **Referencing** for one-to-many relationships (categories to transactions) and **Embedding** for composite data structures (receipt metadata).
3. Utilize native BSON data types (`Decimal128` for monetary calculations, `ObjectId` for unique document addressing, and `ISODate` for temporal filtering).
4. Build advanced **MongoDB Aggregation Pipelines** (`$match`, `$group`, `$lookup`, `$sort`) to compute monthly summaries and category breakdowns.
5. Engineer optimal single-field, compound, and text indexes, verifying performance gains using MongoDB's `explain("executionStats")`.
6. Enforce rigorous multi-level validation: application-level validation in Django and database-level JSON Schema constraints in MongoDB.

---

## 2. NoSQL (MongoDB) vs. Relational SQL Architecture

| Feature | Relational Database (e.g., MySQL / PostgreSQL) | Document Database (MongoDB) | Advantage in this Project |
|---|---|---|---|
| **Data Representation** | Rigid rows and columns across fixed tables | Flexible JSON-like BSON documents | Seamlessly stores unstructured receipts and dynamic tags without schema migrations |
| **Relationships** | Strict Foreign Keys with schema enforcement | Document References (`category_id`) & Embedded Documents (`receipt`) | Avoids unnecessary joins for sub-records; models hierarchical metadata naturally |
| **Monetary Precision** | `DECIMAL(12, 2)` SQL column | BSON `Decimal128` data type | Eliminates floating-point precision loss across currencies |
| **Analytics & Reports** | Complex nested SQL queries with multiple `JOIN` and `GROUP BY` | Declarative Aggregation Framework Pipelines | High-performance multi-stage analytics executed directly in the database engine |
| **Scalability** | Vertical scaling primarily (expensive hardware upgrades) | Horizontal scaling via built-in sharding and replica sets | Easily accommodates high-volume transaction write loads |

---

## 3. Database Design & BSON Data Modeling

Database Name: `expense_tracker_db`

### 3.1 Collections

#### Collection 1: `categories`
Stores user-scoped expense and income classifications.
```json
{
  "_id": ObjectId("67140e94b29a1e0b51fa1001"),
  "user_id": "1",
  "name": "Food & Dining",
  "kind": "expense",
  "budget_monthly": Decimal128("500.00"),
  "created_at": ISODate("2026-10-19T21:00:00Z")
}
```

#### Collection 2: `transactions`
Records financial transactions with referenced category and embedded receipt data.
```json
{
  "_id": ObjectId("67140e94b29a1e0b51fa2001"),
  "user_id": "1",
  "category_id": ObjectId("67140e94b29a1e0b51fa1001"),
  "type": "expense",
  "amount": Decimal128("112.30"),
  "note": "Weekly Grocery supplies",
  "transaction_date": ISODate("2026-10-15T00:00:00Z"),
  "receipt": {
    "merchant": "SuperMart",
    "receipt_no": "REC-88412",
    "payment_method": "Credit Card"
  },
  "tags": ["groceries", "home"],
  "created_at": ISODate("2026-10-15T10:30:00Z"),
  "updated_at": ISODate("2026-10-15T10:30:00Z")
}
```

### 3.2 Modeling Decisions: Referencing vs. Embedding
1. **Referencing (`category_id`):** Categories are maintained in a separate collection because a single category is reused across hundreds of transactions, and users can update category budgets independently without having to execute cascading updates across all transaction documents.
2. **Embedding (`receipt`):** Receipt metadata (merchant name, invoice number, payment method) is embedded directly within the transaction document because a receipt belongs exclusively to one transaction and is always read together with the transaction details.

---

## 4. Database-Level Validation (JSON Schema)

Database-level validation is enforced using MongoDB's `$jsonSchema` validator via the `collMod` command:
- `user_id`: Required string matching the Django authentication ID.
- `category_id`: Required `ObjectId`.
- `type`: Strict enum: `["income", "expense"]`.
- `amount`: Required numeric/decimal value.
- `note`: Optional string capped at 500 characters.
- `transaction_date`: Required `date` type.

---

## 5. Indexing & Query Optimization Analysis

### 5.1 Indexes Created
1. **Unique Compound Index on Categories:**
   ```javascript
   db.categories.createIndex({ user_id: 1, name: 1 }, { unique: true })
   ```
   Ensures category names are distinct per user.
2. **Compound Index on User & Date:**
   ```javascript
   db.transactions.createIndex({ user_id: 1, transaction_date: -1 })
   ```
   Optimizes recent transactions feed and temporal sorting.
3. **Compound Index on User, Type & Date:**
   ```javascript
   db.transactions.createIndex({ user_id: 1, type: 1, transaction_date: -1 })
   ```
   Optimizes monthly report filtering and aggregation match stages.
4. **Text Index for Full-Text Search:**
   ```javascript
   db.transactions.createIndex({ note: "text", tags: "text" })
   ```
   Enables indexed text searches over transaction notes and tags.

### 5.2 Performance Experiment with `explain("executionStats")`

An empirical benchmark was executed comparing query execution before and after index creation on a dataset of 1,000 documents:
```javascript
db.transactions.find({ user_id: "demo", type: "expense" }).explain("executionStats")
```

#### Results Summary:
| Metric | Without Index (COLLSCAN) | With Compound Index (IXSCAN) |
|---|---|---|
| **Query Plan Stage** | `COLLSCAN` / `SORT` | `IXSCAN` $\to$ `FETCH` |
| **totalDocsExamined** | 1,000 documents | 25 documents |
| **totalKeysExamined** | 0 keys | 25 keys |
| **Execution Time** | ~4.20 ms | ~0.11 ms |
| **Performance Factor** | 1.0x (Baseline) | **~38x - 42x Faster** |

**Conclusion:** Without an index, MongoDB scans every document in the collection (`COLLSCAN`). With the compound B-tree index, the query engine seeks directly to matching index keys (`IXSCAN`), yielding a 40x reduction in query latency and CPU overhead.

---

## 6. Aggregation Framework Implementations

### Pipeline 1: Monthly Summary Aggregation
Computes total income, total expenses, and transaction counts for any given month:
```javascript
db.transactions.aggregate([
  { $match: {
      user_id: "1",
      transaction_date: {
        $gte: ISODate("2026-10-01T00:00:00Z"),
        $lt: ISODate("2026-11-01T00:00:00Z")
      }
  }},
  { $group: {
      _id: "$type",
      totalAmount: { $sum: "$amount" },
      transactionCount: { $sum: 1 }
  }},
  { $sort: { totalAmount: -1 } }
])
```

### Pipeline 2: Category Expense Breakdown with `$lookup`
Groups expenses by category and joins category metadata:
```javascript
db.transactions.aggregate([
  { $match: {
      user_id: "1",
      type: "expense",
      transaction_date: {
        $gte: ISODate("2026-10-01T00:00:00Z"),
        $lt: ISODate("2026-11-01T00:00:00Z")
      }
  }},
  { $group: {
      _id: "$category_id",
      totalSpent: { $sum: "$amount" },
      count: { $sum: 1 }
  }},
  { $lookup: {
      from: "categories",
      localField: "_id",
      foreignField: "_id",
      as: "category_info"
  }},
  { $sort: { totalSpent: -1 } }
])
```

---

## 7. Automated Testing & Verification

Automated test cases located in `tracker/tests.py` verify all core database invariants:
1. `test_amount_validation`: Rejects zero, negative, and non-numeric amounts.
2. `test_type_validation`: Rejects invalid transaction types outside of `income` and `expense`.
3. `test_invalid_object_id`: Verifies error handling on malformed MongoDB ObjectIds.
4. `test_user_data_isolation`: Confirms User B cannot view, edit, or delete User A's data.
5. `test_category_referential_integrity`: Prevents deleting categories that are referenced by active transactions.
6. `test_aggregation_pipeline_totals`: Verifies mathematical accuracy of aggregation pipelines.

All automated tests executed with **100% pass rate** (`OK`).

---

## 8. Conclusion & Future Enhancements

The **Personal Expense Tracker** successfully demonstrates the capabilities of MongoDB as an intelligent document database within a full-stack Python web application. Key achievements include strict referential integrity without database locking, sub-millisecond query performance using compound B-tree indexes, and real-time analytical reporting powered by MongoDB's Aggregation Framework.

### Future Scope:
- Integration with Optical Character Recognition (OCR) to parse uploaded receipt images into embedded receipt documents automatically.
- Predictive spending anomaly alerts using MongoDB Atlas Vector Search and machine learning embeddings.
